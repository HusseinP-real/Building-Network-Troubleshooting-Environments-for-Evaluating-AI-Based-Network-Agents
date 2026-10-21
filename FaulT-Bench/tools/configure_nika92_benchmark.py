#!/usr/bin/env python3
"""Render four cases against the exported NIKA reference's real peer/address map."""
from pathlib import Path
import json
import shlex

ROOT=Path(__file__).resolve().parents[1]
TOPO='NIKA_Clos_Jiayuan_92Devices'
LAB=ROOT/'topology_kathara'/TOPO
PLAN=json.loads((LAB/'address-plan.json').read_text())
CASES=ROOT/'dataset/nika92_Q/custom'
EST='vtysh -c "show bgp ipv4 unicast summary json" | python3 -c \'import json,sys; d=json.load(sys.stdin); print(sum(p.get("state")=="Established" for p in d.get("ipv4Unicast",d).get("peers",{}).values()))\''

def check(device,command,expect):return dict(device=device,command=command,expect=str(expect))
def http(device,ip='10.0.1.80',port=8080,code=200):
    command=f"curl --noproxy '*' -sS --max-time 3 -o /dev/null -w '%{{http_code}}' http://{ip}:{port}/"
    if str(code)=='000':command+=' 2>/dev/null || { rc=$?; test "$rc" = 7 || test "$rc" = 28; }'
    return check(device,command,str(code))
def ping(device,ip):return check(device,f'ping -n -c1 -W1 {ip}','0% loss')
def dns(device,name='api.nika.test',answer='10.0.1.80',server='10.0.0.2',tcp=False):
    return check(device,f'dig @{server} {name} +short +time=1 +tries=1'+(' +tcp' if tcp else ''),'equals: '+answer)
def cli(*commands):return 'vtysh '+' '.join('-c '+shlex.quote(c) for c in commands)
def lines(checks):return '\n'.join(f"{c['device']}  {c['command']}  => expect {c['expect']}" for c in checks)
def scenario(sid,device,family,prompt,pre,inject,post,recovery,truth,trigger=None):
    text=f'''Scenario: {sid}
Topology: {TOPO}
Validation: strict
Fault family: {family}

[PROMPT-TO-AGENT]
{prompt}

[PRE-CHECK]
{lines(pre)}

[INJECTION]
device: {device}
action: {family}
cmd: |
'''+''.join('  '+line+'\n' for line in inject.splitlines())
    if trigger:text+=f'\n[TRIGGER]\ndevice: {trigger}\naction: renew the real DHCP lease\ncmd: sh /opt/soft3888/dhcp-client renew\n'
    text+=f'''
[POST-INJECT-CHECK]
{lines(post)}

[GROUND-TRUTH]
Fault location: {device}
Fault type: {family}
Root cause, expected symptoms and controls: {truth}

[FIX]
On {device}, execute:
{recovery}
'''
    if trigger:text+=f'Renew {trigger} afterwards: sh /opt/soft3888/dhcp-client renew\n'
    text+=f'''
[RECOVERY]
device: {device}
action: restore healthy configuration
cmd: |
'''+''.join('  '+line+'\n' for line in recovery.splitlines())+f'''
[RECOVERY-CHECK]
{lines(pre)}

[DIAGNOSTIC-PROCESS]
Scope the affected NIKA pod/service, compare an unaffected pod and local
connectivity, inspect the owning configuration and protocol/service state.
The explicit recovery is applied inside disposable containers only; validate
the complete healthy baseline before the next case.

[SCORING-AXES]
assert-identifies: {device}
must-identify-device: {device}
must-identify-component: {family}
must-identify-mechanism: {truth}

[NIKA-LABEL]
nika_label: not assigned
nika_category: MISCONFIGURATION
in_taxonomy: not verified
note: Project-local case on the exported pinned DCClosService(l); no exact taxonomy equivalence claimed.
'''
    return sid,text


