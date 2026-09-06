from __future__ import annotations
import json, subprocess, sys
p=sys.argv[1]
r=subprocess.run(['ffprobe','-v','error','-show_streams','-show_format','-of','json',p],capture_output=True,text=True,check=True)
j=json.loads(r.stdout)
vs=[s for s in j['streams'] if s.get('codec_type')=='video']
as_=[s for s in j['streams'] if s.get('codec_type')=='audio']
assert vs, 'sem stream de vídeo'
v=vs[0]
assert int(v['width'])==1080 and int(v['height'])==1920, f"resolução inválida {v['width']}x{v['height']}"
assert v.get('codec_name')=='h264', f"codec inválido {v.get('codec_name')}"
assert as_, 'sem áudio'
d=float(j['format']['duration'])
assert 12 <= d <= 40, f'duração fora do gate: {d}'
print(json.dumps({'ok':True,'width':v['width'],'height':v['height'],'video_codec':v['codec_name'],'audio_codec':as_[0].get('codec_name'),'duration':round(d,2)},ensure_ascii=False))
