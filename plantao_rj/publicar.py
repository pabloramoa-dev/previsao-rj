"""Publicação independente RJ: Meta Graph, Reel + Story, recibos por evento."""
import argparse
import json
import os
import re
import time
from datetime import datetime,timedelta
from pathlib import Path
from urllib.parse import urlparse
from zoneinfo import ZoneInfo
import requests

BASE_OUT=Path("output/plantao_rj")
STATE=Path("data/plantao_rj_publicacoes.json")
TZ=ZoneInfo("America/Sao_Paulo")

def api_obj(resp):
    try:data=resp.json()
    except ValueError:raise RuntimeError("Meta não respondeu com JSON")
    if not resp.ok or "error" in data:
        err=data.get("error",{})
        raise RuntimeError("Meta: "+str(err.get("message",resp.status_code))[:180])
    return data

def publicar(url):
    u=urlparse(url)
    repo=os.environ.get("GITHUB_REPOSITORY","")
    if u.scheme!="https" or u.netloc!="github.com" or not u.path.startswith("/"+repo+"/releases/download/"):
        raise ValueError("URL de mídia não pertence ao release deste repositório")
    rel=json.loads((BASE_OUT/"consulta.json").read_text(encoding="utf-8"))
    agora=datetime.now(TZ)
    emitido=datetime.fromisoformat(rel["emitido_em"])
    if not rel["publicar"] or not rel["eventos"] or not timedelta(0)<=agora-emitido<=timedelta(hours=2):
        raise ValueError("Relatório ausente, não aprovado ou vencido")
    e=rel["eventos"][0]
    if datetime.fromisoformat(e["fim"])<=agora:raise ValueError("Aviso expirado")
    if e["tipo"]=="ciclone" and e.get("fonte")!="INMET":raise ValueError("Ciclone sem fonte oficial")
    legenda=(BASE_OUT/"LEGENDA.txt").read_text(encoding="utf-8")
    if not legenda or len(legenda)>2200 or "@previsaorj" not in legenda:
        raise ValueError("Legenda inválida")
    token=os.environ.get("IG_ACCESS_TOKEN","").strip()
    uid=os.environ.get("IG_USER_ID","").strip()
    if not uid.isdecimal() or not token:raise ValueError("Secrets IG indisponíveis")
    versao=os.environ.get("META_GRAPH_VERSION","v26.0")
    if not re.fullmatch(r"v\d+\.\d+",versao):raise ValueError("Versão da API inválida")
    host="graph.facebook.com" if token.startswith("EAA") else "graph.instagram.com"
    base=f"https://{host}/{versao}"
    header={"Authorization":"Bearer "+token}
    def get(path,fields):
        return api_obj(requests.get(f"{base}/{path}",params={"fields":fields},headers=header,timeout=35))
    def post(path,form):
        return api_obj(requests.post(f"{base}/{path}",data=form,headers=header,timeout=80))
    conta=get(uid,"id,username")
    if str(conta.get("id"))!=uid or conta.get("username","").lower()!="previsaorj":
        raise ValueError("Conta da Meta não corresponde a @previsaorj")
    # Chave lógica estável por aviso/evento; reexecução no mesmo dia não duplica.
    chave=rel["data"]+":"+e["tipo"]+":"+e["local"]+":"+str(e.get("aviso_id") or e["inicio"])
    STATE.parent.mkdir(parents=True,exist_ok=True)
    estado=json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else {}
    registro=estado.setdefault(chave,{})
    def salvar():
        t=STATE.with_suffix(".tmp")
        t.write_text(json.dumps(estado,ensure_ascii=False,indent=2),encoding="utf-8")
        t.replace(STATE)
    for tipo in ("REELS","STORIES"):
        if registro.get(tipo):
            print(tipo,"já publicado:",registro[tipo]);continue
        ck=tipo+"_container"
        if not registro.get(ck):
            req={"media_type":tipo,"video_url":url}
            if tipo=="REELS":req.update(caption=legenda,share_to_feed="true")
            registro[ck]=str(post(uid+"/media",req)["id"])
            salvar()
        cid=registro[ck]
        for tentativa in range(75):
            status=get(cid,"status_code").get("status_code")
            if status=="FINISHED":break
            if status=="PUBLISHED":
                registro[tipo]={"container_publicado":cid}
                salvar()
                break
            if status in ("ERROR","EXPIRED"):raise RuntimeError("Meta "+tipo+": "+status)
            time.sleep(5)
        else:raise TimeoutError("Meta não processou "+tipo)
        if registro.get(tipo):continue
        result=post(uid+"/media_publish",{"creation_id":cid})
        mid=str(result.get("id",""))
        if not mid:raise RuntimeError("Meta não retornou media_id")
        registro[tipo]=mid
        salvar()
        print(tipo,"media_id",mid)
    print("RESULTADO",json.dumps(registro,ensure_ascii=False))

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--url",required=True)
    args=ap.parse_args()
    publicar(args.url)