def render():
    cases=[]
    leaf='leaf_router_0_1';r=PLAN['routers'][leaf]
    def set_as(bad):
        commands=['conf t',f"router bgp {r['asn']}"]+[f"neighbor {p['address']} remote-as {65999 if bad else p['asn']}" for p in r['peers']]+['end']
        # Guard each neighbor: repeated remote-as commands can unnecessarily reset sessions.
        payload=cli(*commands)
        return "config=$(vtysh -c 'show running-config') || exit $?\n"+"n=$(printf '%s\\n' \"$config\" | awk '$1==\"neighbor\" && $3==\"remote-as\" && $4==65999 {n++} END {print n+0}') || exit $?\n"+f'case "$n" in\n  {4 if bad else 0}) echo "Already in requested AS state" ;;\n  {0 if bad else 4}) {payload} ;;\n  *) echo "Unexpected partial AS state" >&2; exit 2 ;;\nesac'
    pre=[check(leaf,EST,4),http('client_1','10.0.1.2',80),ping('webserver0_pod0','10.0.1.1'),http('client_2','10.2.1.2',80)]
    post=[check(leaf,EST,0),http('client_1','10.0.1.2',80,'000'),ping('webserver0_pod0','10.0.1.1'),http('client_2','10.2.1.2',80)]
    cases.append(scenario('nika92-pod0-leaf1-wrong-remote-as',leaf,'BGP remote AS mismatch',
        'External clients cannot open web0.pod0, although the server reaches its local gateway. A web service in pod2 still works. Diagnose the affected path.',pre,set_as(True),post,set_as(False),
        'All four peers on leaf_router_0_1 incorrectly expect AS65999 instead of the reference spine AS65100/65101/65102/65103. The four sessions fail and remote access to 10.0.1.2 is lost. Local web/gateway connectivity and pod2 HTTP remain healthy. Restore each specific neighbor AS; do not replace all with one AS.'))
    leaf='leaf_router_1_1';r=PLAN['routers'][leaf]
    inject=cli('conf t','ip prefix-list NIKA92_BLOCK seq 5 deny 10.1.1.0/24','ip prefix-list NIKA92_BLOCK seq 100 permit 0.0.0.0/0 le 32',f"router bgp {r['asn']}",'address-family ipv4 unicast',*[f"neighbor {p['address']} prefix-list NIKA92_BLOCK out" for p in r['peers']],'end','clear bgp * soft out')
    recover=cli('conf t',f"router bgp {r['asn']}",'address-family ipv4 unicast',*[f"no neighbor {p['address']} prefix-list NIKA92_BLOCK out" for p in r['peers']],'exit-address-family','exit','no ip prefix-list NIKA92_BLOCK','end','clear bgp * soft out')
    pre=[check(leaf,EST,4),http('client_1','10.1.1.2',80),dns('client_1','web0.pod1','10.1.1.2'),http('client_2','10.2.1.2',80)]
    post=[check(leaf,EST,4),http('client_1','10.1.1.2',80,'000'),dns('client_1','web0.pod1','10.1.1.2'),http('client_2','10.2.1.2',80),ping('webserver0_pod1','10.1.1.1'),check('super_spine_router_1','ip route show 10.1.1.0/24 | wc -l',0)]
    cases.append(scenario('nika92-pod1-leaf1-service-prefix-filter',leaf,'BGP outbound service-prefix rejection','The name web0.pod1 resolves but remote HTTP fails. Its leaf still has established BGP sessions and pod2 services work. Locate the configuration error.',pre,inject,post,recover,'An outbound prefix-list on all four leaf_router_1_1 peers blocks the reference service LAN 10.1.1.0/24. Sessions remain Established; remote routers lose this prefix. DNS on another reference leaf, local gateway and pod2 HTTP remain healthy. Remove the specific policy from all four neighbors and refresh advertisements.'))
    pre=[check('client_0',"ip route show default | awk '{print $3}'",'equals: 192.168.0.1'),http('client_0'),ping('client_0','192.168.0.1'),http('client_1')]
    post=[check('client_0',"ip route show default | awk '{print $3}'",'equals: 192.168.0.254'),http('client_0',code='000'),ping('client_0','192.168.0.1'),http('client_1'),check('dhcp1',"awk '$0==\"dhcp-option=option:router,192.168.0.254\" {n++} END {print n+0}' /etc/dnsmasq.d/clos.conf",1)]
    cases.append(scenario('nika92-dhcp1-wrong-router-option','dhcp1','DHCP incorrect default-router option','External client_0 loses remote service access after renewing, but its real gateway responds. The static external client_1 still reaches the application. Determine why the renewed client route is wrong.',pre,"set -eu\nsed -i 's/option:router,192.168.0.1$/option:router,192.168.0.254/' /etc/dnsmasq.d/clos.conf\nsh /opt/soft3888/dns-control restart",post,"set -eu\nsed -i 's/option:router,192.168.0.254$/option:router,192.168.0.1/' /etc/dnsmasq.d/clos.conf\nsh /opt/soft3888/dns-control restart",'Added dhcp1 advertises unused 192.168.0.254 instead of the original super_spine_router_0 gateway 192.168.0.1. Real lease renewal installs the wrong default route while preserving original client_0 IP 192.168.0.2. Local gateway and another external client remain healthy. Correct the DHCP router option and renew client_0, rather than patching only its route.',trigger='client_0'))
    pre=[http('client_1'),http('client_1','10.0.1.2',80),http('client_1','10.0.2.2',80),http('client_1','10.0.3.2',80),dns('client_1')]
    post=[http('client_1',code=503)]+pre[1:]
    cases.append(scenario('nika92-lb1-wrong-backend-ports','lb1','HTTP load-balancer backend port misconfiguration','The application returns HTTP503, although the three NIKA web backends open directly and DNS works. Diagnose the application delivery failure.',pre,"set -eu\nsed -i -E '/^[[:space:]]*server web[123] /s/:80 /:81 /' /etc/haproxy/haproxy.cfg\nsh /opt/soft3888/lb-control restart",post,"set -eu\nsed -i -E '/^[[:space:]]*server web[123] /s/:81 /:80 /' /etc/haproxy/haproxy.cfg\nsh /opt/soft3888/lb-control restart",'Added lb1 forwards to port81 on 10.0.1.2, 10.0.2.2 and 10.0.3.2, while the original NIKA web services listen on port80. HAProxy health checks mark all configured backends down, returning HTTP503. Direct HTTP to all three backends and DNS remain healthy; restore port80 and restart the load balancer.'))
    baseline=[check(name,EST,len(r['peers'])) for name,r in PLAN['routers'].items()]
    # Every reference web endpoint is checked remotely, including last leaf of every pod.
    for pod in range(4):
        probe=f'client_{(pod+1)%4}'
        for web in range(7):baseline.append(http(probe,f'10.{pod}.{web+1}.2',80))
        baseline += [dns(probe,f'web6.pod{pod}',f'10.{pod}.7.2',f'10.{pod}.0.2'),dns(probe,server=f'10.{pod}.0.2',tcp=True)]
    baseline += [http(f'client_{p}') for p in range(4)]
    baseline += [check('client_0',"ip -4 -o addr show eth0 | awk '{print $4}'",'equals: 192.168.0.2/24'),check('client_0',"ip route show default | awk '{print $3}'",'equals: 192.168.0.1'),http('monitor1',port=9090,code=200),http('client_1',port=9090,code=403)]
    # HAProxy stats needs its actual path, not /.
    for c in baseline:
        if ':9090/' in c['command']:c['command']=c['command'].replace(':9090/',':9090/stats')
    baseline += [check(n,"python3 /opt/soft3888/check-services.py | python3 -c 'import json,sys; print(int(json.load(sys.stdin)[\"passed\"]))'",1) for n in ['monitor1','monitor2']]
    baseline += [check('client_1',"curl --noproxy '*' -fsS --max-time 3 http://web6.pod3/ | grep -c 'SOFT3888 NIKA Backend webserver6_pod3'",1)]
    aux=[dict(name='pod2-leaf7-single-uplink-failover',injection=dict(device='leaf_router_2_7',action='disable one of four reference uplinks',command='ip link set eth0 down'),checks=[check('leaf_router_2_7',EST,3),http('client_1','10.2.7.2',80),http('monitor1')],recovery=dict(device='leaf_router_2_7',action='restore original uplink',command='ip link set eth0 up'),recovery_checks=[check('leaf_router_2_7',EST,4)])]
    benchmark=dict(devices=92,collision_domains=228,images=['soft3888/frr:10.5.3-v1','soft3888/host:bookworm-v1'],baseline=baseline,scenarios=[sid for sid,_ in cases],auxiliary=aux,mcp_probe=dict(host='client_1',destination='10.0.1.80',router='leaf_router_0_7',route='10.0.1.0/24'))
    outputs={CASES/(sid+'.txt'):text for sid,text in cases}
    outputs[LAB/'benchmark.json']=json.dumps(benchmark,indent=2)+'\n'
    outputs[ROOT/'faultbench/benchmarks/nika92.csv']='scenario\n'+'\n'.join(sid for sid,_ in cases)+'\n'
    return outputs

if __name__=='__main__':
    outputs=render()
    for p,text in outputs.items():
        if p.exists() and p.read_text()!=text:raise SystemExit(f'Refusing changed file {p}')
    for p,text in outputs.items():p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text)
    print(f'Rendered 4 scenarios and {len(json.loads((LAB/"benchmark.json").read_text())["baseline"])} baseline checks')
