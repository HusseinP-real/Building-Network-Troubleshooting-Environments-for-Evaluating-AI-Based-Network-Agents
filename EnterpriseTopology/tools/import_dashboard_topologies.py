"""Export teammate topology inventories from a Git ref without changing checkout."""
import argparse
import collections
import io
import json
from pathlib import Path
import re
import subprocess
import tarfile
import xml.etree.ElementTree as ET

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / 'EnterpriseTopology/dashboard/topologies'
SPECS = [
 ('datacenter-fabric', 'Data Centre Fabric · 39 devices', 'DatacenterFabric', '.', ['healthy','uplink','wrong-gateway','backend-link','withdrawal','compound'], 'eBGP · ECMP'),
 ('multi-as-isp', 'Multi-AS ISP Backbone · 75 devices', 'Multi-AS-ISP-Backbone-W11-75', 'lab', [f'S{i:02}' for i in range(1,9)], 'IS-IS · OSPF · iBGP · eBGP'),
 ('multisite', 'Multi-Site Enterprise · 80 devices', 'MultiSite_BGP_OSPF_Benchmark', '.', ['F01','F02','F03'], 'OSPF · eBGP'),
 ('jiayuan-75', 'Jiayuan Enterprise · 75 devices', 'FaulT-Bench/topology_kathara/Kath5_Jiayuan_75Devices', '.', [], 'OSPF · EIGRP · DNS · HTTP'),
 ('nika-92', 'NIKA Clos · 92 devices', 'FaulT-Bench/topology_kathara/NIKA_Clos_Jiayuan_92Devices', '.', [], 'BGP · DHCP · DNS · HAProxy'),
 ('missing-return-route', 'Missing Return Route · micro lab', 'kathara_scenario/missing_return_route', '.', ['missing-return-route'], 'Static routing'),
 ('abilene', 'Abilene · IS-IS backbone', 'SOFT3888_Abilene_YUMAng_Deliverable', '.', ['link-failure'], 'IS-IS'),
]

def export(ref):
 commit = subprocess.check_output(['git','rev-parse',ref],cwd=REPO,text=True).strip()
 archive = subprocess.check_output(['git','archive',commit],cwd=REPO)
 with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
  files = {m.name:tar.extractfile(m).read() for m in tar.getmembers() if m.isfile()}
 def read(path): return files.get(str(path),b'').decode('utf-8',errors='replace')
 catalog=[]
 for key,name,source,labpath,cases,protocols in SPECS:
  base=Path(source); labbase=base if labpath=='.' else base/labpath
  nodes={}; domains=collections.defaultdict(list); links=[]
  roles=json.loads(read(base/'roles.json') or '{}')
  for node,port,domain in re.findall(r'^([\w-]+)\[(\d+)\]\s*=\s*["\x27]?([\w.-]+)',read(labbase/'lab.conf'),re.M):
   startup=read(labbase/(node+'.startup')); config=read(labbase/node/'etc/frr/frr.conf')
   role='router' if node in roles.get('routers',[]) or 'router ' in config or 'vtysh' in startup or 'ip_forward=1' in startup or 'ip_forward = 1' in startup else 'switch' if 'brctl' in startup or 'type bridge' in startup else 'host'
   nodes.setdefault(node,{'role':role,'ports':[]})
   domains[domain].append({'node':node,'interface':'eth'+port})
  if key=='datacenter-fabric':
   original=json.loads(read(base/'inventory.json'))
   nodes=original['nodes'];links=original['links']
   for n in nodes.values():
    n['source_role']=n['role'];n['role']={'spine':'router','leaf':'router','server':'host','client':'host'}.get(n['role'],n['role'])
  elif key=='abilene':
   root=ET.fromstring(files[str(base/'topology/network.xml')]); ns={'n':'http://sndlib.zib.de/network'}
   nodes={n.attrib['id']:{'role':'router','ports':[]} for n in root.findall('.//n:networkStructure/n:nodes/n:node',ns)}
   for link in root.findall('.//n:networkStructure/n:links/n:link',ns):
    a=link.find('n:source',ns).text;b=link.find('n:target',ns).text
    links.append({'name':link.attrib['id'],'kind':'routed','endpoints':[{'node':a,'interface':link.attrib['id']},{'node':b,'interface':link.attrib['id']}]})
  else:
   for domain,endpoints in domains.items():
    # A shared collision domain is a LAN, not a fabricated mesh of direct wires.
    if len(endpoints)>2:
     hub='lan:'+domain;nodes[hub]={'role':'switch','source_role':'shared LAN','virtual':True,'ports':[]}
     for i,endpoint in enumerate(endpoints):links.append({'name':domain+':'+str(i),'kind':'lan','endpoints':[endpoint,{'node':hub,'interface':'port'+str(i)}]})
    elif len(endpoints)==2:links.append({'name':domain,'kind':'routed','endpoints':endpoints})
  device_count = sum(not n.get('virtual') for n in nodes.values())
  if device_count < 75:
   (OUT/(key+'.json')).unlink(missing_ok=True)
   print(key, 'excluded:', device_count, 'devices (minimum 75)')
   continue
  saved_ports={name:{p['interface']:p for p in n.get('ports',[])} for name,n in nodes.items()}
  for n in nodes.values():n['ports']=[]
  for link in links:
   a,b=link['endpoints']
   for own,peer in [(a,b),(b,a)]:
    port={**saved_ports.get(own['node'],{}).get(own['interface'],{}),'interface':own['interface'],'peer':peer['node'],'kind':link['kind'],'link':link['name']}
    startup=read(labbase/(own['node']+'.startup'))
    addresses=re.findall(r'ip (?:-4 )?addr(?:ess)? (?:add|replace) ([\d./]+) dev '+re.escape(own['interface'])+r'\b',startup)
    if addresses:port['address']=addresses[0]
    nodes[own['node']]['ports'].append(port)
  if key in ('jiayuan-75','nika-92'):
   folder='jiayuan75_Q' if key=='jiayuan-75' else 'nika92_Q'
   cases=[Path(p).stem for p in files if p.startswith('FaulT-Bench/dataset/'+folder+'/custom/') and p.endswith('.txt')]
  data={'nodes':nodes,'links':links,'layout':'generic','protocols':protocols,'source_path':source,'source_commit':commit,'scenarios':cases,'scenario_count':len(cases),'evaluation_enabled':False,'note':'Imported from main · exploration and scenario catalog · live evaluation adapter pending','health':None}
  assert nodes and links, source
  OUT.mkdir(parents=True,exist_ok=True);(OUT/(key+'.json')).write_text(json.dumps(data,indent=2)+'\n')
  catalog.append({'id':key,'name':name,'inventory':key+'.json','scenario_count':len(cases),'evaluation_enabled':False})
  print(key, sum(not n.get('virtual') for n in nodes.values()),'devices',len(links),'drawn edges')
 (OUT/'catalog.json').write_text(json.dumps(catalog,indent=2)+'\n')

if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--ref',default='origin/main');export(parser.parse_args().ref)
