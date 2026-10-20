#!/usr/bin/env python3
"""Generate a transparent ticket catalogue; maintain strict separation from agent input."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
FAULTS={
 'F01':{'type':'ebgp_uplink_loss','nodes':['a1','a3'],'expected':'Both ISP-A peering interfaces are down; the independent ISP-B service remains reachable', 'normal':'Enterprise can access both external service networks','symptom':'ISP-A hosted service unavailable', 'general':'Our external partner website stopped working, but another website still loads.', 'engineer':'Clients cannot reach 198.18.10.10; 198.18.20.10 remains reachable.', 'expert':'Both ISP-A eBGP adjacencies appear to be down; inspect a1 and a3 uplinks.', 'misleading':'The data center application server must be offline.'},
 'F02':{'type':'bgp_prefix_withdrawal','nodes':['a1','a3'],'expected':'ISP-A edge routers have withdrawn 198.18.10.0/24; BGP sessions remain established', 'normal':'Service prefix announced by ISP-A eBGP speakers','symptom':'Only ISP-A service prefix unreachable', 'general':'One partner site is unavailable from the office.', 'engineer':'External prefix 198.18.10.0/24 is absent despite live WAN links.', 'expert':'eBGP sessions are up but the 198.18.10.0/24 advertisement is missing at both ISP-A borders.', 'misleading':'Our DNS server is down; that must be why the partner site is unreachable.'},
 'F03':{'type':'branch_ospf_failure','nodes':['ba_r1','ba_r2'],'expected':'Both Branch-A FRR processes stopped; 10.20.10.0/24 no longer propagated into enterprise OSPF', 'normal':'Headquarters reaches branch A and data center','symptom':'Branch A becomes unreachable from HQ', 'general':'People in one branch report losing access to company systems.', 'engineer':'HQ cannot ping 10.20.10.21 but can reach 10.40.10.21.', 'expert':'Branch A routes disappeared after both local routing daemons stopped.', 'misleading':'The ISP-B carrier must have an outage.'}
}
for fid,v in FAULTS.items():
    dest=ROOT/'scenarios'/fid;dest.mkdir(parents=True,exist_ok=True)
    gt={'scenario_id':fid,'fault_exists':True,'fault_type':v['type'],'fault_devices':v['nodes'],'expected_root_cause':v['expected'],'normal_state':v['normal'],'observable_symptom':v['symptom'],'injection':'python3 lab.py inject '+fid,'repair':'python3 lab.py repair '+fid,'evaluation_fields':['fault_detection','fault_type','fault_devices','root_cause','repair_suggestion'],'status':'planned_until_live_verified'}
    (dest/'ground_truth.json').write_text(json.dumps(gt,indent=2)+'\n')
    tickets=[]
    for level in ('general','engineer','expert','misleading'):
        tickets.append({'ticket_id':f'{fid}_{level}','scenario_id':fid,'reporter_type':level,'text':v[level],'accuracy':'potentially_inaccurate' if level=='misleading' else 'scenario_consistent'})
    (dest/'tickets.json').write_text(json.dumps(tickets,indent=2)+'\n')
print('Wrote 3 ground truths and 12 tickets')
