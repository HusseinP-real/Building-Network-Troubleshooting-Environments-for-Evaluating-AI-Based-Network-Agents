#!/usr/bin/env python3
"""Build only image variants with existing authoritative recipes; never guess kathara/dhcp."""
import json,os,socket,subprocess,urllib.parse
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def main():
    import docker
    client=docker.from_env();records=[];env=os.environ.copy()
    cache=Path('/workspace/.cache') if Path('/workspace').is_dir() else Path(os.environ.get('XDG_CACHE_HOME',str(Path.home()/'.cache')))
    env.setdefault('DOCKER_CONFIG',str(cache/'docker'));Path(env['DOCKER_CONFIG']).mkdir(parents=True,exist_ok=True)
    for target,base,packages,reference in [('kathara/base-stress:latest','kathara/base:latest','stress-ng isc-dhcp-server isc-dhcp-relay','SADE-NetworkAgent/src/nika/net_env/utils/DockerFiles/Dockerfile.base'),('kathara/frr-stress:latest','kathara/frr:latest','stress-ng isc-dhcp-server isc-dhcp-relay','SADE-NetworkAgent/src/nika/net_env/utils/DockerFiles/Dockerfile.frr'),('frr-with-vrrp-relay:latest','kathara/frr:latest','keepalived isc-dhcp-relay ipvsadm','topology_kathara/Kath1/Dockerfile.relay')]:
        source=client.images.get(base);pin=source.attrs.get('RepoDigests',[None])[0]
        if not pin:raise RuntimeError(f'Pull {base} from its registry before building derivatives; source digest required')
        if subprocess.run(['docker','image','inspect',target],capture_output=True,env=env).returncode:
            cmd=['docker','build','--network','host','--build-arg','SOURCE_IMAGE='+pin,'--build-arg','PACKAGES='+packages]
            proxy=os.environ.get('HTTP_PROXY') or os.environ.get('http_proxy')
            if proxy:
                host=urllib.parse.urlparse(proxy).hostname;cmd+=['--add-host',host+':'+socket.gethostbyname(host)]
            for key in ['HTTP_PROXY','HTTPS_PROXY','NO_PROXY','http_proxy','https_proxy','no_proxy']:
                if key in os.environ:cmd+=['--build-arg',key]
            cert=os.environ.get('SSL_CERT_FILE')
            if cert and Path(cert).is_file():cmd+=['--secret','id=cloud-ca,src='+cert]
            cmd+=['-t',target,'-f',str(ROOT/'tools/soft3888-images/Dockerfile.team'),str(ROOT/'tools/soft3888-images')]
            subprocess.run(cmd,env=env,check=True)
        records.append(dict(image=target,image_id=client.images.get(target).id,source_digest=pin,package_reference=reference))
        (ROOT/'docs/validation/soft3888/team-image-builds.json').write_text(json.dumps(records,indent=2)+'\n')
    client.close()
    print('Verified/rebuilt3 recipe-backed variants. kathara/dhcp still needs the team artifact/Dockerfile; it is not silently substituted.')

if __name__=='__main__':main()
