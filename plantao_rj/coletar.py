"""Plantão RJ independente: INMET CAP + dois modelos ICON/GFS.
Não importa componentes dos Reels nem do workflow antigo."""
import datetime as dt
import json
import math
import os
import re
import unicodedata
import xml.etree.ElementTree as ET
from pathlib import Path
from zoneinfo import ZoneInfo
import requests

TZ = ZoneInfo("America/Sao_Paulo")
REGIOES = [
    ("Rio de Janeiro",-22.9068,-43.1729),("Niterói",-22.8832,-43.1034),
    ("Duque de Caxias",-22.7858,-43.3045),("Nova Iguaçu",-22.7592,-43.4511),
    ("São Gonçalo",-22.8268,-43.0634),("Belford Roxo",-22.764,-43.3992),
    ("São João de Meriti",-22.8058,-43.3729),("Nilópolis",-22.8075,-43.4139),
    ("Itaboraí",-22.7445,-42.8598),("Maricá",-22.9194,-42.8186)]
MODELOS=("icon_seamless","gfs_seamless")
INMET="https://apiprevmet3.inmet.gov.br/avisos/ativos"
API="https://api.open-meteo.com/v1/forecast"
TIPOS={"TEMPESTADE":"temporal","CHUVAS INTENSAS":"chuva",
       "ACUMULADO DE CHUVA":"chuva","GRANIZO":"granizo",
       "VENDAVAL":"vento","CICLONE":"ciclone",
       "CICLONE EXTRATROPICAL":"ciclone",
       "CICLONE TROPICAL":"ciclone","CICLONE SUBTROPICAL":"ciclone"}
PRIORIDADE={"ciclone":6,"granizo":5,"temporal":4,"chuva":3,"vento":2}
NS={"c":"urn:oasis:names:tc:emergency:cap:1.2"}

def normal(s):
    return "".join(ch for ch in unicodedata.normalize("NFD",str(s)) if not unicodedata.combining(ch)).upper().strip()

def obter(url,params=None):
    r=requests.get(url,params=params,timeout=(10,35),
         headers={"User-Agent":"PlantaoRJ/1.0 (monitor meteorologico publico)"})
    r.raise_for_status()
    if r.url.split("/")[2] != url.split("/")[2]:
        raise ValueError("Redirecionamento não autorizado")
    return r

def avisos_inmet(agora):
    j=obter(INMET).json()
    if not isinstance(j.get("hoje"),list) or not isinstance(j.get("futuro"),list):
        raise ValueError("Lista INMET incompleta")
    ids=set()
    nomes=[normal(c[0]) for c in REGIOES]
    for item in j["hoje"]+j["futuro"]:
        municipios=normal(item.get("municipios",""))
        if re.search(r"\s-\sRJ\s+\(\d{7}\)",municipios) and any(n in municipios for n in nomes):
            ids.add(str(item["id"]))
    out=[]
    for ident in sorted(ids):
        if not ident.isdigit(): raise ValueError("ID inválido do INMET")
        root=ET.fromstring(obter("https://apiprevmet3.inmet.gov.br/avisos/rss/"+ident).content)
        def top(k):return root.findtext("c:"+k,"",NS)
        if top("status")!="Actual" or top("msgType") not in ("Alert","Update") or top("scope")!="Public":
            continue
        if not top("sender").lower().endswith("@inmet.gov.br"):continue
        emitido=dt.datetime.fromisoformat(top("sent"))
        if not emitido.tzinfo or emitido > agora+dt.timedelta(minutes=5):continue
        for info in root.findall("c:info",NS):
            def field(k):return info.findtext("c:"+k,"",NS)
            if field("language") not in ("pt","pt-BR"):continue
            tipo=TIPOS.get(normal(field("event")))
            if not tipo:continue
            inicio=dt.datetime.fromisoformat(field("onset") or field("effective"))
            fim=dt.datetime.fromisoformat(field("expires"))
            if not inicio.tzinfo or not fim.tzinfo or fim<=agora or inicio>agora+dt.timedelta(hours=24):
                continue
            params={p.findtext("c:valueName","",NS):p.findtext("c:value","",NS)
                    for p in info.findall("c:parameter",NS)}
            presentes={normal(x) for x in re.findall(
                r"(?:^|,)\s*([^,]+?)\s+-\s+RJ\s+\(\d{7}\)",params.get("Municipios",""))}
            cidades=[c[0] for c in REGIOES if normal(c[0]) in presentes]
            url=field("web")
            if not cidades or not url.startswith("https://avisos.inmet.gov.br/"):
                continue
            out.append({"tipo":tipo,"inicio":inicio.isoformat(),"fim":fim.isoformat(),
                        "local":cidades[0],"cidades":cidades,"aviso_id":top("identifier"),
                        "severidade":field("severity"),"evento":field("event"),
                        "url":url,"fonte":"INMET","descricao":field("description")})
    return list({(x["aviso_id"],x["tipo"],x["inicio"]):x for x in out}.values())

