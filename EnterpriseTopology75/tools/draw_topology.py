#!/usr/bin/env python3
"""Render every inventory device and physical link; requires matplotlib."""
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

ROOT = Path(__file__).resolve().parents[1]
inv = json.loads((ROOT / 'inventory.json').read_text())
pos = {'r1':(10,20),'r2':(17,20),'r3':(22,20),'r4':(26,20)}
regions = [
    (0, 'HEADQUARTERS / AREA 10', ['r5','r6'], ['s1','s2'], ['s3','s4','s16','s17','s18','s19']),
    (10, 'BRANCH / AREA 20', ['r7','r8'], ['s5','s6'], ['s7','s8','s20','s21','s22']),
    (20, 'DATA CENTER / AREA 30', ['r9','r10'], ['s9','s10'], ['s11','s12','s23','s24','s25']),
]
fig, ax = plt.subplots(figsize=(27,21))
fig.patch.set_facecolor('#f8fafc'); ax.set_facecolor('#f8fafc')
for off, title, routers, distribution, access in regions:
    ax.add_patch(FancyBboxPatch((off+.1,.1),9.7,13.5,boxstyle='round,pad=0.02,rounding_size=0.2',fc='#eef2f7',ec='#cbd5e1',zorder=0))
    ax.text(off+.5,13,title,fontsize=16,weight='bold',color='#1e293b')
    for n,x in zip(routers,[off+2.5,off+7.5]): pos[n]=(x,11.7)
    for n,x in zip(distribution,[off+2.5,off+7.5]): pos[n]=(x,9.8)
    for i,n in enumerate(access):
        x=off+.9+i*8.2/(len(access)-1); pos[n]=(x,7.5)
        hosts=[p['peer'] for p in inv['nodes'][n]['ports'] if inv['nodes'][p['peer']]['role']=='host']
        for j,h in enumerate(hosts): pos[h]=(x,5.6-j*1.45)
for i,s in enumerate(['s13','s14','s15']):
    pos[s]=(21.5+i*3,17.4)
    for p in inv['nodes'][s]['ports']:
        if inv['nodes'][p['peer']]['role']=='host': pos[p['peer']]=(21.5+i*3,15.6)
assert set(pos)==set(inv['nodes'])
styles={'routed':('#64748b','-',1.4),'trunk':('#3b82f6','--',1.1),'access':('#94a3b8','-',1)}
for edge in inv['links']:
    a,b=[e['node'] for e in edge['endpoints']]
    color,style,width=styles[edge['kind']]
    if edge['kind']=='access':
        sw,host=(a,b) if inv['nodes'][a]['role']=='switch' else (b,a)
        x,y=pos[sw]; hx,hy=pos[host]
        siblings=[p['peer'] for p in inv['nodes'][sw]['ports'] if inv['nodes'][p['peer']]['role']=='host']
        rail=x+.71+.055*siblings.index(host)
        ax.plot([x,rail,rail,hx+.65],[y-.31,y-.65,hy,hy],color=color,lw=width,alpha=.7,zorder=1)
        continue
    rad=0
    if edge['kind']=='routed':
        rad=.10 if pos[a][1]==pos[b][1] else (-.07 if a=='r1' else .07)
    if edge['kind']=='trunk' and pos[a][1]==pos[b][1]: rad=.15
    ax.add_patch(FancyArrowPatch(pos[a],pos[b],arrowstyle='-',connectionstyle=f'arc3,rad={rad}',color=color,linestyle=style,linewidth=width,alpha=.65,zorder=1))
colors={'router':'#0f766e','switch':'#2563eb','host':'#fff7ed'}
for n,node in inv['nodes'].items():
    x,y=pos[n]; role=node['role']; w=1.3 if role=='host' else 1.05
    h=.78 if role=='host' else .62
    ax.add_patch(FancyBboxPatch((x-w/2,y-h/2),w,h,boxstyle='round,pad=0.03,rounding_size=0.12',fc=colors[role],ec='#fb923c' if role=='host' else 'white',lw=1.3,zorder=3))
    label=n
    if role=='host': label+='\nVLAN '+str(node['vlan'])
    ax.text(x,y,label,ha='center',va='center',fontsize=8 if role=='host' else 11,color='#7c2d12' if role=='host' else 'white',weight='bold',zorder=4)
ax.text(.4,22.4,'ENTERPRISE NETWORK / 75 DEVICES',fontsize=30,weight='bold',color='#0f172a')
ax.text(.4,21.5,'10 routers  +  25 switches  +  40 endpoints  |  108 physical point-to-point links',fontsize=17,color='#475569')
ax.text(.4,19.7,'CORE / OSPF AREA 0',fontsize=16,weight='bold',color='#0f766e')
ax.text(21,18.65,'SHARED SERVICES / AREA 0',fontsize=13,weight='bold',color='#0f766e')
ax.text(.5,17.6,'TEAL: FRR routers     BLUE: VLAN-aware switches     ORANGE: endpoints',fontsize=13,color='#334155')
ax.text(.5,16.7,'Solid gray: routed links     Dashed blue: VLAN trunks     Thin gray: endpoint access',fontsize=12,color='#475569')
ax.text(.5,15.7,'Every device and link is read from inventory.json.\nPhysical links shown; STP selects active Layer 2 paths.',fontsize=12,color='#475569',linespacing=1.7)
ax.set_xlim(-.3,30.3); ax.set_ylim(-.5,23.2); ax.axis('off')
fig.tight_layout()
for ext in ['svg','png']:
    fig.savefig(ROOT/'docs'/f'topology-75.{ext}',dpi=160,bbox_inches='tight',facecolor=fig.get_facecolor())
print(f'Rendered {len(pos)} devices and {len(inv["links"])} links')
