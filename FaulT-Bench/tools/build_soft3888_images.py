#!/usr/bin/env python3
"""Build local lab images without weakening APT, TLS or signature verification.

The cloud proxy hostname may need an explicit build-network host entry. Its
public CA bundle is mounted temporarily, never copied into an image. Existing
images are retained by default; this script never prunes other Docker state.
"""
import argparse
import os
from pathlib import Path
import socket
import subprocess
import urllib.parse

ROOT = Path(__file__).resolve().parents[1]

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rebuild',action='store_true')
    args=parser.parse_args()
    env=os.environ.copy()
    cache=Path('/workspace/.cache') if Path('/workspace').is_dir() else Path(os.environ.get('XDG_CACHE_HOME',str(Path.home()/'.cache')))
    env.setdefault('DOCKER_CONFIG',str(cache/'docker'))
    Path(env['DOCKER_CONFIG']).mkdir(parents=True,exist_ok=True)
    context=ROOT/'tools/soft3888-images'
    for role,tag in [('host','soft3888/host:bookworm-v1'),('router','soft3888/frr:10.5.3-v1')]:
        present=subprocess.run(['docker','image','inspect',tag],capture_output=True).returncode==0
        if present and not args.rebuild:
            print(f'Using existing {tag}');continue
        cmd=['docker','build','--network','host' if role=='host' else 'none']
        if role=='host':
            proxy=os.environ.get('HTTP_PROXY') or os.environ.get('http_proxy')
            if proxy:
                host=urllib.parse.urlparse(proxy).hostname
                cmd+=['--add-host',f'{host}:{socket.gethostbyname(host)}']
            for variable in ('HTTP_PROXY','HTTPS_PROXY','NO_PROXY','http_proxy','https_proxy','no_proxy'):
                if variable in os.environ:cmd+=['--build-arg',variable]
            cert=os.environ.get('SSL_CERT_FILE')
            if cert and Path(cert).is_file():cmd+=['--secret',f'id=cloud-ca,src={cert}']
        cmd+=['-t',tag,'-f',str(context/f'Dockerfile.{role}'),str(context)]
        subprocess.run(cmd,env=env,check=True)

if __name__=='__main__':main()