def horas(resposta,agora):
    hourly=resposta["hourly"]; units=resposta["hourly_units"]
    if units["precipitation"]!="mm" or units["wind_gusts_10m"]!="km/h":
        raise ValueError("Unidades inesperadas")
    first=agora.replace(minute=0,second=0,microsecond=0)+dt.timedelta(hours=1)
    out={}
    for i,raw in enumerate(hourly["time"]):
        h=dt.datetime.fromisoformat(raw).replace(tzinfo=TZ)
        if first<=h<first+dt.timedelta(hours=24):
            x={k:hourly[k][i] for k in ("precipitation","wind_gusts_10m","weather_code")}
            if any(v is None or not math.isfinite(float(v)) or float(v)<0 for v in x.values()):
                raise ValueError("Previsão incompleta")
            out[h]=x
    if len(out)!=24:raise ValueError("Janela horária incompleta")
    return out

def sinais(h):
    resultado=[]
    for instante,r in sorted(h.items()):
        def adicionar(tipo,val,unidade,dur=1):
            resultado.append({"tipo":tipo,"inicio":instante.isoformat(),
                "fim":(instante+dt.timedelta(hours=dur)).isoformat(),
                "valor":round(float(val),1),"unidade":unidade})
        w=int(r["weather_code"])
        if w in (95,96,99):adicionar("temporal",w,"WMO")
        if w in (96,99):adicionar("granizo",w,"WMO")
        if r["wind_gusts_10m"]>=60:adicionar("vento",r["wind_gusts_10m"],"km/h")
        if r["precipitation"]>=20:adicionar("chuva",r["precipitation"],"mm em 1h")
        for n,lim in ((3,30),(24,50)):
            janela=[h.get(instante+dt.timedelta(hours=k)) for k in range(n)]
            if all(janela):
                mm=sum(z["precipitation"] for z in janela)
                if mm>=lim:adicionar("chuva",mm,f"mm em {n}h",n)
    return resultado

def verificar():
    agora=dt.datetime.now(TZ)
    # INMET é obrigatório: em falha, encerrar sem publicação.
    oficiais=avisos_inmet(agora)
    try:
        defesa=obter("https://www.defesacivil.rj.gov.br/").status_code
    except requests.RequestException:
        defesa=None  # Fonte contextual, sem direito de validar o evento.
    respostas=[]
    for modelo in MODELOS:
        params={"latitude":",".join(str(c[1]) for c in REGIOES),
                "longitude":",".join(str(c[2]) for c in REGIOES),
                "hourly":"precipitation,wind_gusts_10m,weather_code",
                "models":modelo,"timezone":"America/Sao_Paulo",
                "forecast_days":3,"wind_speed_unit":"kmh",
                "precipitation_unit":"mm"}
        j=obter(API,params).json()
        if not isinstance(j,list) or len(j)!=len(REGIOES):
            raise ValueError("Cobertura de modelos incompleta")
        respostas.append(j)
    eventos=[]
    for i,(local,_,_) in enumerate(REGIOES):
        aa,bb=[sinais(horas(respostas[k][i],agora)) for k in range(2)]
        for e in aa:
            pares=[b for b in bb if b["tipo"]==e["tipo"] and b["unidade"]==e["unidade"]
                    and max(e["inicio"],b["inicio"])<min(e["fim"],b["fim"])]
            if pares:
                b=max(pares,key=lambda x:x["valor"])
                eventos.append(dict(e,local=local,fonte="ICON + GFS",
                                    valor=min(e["valor"],b["valor"])))
    eventos.sort(key=lambda e:(-PRIORIDADE[e["tipo"]],-e["valor"],e["inicio"]))
    if oficiais:
        niveis={"Extreme":3,"Severe":2,"Moderate":1}
        oficiais.sort(key=lambda a:(-niveis.get(a["severidade"],0),-PRIORIDADE[a["tipo"]]))
        o=oficiais[0]
        eventos.insert(0,o)
    rel={"emitido_em":agora.isoformat(),"data":agora.date().isoformat(),
         "canal":"@previsaorj","eventos":eventos,"publicar":bool(eventos),
         "avisos_oficiais":oficiais,"modelos":list(MODELOS),
         "defesa_civil_http":defesa,"cidades_consultadas":len(REGIOES)}
    p=Path("output/plantao_rj/consulta.json")
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(rel,ensure_ascii=False,indent=2))
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"],"a") as f:
            f.write("publicar="+str(rel["publicar"]).lower()+"\n")
    print(json.dumps({"publicar":rel["publicar"],"eventos":len(eventos),
        "avisos":len(oficiais),"defesa_civil":defesa}))
    return rel

if __name__=="__main__":
    verificar()
