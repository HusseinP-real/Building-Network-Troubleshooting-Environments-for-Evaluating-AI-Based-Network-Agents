#!/usr/bin/env python3
"""Report runtime prerequisites and credential presence only; never print values."""
from pathlib import Path
import argparse,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'faultbench/src'))
from faultbench.ground_truth import build
from faultbench.preflight import missing_credentials

def check():
    d=build();result=dict(kind='environment-and-team-integration-preflight',missing_credentials=missing_credentials(['sade','react-full']),topologies=[],docker_error=None)
    try:
        import docker
        from contextlib import closing
        with closing(docker.from_env()) as client:
            result['docker_version']=client.version()['Version'];result['storage_driver']=client.info()['Driver']
            available={tag for image in client.images.list() for tag in image.tags}
            for t in d['topologies']:
                result['topologies'].append(dict(topology=t['topology'],devices=t['devices'],inventory_complete=t['inventory_complete'],missing_images=[i for i in t['images'] if i not in available and i+':latest' not in available],current_live_cases=t['live_validated_scenarios'],legacy_validation_gaps=t['scenarios_with_validation_gaps'],requires_vlan=t['requires_vlan']))
            if any(t['requires_vlan'] for t in d['topologies']) and 'kathara/base:latest' in available:
                try:
                    client.containers.run('kathara/base:latest',command=['sh','-c','ip link add preflighta type veth peer name preflightb && ip link add link preflighta name preflighta.100 type vlan id 100'],network_mode='none',cap_add=['NET_ADMIN'],remove=True)
                    result['vlan_capability']=dict(available=True)
                except Exception as exc:result['vlan_capability']=dict(available=False,error=str(exc))
    except Exception as e:result['docker_error']=f'{type(e).__name__}: {e}'
    return result

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--output',type=Path,default=ROOT/'docs/validation/soft3888/environment-preflight.json');args=ap.parse_args()
    r=check();args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(r,indent=2)+'\n')
    print('Missing model credentials:',r['missing_credentials'])
    print('Topologies inspected:',len(r['topologies']),'Docker error:',r['docker_error'])
    for t in r['topologies']:
        if t['missing_images']:print(t['topology'],'requires images:',', '.join(t['missing_images']))
