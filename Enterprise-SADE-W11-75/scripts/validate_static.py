#!/usr/bin/env python3
import json,re,pathlib
root=pathlib.Path(__file__).resolve().parent.parent
lab=root/'lab'
m=json.loads((root/'topology.json').read_text())
assert len(m['devices'])==75
conf=(lab/'lab.conf').read_text()
for d in m['devices']:
    assert (lab/(d+'.startup')).exists(),d
    assert (lab/d).is_dir(),d
    assert f'{d}[image]=' in conf,d
    for i in range(len([a for a in m['links'] if a['a']==d or a['b']==d])):
        assert f'{d}[{i}]=' in conf,(d,i)
for kind,total in m['counts'].items():print(kind,total)
print('STATIC PASS: 75 devices; images, interfaces, startup files exist')
