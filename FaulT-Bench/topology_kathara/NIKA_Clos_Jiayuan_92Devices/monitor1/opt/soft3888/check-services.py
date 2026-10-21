import json, subprocess, sys
checks=[('dns',['dig','@10.0.0.2','api.nika.test','+short','+time=1','+tries=1'],'10.0.1.80'),
        ('app',['curl','--noproxy','*','-fsS','--max-time','3','http://10.0.1.80:8080/'],'SOFT3888 NIKA Backend')]
rows=[]
for name,command,expected in checks:
    p=subprocess.run(command,text=True,capture_output=True,timeout=8)
    rows.append(dict(name=name,rc=p.returncode,output=p.stdout+p.stderr,passed=p.returncode==0 and expected in p.stdout))
print(json.dumps(dict(passed=all(x['passed'] for x in rows),checks=rows)))
sys.exit(0 if all(x['passed'] for x in rows) else 1)
