#!/usr/bin/env python3
"""Draw every inventory node/link as SVG; optionally render PNG with Pillow."""
import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def draw():
    inv = json.loads((ROOT/'inventory.json').read_text())
    width, height = 3000, 1900
    positions = {}
    for i in range(1,4):
        positions[f'spine{i}'] = (750*i, 290)
    for rack in range(1,7):
        x = 250+500*(rack-1)
        positions[f'leaf{rack}'] = (x, 640)
        positions[f'rack{rack}'] = (x, 860)
        for host in range(1,11):
            positions[f'rack{rack}h{host}'] = (x + (-120 if host % 2 else 120), 1080+130*((host-1)//2))
    colors = dict(spine='#2563eb', leaf='#087e8b', switch='#b77916', server='#7c3aed', client='#475569')
    elements = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">', '<rect width="100%" height="100%" fill="#f8fafc"/>']
    labels = [(100,80,'DATA CENTRE / THREE-SPINE FABRIC',48,'#0f172a'),
              (100,135,'75 devices  ·  84 links  ·  6 racks  ·  eBGP + three-path ECMP',30,'#475569'),
              (100,185,'Each leaf connects to all three spines; each rack has one leaf, one switch and ten endpoints.',25,'#475569'),
              (100,1780,'Application: rack5h1 / 10.60.5.11:8080  →  Backend: rack6h1 / 10.60.6.11:8080',28,'#475569'),
              (100,1830,'All devices and physical links are read from inventory.json. No overlay, VRRP or inter-rack Layer 2.',24,'#64748b')]
    segments = []
    for link in inv['links']:
        a,b = (e['node'] for e in link['endpoints'])
        xa,ya=positions[a]; xb,yb=positions[b]
        color = '#a4b9d8' if link['kind']=='fabric' else '#94a3b8'
        elements.append(f'<line x1="{xa}" y1="{ya}" x2="{xb}" y2="{yb}" stroke="{color}" stroke-width="3"/>')
        segments.append((xa,ya,xb,yb,color))
    boxes=[]
    for name,node in inv['nodes'].items():
        x,y=positions[name]; w=180 if 'h' in name and node['role'] in ('client','server') else 230; h=74
        color=colors[node['role']]
        extra = f'AS {node["asn"]}' if 'asn' in node else f'10.60.{node["rack"]}.0/24' if node['role']=='switch' else node['address'].split('/')[0]
        elements.append(f'<rect x="{x-w/2}" y="{y-h/2}" width="{w}" height="{h}" rx="12" fill="{color}"/>')
        for ty,text,size in [(y-2,name,25),(y+24,extra,18)]:
            elements.append(f'<text x="{x}" y="{ty}" fill="white" font-family="Arial,sans-serif" font-size="{size}" text-anchor="middle">{html.escape(text)}</text>')
        boxes.append((x,y,w,h,color,name,extra))
    for x,y,text,size,color in labels:
        elements.append(f'<text x="{x}" y="{y}" fill="{color}" font-family="Arial,sans-serif" font-size="{size}">{html.escape(text)}</text>')
    elements.append('</svg>')
    (ROOT/'docs/topology.svg').write_text('\n'.join(elements)+'\n')
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        print('SVG generated. Install Pillow to also render PNG.')
        return
    canvas=Image.new('RGB',(width,height),'#f8fafc'); pen=ImageDraw.Draw(canvas)
    font_path='/System/Library/Fonts/Supplemental/Arial.ttf'
    def font(size):
        try: return ImageFont.truetype(font_path,size)
        except OSError: return ImageFont.truetype('DejaVuSans.ttf',size)
    for xa,ya,xb,yb,color in segments:
        pen.line((xa,ya,xb,yb), fill=color,width=3)
    for x,y,w,h,color,name,extra in boxes:
        pen.rounded_rectangle((x-w/2,y-h/2,x+w/2,y+h/2),radius=12,fill=color)
        pen.text((x,y-7),name,fill='white',font=font(25),anchor='mm')
        pen.text((x,y+22),extra,fill='white',font=font(18),anchor='mm')
    for x,y,text,size,color in labels:
        pen.text((x,y),text,fill=color,font=font(size),anchor='ls')
    canvas.save(ROOT/'docs/topology.png')
    print('Generated docs/topology.svg and docs/topology.png')


if __name__=='__main__':
    draw()
