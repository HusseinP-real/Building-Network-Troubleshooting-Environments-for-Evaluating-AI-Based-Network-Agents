(() => {
  const byId = id => document.getElementById(id);
  const svg = byId('networkMap');
  const ns = 'http://www.w3.org/2000/svg';
  let loadSequence = 0;
  let inventory, selected = '', view = [0, 0, 1600, 1000];
  const positions = new Map(), groups = new Map(), edges = [];
  function route() {
    const topology = location.hash === '#topology';
    byId('dashboardPage').hidden = topology;
    byId('topologyPage').hidden = !topology;
    for (const [id, active] of [['navDashboard', !topology], ['navTopology', topology]]) {
      byId(id).classList.toggle('active', active);
      if (active) byId(id).setAttribute('aria-current', 'page');
      else byId(id).removeAttribute('aria-current');
    }
  }
  window.addEventListener('hashchange', route); route();
  function mark(tag, attrs, text) {
    const el = document.createElementNS(ns, tag);
    Object.entries(attrs).forEach(([key, value]) => el.setAttribute(key, value));
    if (text !== undefined) el.textContent = text;
    return el;
  }
  function applyView() { svg.setAttribute('viewBox', view.join(' ')); }
  function zoom(factor) {
    const w = Math.min(2400, Math.max(400, view[2] * factor));
    const ratio = w / view[2];
    view = [view[0] + (view[2] - w) / 2, view[1] + view[3] * (1 - ratio) / 2, w, view[3] * ratio];
    applyView();
  }
  byId('zoomIn').onclick = () => zoom(.8);
  byId('zoomOut').onclick = () => zoom(1.25);
  byId('fitMap').onclick = () => {view = [0, 0, 1600, 1000]; applyView();};
  svg.addEventListener('wheel', event => {event.preventDefault(); zoom(event.deltaY > 0 ? 1.1 : .9);}, {passive:false});
  let drag;
  svg.addEventListener('pointerdown', event => {
    if (event.target.closest('.network-node')) return;
    const matrix = svg.getScreenCTM();
    if (!matrix) return;
    drag = {x:event.clientX, y:event.clientY, view:[...view], scale:matrix.a};
    svg.setPointerCapture(event.pointerId);
  });
  svg.addEventListener('pointermove', event => {
    if (!drag) return;
    view[0] = drag.view[0] - (event.clientX - drag.x) / drag.scale;
    view[1] = drag.view[1] - (event.clientY - drag.y) / drag.scale;
    applyView();
  });
  for (const type of ['pointerup', 'pointercancel', 'lostpointercapture']) svg.addEventListener(type, () => {drag = null;});
  function highlight() {
    const term = byId('nodeSearch').value.trim().toLowerCase();
    const neighbors = new Set(selected ? [selected, ...inventory.nodes[selected].ports.map(p => p.peer)] : []);
    groups.forEach((el, name) => {
      el.classList.toggle('dimmed', term ? !name.includes(term) : selected && !neighbors.has(name));
      el.classList.toggle('selected', name === selected);
      el.classList.toggle('search-match', !!term && name.includes(term));
    });
    edges.forEach(({el, a, b}) => {
      const match = selected && (a === selected || b === selected);
      el.classList.toggle('connected', !!match);
      el.classList.toggle('dimmed', term ? !(a.includes(term) || b.includes(term)) : !!selected && !match);
    });
  }
  function inspect(name) {
    selected = name;
    const node = inventory.nodes[name];
    byId('deviceName').textContent = name;
    byId('deviceSummary').textContent = `${node.role[0].toUpperCase() + node.role.slice(1)} · ${node.ports.length} connected interfaces`;
    const target = byId('deviceDetails'); target.replaceChildren();
    for (const [label, value] of [['Address', node.address], ['Gateway', node.gateway], ['VLAN', node.vlan], ['Address mode', node.role === 'host' ? (node.dhcp ? 'DHCP' : 'Static') : null]]) {
      if (value === undefined || value === null) continue;
      const row = document.createElement('div'); row.className = 'device-property';
      const key = document.createElement('span'), val = document.createElement('strong');
      key.textContent = label; val.textContent = value; row.append(key, val); target.append(row);
    }
    const title = document.createElement('h3'); title.textContent = 'Interfaces & neighbors'; target.append(title);
    node.ports.forEach(port => {
      const button = document.createElement('button'); button.className = 'port-row';
      const label = document.createElement('strong'), detail = document.createElement('small');
      label.textContent = `${port.interface} → ${port.peer}`;
      detail.textContent = [port.kind, port.address || port.subnet, port.vlans ? `VLAN ${port.vlans.join(', ')}` : ''].filter(Boolean).join(' · ');
      button.append(label, detail); button.onclick = () => inspect(port.peer); target.append(button);
    });
    highlight();
  }
  byId('nodeSearch').addEventListener('input', () => { if (inventory) highlight(); });
  byId('nodeSearch').addEventListener('keydown', event => {
    if (event.key !== 'Enter' || !inventory) return;
    const term = event.target.value.trim().toLowerCase();
    const name = Object.keys(inventory.nodes).find(n => n === term) || Object.keys(inventory.nodes).find(n => n.includes(term));
    if (name) {inspect(name); const p = positions.get(name); view = [p.x - 400, p.y - 250, 800, 500]; applyView();}
  });
  function draw(data) {
    inventory = data;
    selected = '';
    drag = null;
    positions.clear(); groups.clear(); edges.length = 0;
    svg.replaceChildren();
    view = [0, 0, 1600, 1000]; applyView();
    byId('nodeSearch').value = '';
    byId('deviceName').textContent = 'Select a device';
    byId('deviceSummary').textContent = 'Choose any node to highlight its neighbors and inspect its interfaces.';
    byId('deviceDetails').replaceChildren();
    svg.setAttribute('aria-label', `${data.name} network topology`);
    byId('topologySelectionNote').textContent = data.evaluation_enabled
      ? 'Current evaluation environment'
      : 'Standalone copy · exploration only · runtime validation pending';
    const counts = {router:0, switch:0, host:0};
    Object.values(data.nodes).forEach(node => {counts[node.role] += 1;});
    const metrics = byId('topologyMetrics'); metrics.replaceChildren();
    for (const [value, label] of [[Object.keys(data.nodes).length,'devices'], [data.links.length,'links'], [counts.router,'routers'], [counts.switch,'switches'], [counts.host,'hosts'], [data.scenario_count,'scenarios']]) {
      const span = document.createElement('span'), strong = document.createElement('strong');
      strong.textContent = value; span.append(strong, ` ${label}`); metrics.append(span);
    }
    const zones = [
      {name:'Shared services', x:210, routers:['r3','r4'], switches:['s13','s14','s15'], extra:[], vlans:[410,420,430]},
      {name:'Staff & guest', x:600, routers:['r5','r6'], switches:['s1','s2','s3','s4'], extra:['s16','s17','s18','s19'], vlans:[110,120]},
      {name:'Office & engineering', x:990, routers:['r7','r8'], switches:['s5','s6','s7','s8'], extra:['s20','s21','s22'], vlans:[210,220]},
      {name:'Application & database', x:1380, routers:['r9','r10'], switches:['s9','s10','s11','s12'], extra:['s23','s24','s25'], vlans:[310,320]},
    ];
    positions.set('r1', {x:680,y:75}); positions.set('r2', {x:920,y:75});
    zones.forEach(zone => {
      svg.append(mark('rect', {x:zone.x-185,y:155,width:370,height:815,rx:24,class:'network-zone'}));
      svg.append(mark('text', {x:zone.x,y:190,'text-anchor':'middle',class:'zone-label'}, zone.name));
      for (const [names,y] of [[zone.routers,255],[zone.switches,400],[zone.extra,535]]) {
        names.forEach((name,i) => positions.set(name,{x:zone.x+(i-(names.length-1)/2)*85,y}));
      }
      const hosts = Object.entries(data.nodes).filter(([,node]) => node.role==='host' && zone.vlans.includes(node.vlan));
      hosts.forEach(([name],i) => positions.set(name,{x:zone.x-120+(i%3)*120,y:680+Math.floor(i/3)*58}));
    });
    const edgeLayer = mark('g', {}); svg.append(edgeLayer);
    data.links.forEach(link => {
      const [a,b] = link.endpoints, start = positions.get(a.node), end = positions.get(b.node);
      if (!start || !end) return;
      const el = mark('path', {d:`M ${start.x} ${start.y} L ${end.x} ${end.y}`,class:`network-edge ${link.kind}`});
      el.append(mark('title',{},`${a.node}/${a.interface} ↔ ${b.node}/${b.interface} · ${link.kind}`));
      edgeLayer.append(el); edges.push({el,a:a.node,b:b.node});
    });
    Object.entries(data.nodes).forEach(([name,node]) => {
      const p = positions.get(name); if (!p) return;
      const g = mark('g',{transform:`translate(${p.x} ${p.y})`,class:`network-node ${node.role}`,tabindex:0,role:'button','aria-label':`${name}, ${node.role}, inspect device`});
      g.append(mark('rect',{x:-37,y:-17,width:74,height:34,rx:node.role==='router'?17:node.role==='host'?10:4}));
      g.append(mark('text',{'text-anchor':'middle','dominant-baseline':'central'},name));
      g.onclick=()=>inspect(name); g.onkeydown=event=>{if(event.key==='Enter'||event.key===' '){event.preventDefault();inspect(name);}};
      svg.append(g); groups.set(name,g);
    });
    const health=data.health;
    const summary=health ? `${health.passing}/${health.total} checks passed · ${new Date(health.timestamp).toLocaleString()}` : 'No saved health check available';
    byId('topologyHealth').textContent=summary;
    if (data.evaluation_enabled) byId('workspaceHealth').textContent=health ? `Saved health · ${health.passing}/${health.total}` : 'Saved health · unavailable';
  }
  async function loadTopology(id) {
    const sequence = ++loadSequence;
    byId('topologyError').hidden = true;
    svg.setAttribute('aria-busy', 'true');
    try {
      const response = await fetch(`/api/topology?id=${encodeURIComponent(id)}`);
      if (!response.ok) throw Error('Topology could not be loaded');
      const data = await response.json();
      if (sequence !== loadSequence) return;
      draw(data);
    } catch (error) {
      if (sequence !== loadSequence) return;
      inventory = null; selected = ''; positions.clear(); groups.clear(); edges.length = 0;
      svg.replaceChildren();
      byId('deviceName').textContent = 'Select a device';
      byId('deviceDetails').replaceChildren();
      byId('deviceSummary').textContent = 'Device information is unavailable.';
      byId('topologyMetrics').replaceChildren();
      byId('topologyError').hidden = false;
      byId('topologyError').textContent = error.message;
      byId('topologyHealth').textContent = 'Health unavailable';
    } finally {
      if (sequence === loadSequence) svg.setAttribute('aria-busy', 'false');
    }
  }
  byId('topologySelect').addEventListener('change', event => loadTopology(event.target.value));
  async function initialize() {
    try {
      const response = await fetch('/api/topologies');
      if (!response.ok) throw Error('Topology selection could not be loaded');
      const topologies = await response.json();
      const select = byId('topologySelect'); select.replaceChildren();
      topologies.forEach(topology => {
        const option = document.createElement('option');
        option.value = topology.id; option.textContent = topology.name;
        select.append(option);
      });
      select.disabled = false;
      await loadTopology(select.value);
    } catch (error) {
      byId('topologyError').hidden = false;
      byId('topologyError').textContent = error.message;
    }
  }
  initialize();
})();
