"""Exercise real diagnostic MCP servers without making model API requests."""
import asyncio
import json
import os
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from .runners.base import diagnostic_mcp_config
from .paths import KATH_BASE


async def smoke(lab_name, topology, probe, records):
    from .inventory import role_path
    from types import SimpleNamespace
    roles=json.loads(role_path(SimpleNamespace(lab=SimpleNamespace(name=topology)),topology).read_text())
    expected=set(roles.get('hosts',[]))
    for values in roles.get('servers',{}).values():expected.update(values)
    for name,cfg in diagnostic_mcp_config(lab_name).items():
        env=dict(cfg['env'], FAULTBENCH_INVENTORY_TOPOLOGY=topology)
        params=StdioServerParameters(command=cfg['command'],args=cfg['args'],env=env)
        async with stdio_client(params) as (read,write):
            async with ClientSession(read,write) as session:
                await session.initialize()
                listing=await session.list_tools()
                if not listing.tools:raise RuntimeError(f'{name}: empty tool list')
                record=dict(server=name,tools=[t.name for t in listing.tools],calls=[])
                records.append(record)
                async def call(tool,arguments):
                    result=await session.call_tool(tool,arguments)
                    text='\n'.join(c.text for c in result.content if hasattr(c,'text'))
                    record['calls'].append(dict(tool=tool,arguments=arguments,is_error=result.isError,output=text))
                    if result.isError:raise RuntimeError(text)
                    return text
                if name=='kathara_base_mcp_server':
                    output=await call('exec_shell',{'host_name':probe['host'],'command':f"ping -n -W1 -c1 {probe['destination']}"})
                    from .checks import _evaluate_expectation
                    if not _evaluate_expectation('0% loss',0,output)[0]:raise RuntimeError('MCP ping did not succeed')
                    output=await call('get_reachability',{})
                    payload=json.loads(output)
                    if set(payload['hosts'])!=expected:raise RuntimeError('MCP inventory omits or duplicates expected endpoints')
                    from collections import Counter
                    statuses=Counter(row.get('status') for row in payload.get('results',[]))
                    record['reachability_status_counts']=dict(statuses)
                    if not statuses or set(statuses)-{'ok','down','unstable'}:
                        raise RuntimeError('MCP reachability contains unparsed/unknown probes')
                    record['inventory_endpoints']=len(expected)
                elif name=='kathara_frr_mcp_server':
                    output=await call('frr_exec',{'router_name':probe['router'],'command':'show ip route '+probe['route']})
                    if probe['route'] not in output:raise RuntimeError('MCP route table missing healthy target prefix')
                # Telemetry tools are discoverable; this lab does not claim an
                # InfluxDB deployment, so do not call nonexistent DB services.
    return records


def run_smoke(lab_name,topology,probe,records):
    return asyncio.run(asyncio.wait_for(smoke(lab_name,topology,probe,records),timeout=120))
