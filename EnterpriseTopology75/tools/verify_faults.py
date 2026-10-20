#!/usr/bin/env python3
"""Exercise three faults, always repairing before moving to the next case."""
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import time

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import lab

results=[]

def require(title,node,command):
    ok,out=lab.execute(node,command)
    results.append({'check':title,'node':node,'passed':ok,'output':out})
    print(('PASS ' if ok else 'FAIL ')+title,flush=True)
    if not ok: raise RuntimeError(title+': '+out)

def application(title):
    require(title,'staff','curl -fsS --max-time 6 http://app.enterprise.test/ | grep -F "app: healthy"')

def main():
    try:
        application('Baseline application and database dependency')
        for name,(node,inject,repair) in lab.FAULTS.items():
            try:
                require(name+': inject',node,inject)
                time.sleep(7)
                if name=='core-uplink':
                    require('Uplink is administratively down','r5',"ip -j link show eth0 | python3 -c 'import sys,json; assert \"UP\" not in json.load(sys.stdin)[0][\"flags\"]'")
                    require('R5 retains two Full neighbors','r5',"test \"$(vtysh -c 'show ip ospf neighbor' | grep -c Full)\" -eq 2")
                    application('Application survives core uplink failure')
                elif name=='gateway-service':
                    require('Primary VRRP process stopped','r5','! pgrep keepalived')
                    require('Backup owns staff virtual gateway','r6',"ip -4 addr | grep -F '10.10.10.1/24'")
                    require('Primary released staff virtual gateway','r5',"! ip -4 addr | grep -F '10.10.10.1/24'")
                    application('Application survives gateway takeover')
                else:
                    require('Injected database ACL exists','app','iptables -C OUTPUT -d 10.30.20.10 -p tcp --dport 8080 -j REJECT')
                    require('Application reports backend failure','office',"test \"$(curl -s --max-time 6 -o /tmp/fault-body -w '%{http_code}' http://app.enterprise.test/)\" = 503 && grep -F 'database dependency unavailable' /tmp/fault-body")
                    require('Database remains healthy from operations','ops','curl -fsS --max-time 5 http://10.30.20.10:8080/ | grep -F "database: healthy"')
            finally:
                require(name+': repair',node,repair)
                time.sleep(7)
            application(name+': recovered application')
        return 0
    except RuntimeError as e:
        print(str(e),file=sys.stderr);return 1
    finally:
        report={'timestamp':datetime.now(timezone.utc).isoformat(),'passed':bool(results) and all(r['passed'] for r in results),'checks':results}
        (lab.ROOT/'results/fault-verification.json').write_text(json.dumps(report,indent=2)+'\n')

if __name__=='__main__': sys.exit(main())
