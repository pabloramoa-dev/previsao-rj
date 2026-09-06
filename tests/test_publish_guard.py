from src.previsao_rj.publish.instagram import caption_hash

def test_caption_hash_stable_whitespace():
    assert caption_hash('a  b') == caption_hash('a b')
