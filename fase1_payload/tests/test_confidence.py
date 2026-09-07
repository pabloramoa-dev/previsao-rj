"""Score de confianca — Plano Mestre, secao 5.2."""
from __future__ import annotations

from src.previsao_rj.quality import confidence as conf


def test_pesos_somam_cem():
    assert sum(conf.WEIGHTS.values()) == 100
    assert conf.WEIGHTS == {"model_agreement": 30, "run_recency": 20,
                            "temporal_consistency": 15, "observation_match": 20,
                            "spatial_fit": 15}


def test_modelos_que_concordam_pontuam_mais_que_modelos_divergentes():
    juntos = {"a": {"max_c": 30.0, "rain_probability_pct": 60},
              "b": {"max_c": 30.4, "rain_probability_pct": 63}}
    brigando = {"a": {"max_c": 27.0, "rain_probability_pct": 20},
                "b": {"max_c": 34.0, "rain_probability_pct": 85}}
    assert conf.model_agreement(juntos)[0] > conf.model_agreement(brigando)[0]
    assert conf.model_agreement(brigando)[0] < 8


def test_um_modelo_so_nao_conta_como_concordancia():
    valor, nota = conf.model_agreement({"a": {"max_c": 30, "rain_probability_pct": 50}})
    assert valor < conf.WEIGHTS["model_agreement"] / 2
    assert "so um modelo" in nota


def test_dado_velho_perde_pontos_ate_zerar():
    novo = conf.run_recency(5, 120)[0]
    meio = conf.run_recency(60, 120)[0]
    vencido = conf.run_recency(180, 120)[0]
    assert novo > meio > vencido == 0.0


def test_sem_observacao_o_criterio_vale_zero_e_fica_registrado():
    valor, nota = conf.observation_match("not_collected")
    assert valor == 0.0
    assert "sem observacao" in nota


def test_microclima_pontua_menos_que_bairro_representativo():
    assert conf.spatial_fit(["alto", "alto"])[0] > conf.spatial_fit(["baixo", "baixo"])[0]


def test_sem_snapshot_anterior_nao_premia_nem_pune():
    valor, nota = conf.temporal_consistency(None, {"max_c": 30, "rain_probability_pct": 50})
    assert valor == conf.WEIGHTS["temporal_consistency"] / 2
    assert "sem snapshot anterior" in nota


def test_virada_grande_entre_rodadas_derruba_a_consistencia():
    anterior = {"max_c": 24, "rain_probability_pct": 10}
    atual = {"max_c": 34, "rain_probability_pct": 90}
    assert conf.temporal_consistency(anterior, atual)[0] < 2


def test_cortes_de_linguagem_e_de_alerta():
    assert conf.level(80) == "alta"
    assert conf.level(conf.MIN_FOR_CATEGORICAL) == "media"
    assert conf.level(conf.MIN_FOR_ALERT) == "baixa"
    assert conf.level(conf.MIN_FOR_ALERT - 1) == "insuficiente"


def test_snapshot_real_produz_score_com_gates(snapshot):
    c = snapshot["confidence"]
    assert 0 <= c["score"] <= 100
    assert set(c["parts"]) == set(conf.WEIGHTS)
    assert c["gates"]["allow_categorical_language"] is (c["score"] >= conf.MIN_FOR_CATEGORICAL)
    assert c["gates"]["allow_alert_reel"] is (c["score"] >= conf.MIN_FOR_ALERT)
    # Sem observacao ligada, o teto honesto do sistema hoje e 80.
    assert c["parts"]["observation_match"] == 0.0
    assert c["score"] <= 80


def test_score_do_snapshot_e_estavel(collected, tier1_locations):
    from src.previsao_rj.normalizers import snapshot as snap
    a = snap.build(collected, tier1_locations)["confidence"]
    b = snap.build(collected, tier1_locations)["confidence"]
    assert a["score"] == b["score"] and a["parts"] == b["parts"]
