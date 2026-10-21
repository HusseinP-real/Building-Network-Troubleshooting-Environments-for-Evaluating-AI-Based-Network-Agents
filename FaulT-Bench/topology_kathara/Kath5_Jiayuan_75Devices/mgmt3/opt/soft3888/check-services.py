"""Active management probes; run after routing convergence."""
import json, subprocess, sys
checks = [('internal-dns', ['dig','@192.168.251.11','app.internal.test','+short','+time=2','+tries=1'], '192.168.251.12'),
          ('internal-http',['curl','--noproxy','*','-fsS','--max-time','4','http://192.168.251.12/'], 'SOFT3888 Internal Application'),
          ('dmz-http',['curl','--noproxy','*','-fsS','--max-time','4','http://192.168.231.11/'], '<')]
results=[]
for name, command, expected in checks:
    p=subprocess.run(command, capture_output=True,text=True,timeout=8)
    results.append(dict(name=name, rc=p.returncode, output=p.stdout+p.stderr, passed=p.returncode==0 and expected in p.stdout))
print(json.dumps({'passed':all(x['passed'] for x in results),'checks':results}))
sys.exit(0 if all(x['passed'] for x in results) else 1)
