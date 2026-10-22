const $ = (id) => document.getElementById(id);
const axes = [
  ['detection_correct', 'Detection', 'Detect'],
  ['device_correct', 'Device', 'Device'],
  ['localization_correct', 'Resource', 'Resource'],
  ['fault_type_correct', 'Fault type', 'Fault'],
  ['rca_exact', 'Exact RCA', 'Exact RCA'],
];
const qualityAxes = [['explanation_correct', 'Explanation', 'Explain'], ['repair_correct', 'Repair advice', 'Repair'], ['full_correct', 'Full correctness', 'Full']];
const caseNames = {
  'core-uplink': 'Core uplink',
  'gateway-service': 'Gateway service',
  'database-acl': 'Database ACL',
};
let selectedReport = '';
let lastRunning = false;
let lastFinished = '';

const iconPaths = {
  hub: '<circle cx="12" cy="12" r="3"/><circle cx="4" cy="5" r="1.5"/><circle cx="20" cy="5" r="1.5"/><circle cx="4" cy="19" r="1.5"/><circle cx="20" cy="19" r="1.5"/><path d="M6 6.5 10 10M18 6.5 14 10M6 17.5 10 14M18 17.5 14 14"/>',
  dark_mode: '<path d="M20.2 15.3A8.8 8.8 0 0 1 8.7 3.8a8.8 8.8 0 1 0 11.5 11.5Z"/>',
  light_mode: '<circle cx="12" cy="12" r="4"/><path d="M12 2v2m0 16v2M4.9 4.9l1.4 1.4m11.4 11.4 1.4 1.4M2 12h2m16 0h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>',
  monitoring: '<path d="M3 17h4l3-7 4 5 3-9 2 5h2"/><path d="M3 21h18"/>',
  analytics: '<path d="M4 19V9m6 10V5m6 14v-7m4 7V3"/><path d="M2 21h20"/>',
  lan: '<rect x="9" y="3" width="6" height="5" rx="1"/><rect x="2" y="16" width="6" height="5" rx="1"/><rect x="16" y="16" width="6" height="5" rx="1"/><path d="M12 8v4M5 16v-4h14v4"/>',
  pentagon: '<path d="m12 2 9 6.5-3.5 11H6.5L3 8.5 12 2Z"/>',
  bolt: '<path d="m13 2-9 11h7l-1 9 10-12h-7V2Z"/>',
  rocket_launch: '<path d="M8 16c2-6 6-10 13-13 0 7-4 11-10 13l-3-3Z"/><path d="M8 13H4l-2 5 6-2m3 0 2 6 5-2v-4M3 21l3-3"/><circle cx="16" cy="8" r="1"/>',
  play_arrow: '<path d="m7 4 13 8-13 8V4Z"/>',
  info: '<circle cx="12" cy="12" r="10"/><path d="M12 11v6m0-10h.01"/>',
  target: '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1"/>',
  verified: '<path d="m12 2 2.5 2 3.2-.2.5 3.2 2.6 2-.9 3 1 3-2.7 1.8-.5 3.2-3.2-.2L12 22l-2.5-2.2-3.2.2-.5-3.2L3 15l1-3-.9-3 2.6-2 .5-3.2 3.2.2L12 2Z"/><path d="m8 12 2.5 2.5L16 9"/>',
  schedule: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
  terminal: '<rect x="2" y="4" width="20" height="16" rx="2"/><path d="m6 9 3 3-3 3m6 0h5"/>',
  refresh: '<path d="M20 7v5h-5M4 17v-5h5"/><path d="M5.5 10A7 7 0 0 1 18 7l2 5M4 12l2 5a7 7 0 0 0 12.5-3"/>',
  expand_more: '<path d="m5 9 7 7 7-7"/>',
};
function renderIcon(host, name) {
  const mark = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  mark.setAttribute('viewBox', '0 0 24 24');
  mark.setAttribute('fill', 'none');
  mark.setAttribute('stroke', 'currentColor');
  mark.setAttribute('stroke-width', '1.8');
  mark.setAttribute('stroke-linecap', 'round');
  mark.setAttribute('stroke-linejoin', 'round');
  mark.setAttribute('aria-hidden', 'true');
  mark.innerHTML = iconPaths[name] || '';
  host.replaceChildren(mark);
}
document.querySelectorAll('.material-symbols-outlined').forEach(host => renderIcon(host, host.textContent.trim()));

function setTheme(theme) {
  document.documentElement.dataset.theme = theme;
  renderIcon($('themeIcon'), theme === 'dark' ? 'light_mode' : 'dark_mode');
  $('themeButton').setAttribute('aria-label', `Switch to ${theme === 'dark' ? 'light' : 'dark'} theme`);
  document.querySelector('meta[name="theme-color"]').content = theme === 'dark' ? '#141218' : '#fef7ff';
  localStorage.setItem('sade-theme', theme);
}
setTheme(localStorage.getItem('sade-theme') === 'dark' ? 'dark' : 'light');
$('themeButton').addEventListener('click', () => setTheme(document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark'));

document.querySelectorAll('.m3-interactive').forEach(control => {
  control.addEventListener('click', event => {
    if (control.disabled || window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
    const rect = control.getBoundingClientRect();
    const ripple = element('span', 'ripple');
    ripple.style.setProperty('--ripple-x', `${event.detail ? event.clientX - rect.left : rect.width / 2}px`);
    ripple.style.setProperty('--ripple-y', `${event.detail ? event.clientY - rect.top : rect.height / 2}px`);
    ripple.style.setProperty('--ripple-scale', Math.ceil(Math.max(rect.width, rect.height) / 12));
    control.append(ripple);
    ripple.addEventListener('animationend', () => ripple.remove(), {once: true});
  });
});

function fmtNumber(value, digits = 0) {
  return Number.isFinite(Number(value)) ? Number(value).toFixed(digits) : '—';
}
function pct(value) {
  return value === null || value === undefined ? '—' : `${Math.round(Number(value) * 100)}%`;
}
function element(tag, cls, content) {
  const el = document.createElement(tag);
  if (cls) el.className = cls;
  if (content !== undefined) el.textContent = content;
  return el;
}
function svg(tag, attrs = {}) {
  const el = document.createElementNS('http://www.w3.org/2000/svg', tag);
  Object.entries(attrs).forEach(([name, value]) => el.setAttribute(name, value));
  return el;
}
function rate(report, key) {
  return report.metrics?.[key]?.rate ?? null;
}
function radar(report) {
  const box = $('radarChart');
  box.replaceChildren();
  const graph = svg('svg', {viewBox: '0 0 440 300', role: 'img', 'aria-label': 'Five-axis accuracy radar chart'});
  const cx = 220, cy = 149, radius = 92;
  const point = (i, r) => {
    const angle = -Math.PI / 2 + i * 2 * Math.PI / 5;
    return [cx + Math.cos(angle) * r, cy + Math.sin(angle) * r];
  };
  const polygon = (radii) => radii.map((r, i) => point(i, r).map(v => v.toFixed(1)).join(',')).join(' ');
  [0.25, 0.5, 0.75, 1].forEach(level => graph.append(svg('polygon', {
    points: polygon(Array(5).fill(radius * level)), fill: 'none', stroke: 'var(--outline-variant)', 'stroke-width': '1',
  })));
  axes.forEach(([, label], i) => {
    const [x, y] = point(i, radius);
    graph.append(svg('line', {x1: cx, y1: cy, x2: x, y2: y, stroke: 'var(--outline-variant)', 'stroke-width': '1'}));
    const [lx, ly] = point(i, radius + 32);
    const text = svg('text', {x: lx, y: ly, 'text-anchor': lx < cx - 10 ? 'end' : lx > cx + 10 ? 'start' : 'middle', class: 'radar-label'});
    text.textContent = label.toUpperCase();
    graph.append(text);
  });
  const values = axes.map(([key]) => Math.max(0, Math.min(1, rate(report, key) ?? 0)));
  graph.append(svg('polygon', {points: polygon(values.map(v => Math.max(v, .012) * radius)), fill: 'var(--primary-container)', 'fill-opacity': '.62', stroke: 'var(--primary)', 'stroke-width': '2.5'}));
  values.forEach((v, i) => {
    const [x, y] = point(i, Math.max(v, .012) * radius);
    graph.append(svg('circle', {cx: x, cy: y, r: 4, fill: 'var(--primary)', stroke: 'var(--surface-container-low)', 'stroke-width': 2}));
  });
  const center = svg('text', {x: cx, y: cy + 6, 'text-anchor': 'middle', class: 'radar-rate'});
  center.textContent = pct(rate(report, 'rca_exact'));
  graph.append(center);
  box.append(graph);
}
function insightCharts(report) {
  const runs = report.runs || [];
  const outcome = run => run.score?.full_correct === true ? 0 : run.score?.rca_exact === true ? 1 : typeof run.score?.rca_exact === 'boolean' ? 2 : 3;
  const labels = ['Full correctness', 'Exact RCA, not full', 'RCA mismatch', 'Unscored'];
  const colors = ['var(--primary)', 'var(--tertiary)', 'var(--error)', 'var(--outline)'];
  const counts = labels.map((_, i) => runs.filter(run => outcome(run) === i).length);
  const donut = svg('svg', {viewBox:'0 0 240 240', role:'img', 'aria-label':`Run outcomes: ${labels.map((label,i)=>`${label}: ${counts[i]}`).join(', ')}`});
  donut.append(svg('circle',{cx:120,cy:120,r:85,fill:'none',stroke:'var(--surface-container-highest)','stroke-width':24}));
  let offset = 0;
  counts.forEach((count,i) => {
    if (!count || !runs.length) return;
    const fraction = count / runs.length;
    const arc = svg('circle',{cx:120,cy:120,r:85,fill:'none',stroke:colors[i],'stroke-width':24,pathLength:100,'stroke-dasharray':`${fraction*100} ${100-fraction*100}`,'stroke-dashoffset':-offset,transform:'rotate(-90 120 120)',class:'outcome-arc'});
    const title=svg('title');title.textContent=`${labels[i]}: ${count}/${runs.length} (${Math.round(fraction*100)}%)`;arc.append(title);donut.append(arc);offset+=fraction*100;
  });
  const total=svg('text',{x:120,y:117,'text-anchor':'middle',class:'donut-total'});total.textContent=runs.length;donut.append(total);
  const subtitle=svg('text',{x:120,y:141,'text-anchor':'middle',class:'plot-label'});subtitle.textContent='ATTEMPTS';donut.append(subtitle);
  $('outcomeDonut').replaceChildren(donut);$('outcomeLegend').replaceChildren();
  labels.forEach((label,i)=>{
    const row=element('div','outcome-row'); const dot=element('span','outcome-dot');dot.style.background=colors[i];
    row.append(dot,element('span','',label),element('strong','',`${counts[i]} · ${runs.length?Math.round(counts[i]/runs.length*100):0}%`));$('outcomeLegend').append(row);
  });
  $('qualityBridge').replaceChildren();
  [['rca_exact','Exact RCA'],['explanation_correct','Explanation'],['repair_correct','Repair advice']].forEach(([key,label])=>{
    const metric=report.metrics?.[key];const cell=element('div','bridge-cell');
    cell.append(element('strong','',metric?.scored_denominator===0?'—':pct(metric?.rate)),element('span','',label));
    cell.title=`${metric?.correct??0}/${metric?.denominator??report.attempted??0} attempts; ${metric?.unscored??0} unscored`;$('qualityBridge').append(cell);
  });
  const valid=runs.filter(r=>Number.isFinite(r.wall_seconds)&&Number.isFinite(r.tool_calls));
  const chart=svg('svg',{viewBox:'0 0 520 290',role:'group','aria-label':'Scatter plot: wall time in seconds against tool calls. Focus points for details.'});
  const maxX=Math.ceil(Math.max(1,...valid.map(r=>r.wall_seconds))/50)*50;
  const maxY=Math.ceil(Math.max(1,...valid.map(r=>r.tool_calls))/20)*20;
  for(let i=0;i<=4;i++){
    const y=235-i*49;
    chart.append(svg('line',{x1:48,x2:494,y1:y,y2:y,stroke:'var(--outline-variant)','stroke-dasharray':'3 5'}));
    const label=svg('text',{x:37,y:y+4,'text-anchor':'end',class:'plot-label'});label.textContent=Math.round(maxY*i/4);chart.append(label);
    const x=48+i*111.5;
    const xt=svg('text',{x,y:255,'text-anchor':'middle',class:'plot-label'});xt.textContent=Math.round(maxX*i/4);chart.append(xt);
  }
  const xtitle=svg('text',{x:275,y:282,'text-anchor':'middle',class:'plot-label'});xtitle.textContent='Wall time per attempt (seconds)';chart.append(xtitle);
  const ytitle=svg('text',{x:48,y:20,class:'plot-label'});ytitle.textContent='Tool calls';chart.append(ytitle);
  valid.forEach((run,i)=>{
    const detail=`${run.case} · ${run.wall_seconds.toFixed(1)}s · ${run.tool_calls} calls · ${labels[outcome(run)]}`;
    const point=svg('circle',{cx:48+run.wall_seconds/maxX*446,cy:235-run.tool_calls/maxY*196,r:6.5,fill:colors[outcome(run)],stroke:'var(--surface-container-low)','stroke-width':2,tabindex:0,role:'img','aria-label':detail,class:'scatter-point'});
    const title=svg('title');title.textContent=detail;point.append(title);
    for(const event of ['mouseenter','focus'])point.addEventListener(event,()=>{$('scatterDetail').textContent=detail;});chart.append(point);
  });
  $('effortScatter').replaceChildren(chart);
  $('scatterDetail').textContent=valid.length?`${valid.length}/${runs.length} attempts plotted. Missing tool usage is excluded. Colors match the outcome chart above.`:'No attempts have both recorded time and tool usage.';
}
function tokenUsage(report) {
  const fields = [['input_tokens','Uncached input'],['cache_creation_input_tokens','Cache creation'],['cache_read_input_tokens','Cache reads'],['output_tokens','Output']];
  const valid = value => typeof value === 'number' && Number.isFinite(value) && value >= 0;
  const hasUsage = usage => usage && fields.some(([key]) => valid(usage[key]));
  const sumUsage = usage => hasUsage(usage) ? fields.reduce((n,[key])=>n+(valid(usage[key])?usage[key]:0),0) : null;
  const exact = value => value===null ? '—' : value.toLocaleString('en-US');
  const compact = value => value>=1e6 ? `${(value/1e6).toFixed(2)}M` : value>=1e3 ? `${(value/1e3).toFixed(1)}K` : String(value);
  const money = value => valid(value) ? `$${value.toFixed(4)}` : '—';
  const rows = (report.runs||[]).map(run=>({run,d:run.usage,j:run.quality?.usage,dt:sumUsage(run.usage),jt:sumUsage(run.quality?.usage),dc:run.total_cost_usd,jc:run.judge_cost_usd??run.quality?.total_cost_usd}));
  const dcount=rows.filter(r=>r.dt!==null).length,jcount=rows.filter(r=>r.jt!==null).length;
  const dtotal=rows.reduce((n,r)=>n+(r.dt??0),0),jtotal=rows.reduce((n,r)=>n+(r.jt??0),0);
  const costs=rows.flatMap(r=>[r.dc,r.jc]).filter(valid);
  $('tokenTotal').textContent=dcount+jcount?compact(dtotal+jtotal):'—';
  $('tokenTotal').title=exact(dcount+jcount?dtotal+jtotal:null);
  $('diagnosisTokens').textContent=dcount?compact(dtotal):'—';$('diagnosisTokens').title=exact(dcount?dtotal:null);
  $('judgeTokens').textContent=jcount?compact(jtotal):'—';$('judgeTokens').title=exact(jcount?jtotal:null);
  $('diagnosisCoverage').textContent=`${dcount}/${rows.length} attempts with usage`;
  $('judgeCoverage').textContent=`${jcount}/${rows.length} attempts with usage`;
  $('tokenCoverage').textContent=`${dcount+jcount} recorded stage totals · includes cache`;
  $('recordedCost').textContent=costs.length?`$${costs.reduce((a,b)=>a+b,0).toFixed(2)}`:'—';
  const dcost=rows.filter(r=>valid(r.dc)),jcost=rows.filter(r=>valid(r.jc));
  $('costCoverage').textContent=`Diagnosis ${money(dcost.length?dcost.reduce((n,r)=>n+r.dc,0):null)} · Judge ${money(jcost.length?jcost.reduce((n,r)=>n+r.jc,0):null)}`;
  $('tokenLimit').textContent=`Missing usage is unknown, not zero: ${rows.length-dcount} diagnosis and ${rows.length-jcount} judge stage totals unavailable. Cost recorded for ${dcost.length} diagnosis and ${jcost.length} judge stages. SDK cost is not a billing statement.`;
  const totals=fields.map(([key])=>rows.reduce((n,r)=>n+(valid(r.d?.[key])?r.d[key]:0)+(valid(r.j?.[key])?r.j[key]:0),0));
  const composition=$('tokenComposition');composition.replaceChildren();
  if(!dcount&&!jcount)composition.append(element('p','bar-empty','No token usage was saved for this report.'));
  else fields.forEach(([,label],i)=>{
    const row=element('div','bar-row token-composition-row');const track=element('div','bar-track');const fill=element('div','bar-fill');
    fill.style.width=`${dtotal+jtotal?totals[i]/(dtotal+jtotal)*100:0}%`;fill.style.minWidth='0';fill.style.background=['var(--primary)','var(--tertiary)','var(--success)','var(--secondary)'][i];track.append(fill);
    row.append(element('span','bar-name',label),track,element('span','bar-value',compact(totals[i])));row.title=`${label}: ${exact(totals[i])} tokens`;composition.append(row);
  });
  const ranked=rows.filter(r=>r.dt!==null||r.jt!==null).sort((a,b)=>(b.dt??0)+(b.jt??0)-(a.dt??0)-(a.jt??0));
  const max=Math.max(1,...ranked.map(r=>(r.dt??0)+(r.jt??0)));$('tokenRuns').replaceChildren();
  if(!ranked.length)$('tokenRuns').append(element('p','bar-empty','No recorded usage available.'));
  ranked.slice(0,8).forEach(r=>{
    const row=element('div','bar-row token-run');row.tabIndex=0;
    row.title=`${r.run.case}: diagnosis ${exact(r.dt)}; judge ${exact(r.jt)} tokens`;
    row.setAttribute('aria-label',row.title);
    const track=element('div','token-stack');
    for(const [value,cls] of [[r.dt,'token-diagnosis'],[r.jt,'token-judge']]){const segment=element('span',cls);segment.style.width=`${(value??0)/max*100}%`;track.append(segment);}
    row.append(element('span','bar-name',r.run.case),track,element('span','bar-value',compact((r.dt??0)+(r.jt??0))));$('tokenRuns').append(row);
  });
  $('tokenTable').replaceChildren();rows.forEach(r=>{
    const tr=element('tr');[r.run.case,exact(r.dt),exact(r.jt),money(r.dc),money(r.jc)].forEach(v=>tr.append(element('td','',v)));$('tokenTable').append(tr);
  });
}
function matrix(report) {
  const box = $('matrixChart');
  box.replaceChildren();
  const grid = element('div', 'matrix-grid');
  grid.append(element('div', 'matrix-col', 'ATTEMPT'));
  const displayedAxes = [...axes, ...qualityAxes];
  grid.style.gridTemplateColumns = `150px repeat(${displayedAxes.length}, minmax(45px, 1fr))`;
  grid.style.minWidth = '650px';
  displayedAxes.forEach(([, , short]) => grid.append(element('div', 'matrix-col', short.toUpperCase())));
  const counts = {};
  (report.runs || []).forEach((run, runIndex) => {
    counts[run.case] = (counts[run.case] || 0) + 1;
    const name = caseNames[run.case] || run.case || 'Unknown';
    grid.append(element('div', 'matrix-row', `${name} · ${String(counts[run.case]).padStart(2, '0')}`));
    displayedAxes.forEach(([key]) => {
      const value = run.score?.[key];
      const status = value === true ? 'good' : value === false ? 'bad' : 'none';
      const tile = element('div', `matrix-cell ${status}`, value === true ? '✓' : value === false ? '×' : '—');
      tile.style.setProperty('--i', runIndex);
      tile.title = `${name}: ${key} — ${status === 'good' ? 'correct' : status === 'bad' ? 'incorrect' : 'unscored'}`;
      grid.append(tile);
    });
  });
  box.append(grid);
}
function bars(report, target, field, unit) {
  const box = $(target);
  box.replaceChildren();
  const runs = report.runs || [];
  const values = runs.map(run => typeof run[field] === 'number' ? run[field] : NaN);
  const valid = values.filter(Number.isFinite);
  const max = Math.max(...valid, 1);
  if (!runs.length) { box.append(element('p', 'bar-empty', 'No run data available.')); return; }
  const counts = {};
  runs.forEach((run, index) => {
    counts[run.case] = (counts[run.case] || 0) + 1;
    const row = element('div', 'bar-row');
    row.append(element('span', 'bar-name', `${caseNames[run.case] || run.case} ${counts[run.case] > 1 ? counts[run.case] : ''}`));
    const track = element('div', 'bar-track');
    const fill = element('div', 'bar-fill');
    fill.style.width = Number.isFinite(values[index]) ? `${Math.max(2, values[index] / max * 100)}%` : '0';
    track.append(fill);
    row.append(track);
    row.append(element('span', 'bar-value', Number.isFinite(values[index]) ? `${fmtNumber(values[index], field === 'wall_seconds' ? 1 : 0)}${unit}` : '—'));
    box.append(row);
  });
}
function pill(value) {
  return element('span', `pill ${value === true ? 'yes' : value === false ? 'no' : 'unknown'}`, value === true ? 'PASS' : value === false ? 'FAIL' : '—');
}
function render(report) {
  $('emptyState').hidden = true;
  $('dashboard').hidden = false;
  const runs = report.runs || [];
  const headline = report.metrics?.full_correct ? 'full_correct' : 'rca_exact';
  $('exactLabel').textContent = headline === 'full_correct' ? 'Full correctness' : 'Exact RCA fields · legacy';
  $('exactValue').textContent = report.metrics?.[headline]?.scored_denominator === 0 ? '—' : pct(rate(report, headline));
  $('exactCount').textContent = `${report.metrics?.[headline]?.correct ?? 0} / ${report.attempted ?? 0} attempts · ${report.metrics?.[headline]?.unscored ?? 0} unscored`;
  $('completeValue').textContent = `${report.complete_runs ?? 0}/${report.attempted ?? 0}`;
  const seconds = runs.map(r => r.wall_seconds).filter(v => typeof v === 'number');
  $('timeValue').textContent = seconds.length ? `${fmtNumber(seconds.reduce((a, b) => a + b, 0) / seconds.length)}s` : '—';
  const calls = runs.map(r => r.tool_calls).filter(v => typeof v === 'number');
  $('callsValue').textContent = calls.length ? String(calls.reduce((a, b) => a + b, 0)) : '—';
  $('reportMeta').textContent = `${report.attempted ?? 0} ATTEMPTS · ${report.scored ?? 0} SCORED`;
  $('robustnessStats').hidden = !report.by_category;
  $('categoryPanel').hidden = !report.by_category;
  $('falsePositiveValue').textContent = pct(report.healthy_false_positive?.rate);
  $('falsePositiveNote').textContent = `Lower is better · ${report.healthy_false_positive?.denominator ?? 0} scored · ${report.healthy_false_positive?.unscored ?? 0} unscored`;
  $('healthyValue').textContent = pct(report.healthy_correct_rejection?.rate);
  $('misleadingValue').textContent = pct(report.by_category?.misleading?.rate);
  const ci = report.metrics?.rca_exact?.ci95;
  $('intervalValue').textContent = ci ? `${pct(ci[0])}–${pct(ci[1])}` : '—';
  $('categoryChart').replaceChildren();
  Object.entries(report.by_category || {}).forEach(([name, metric]) => {
    const row = element('div', 'bar-row');
    row.append(element('span', 'bar-name', name));
    const track = element('div', 'bar-track');
    const fill = element('div', 'bar-fill'); fill.style.width = `${(metric.rate || 0) * 100}%`;
    track.append(fill); row.append(track);
    row.append(element('span', 'bar-value', `${metric.correct}/${metric.denominator} · ${pct(metric.rate)}`));
    $('categoryChart').append(row);
  });
  $('reportMeta').textContent += report.schema_version >= 2
    ? ` · ${(report.modes || ['live']).join('/')} · SUITE ${Math.round((report.suite_coverage || 0) * 100)}%`
    : ' · LEGACY v1 REPORT';
  radar(report); matrix(report); insightCharts(report); tokenUsage(report);
  bars(report, 'durationChart', 'wall_seconds', 's');
  bars(report, 'toolChart', 'tool_calls', '');
  const table = $('runsTable'); table.replaceChildren();
  runs.forEach(run => {
    const tr = element('tr');
    tr.append(element('td', 'table-case', caseNames[run.case] || run.case));
    tr.append(element('td', '', run.model || '—'));
    [run.score?.rca_exact, run.score?.explanation_correct, run.score?.repair_correct, run.score?.full_correct, run.state_verified ?? run.injection_verified, run.repair_verified].forEach(v => {
      const td = element('td'); td.append(pill(v)); tr.append(td);
    });
    tr.append(element('td', '', typeof run.wall_seconds === 'number' ? `${fmtNumber(run.wall_seconds, 1)}s` : '—'));
    tr.append(element('td', '', run.tool_calls ?? '—'));
    table.append(tr);
  });
}
async function json(url, options) {
  const response = await fetch(url, options);
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || `Request failed (${response.status})`);
  return data;
}
async function loadReports(preferred) {
  const reports = await json('/api/reports');
  const select = $('reportSelect');
  select.replaceChildren();
  if (!reports.length) {
    select.append(element('option', '', 'No saved reports'));
    $('emptyState').hidden = false;
    $('dashboard').hidden = true;
    return;
  }
  reports.forEach(item => {
    const date = item.generated_at ? new Date(item.generated_at).toLocaleString() : item.id;
    const option = element('option', '', `${date} · v${item.scorer_version || '1.0'} · fields ${pct(item.exact_rate)} · full ${pct(item.full_rate)} · ${item.model || 'Unknown'}`);
    option.value = item.id; select.append(option);
  });
  selectedReport = reports.some(r => r.id === preferred) ? preferred : reports.some(r => r.id === selectedReport) ? selectedReport : reports[0].id;
  select.value = selectedReport;
  await loadReport(selectedReport);
}
async function loadReport(id) {
  selectedReport = id;
  render(await json(`/api/report?id=${encodeURIComponent(id)}`));
}
function progress(lines, repeats, running, successful, caseCount = 20) {
  const total = repeats * caseCount;
  const completed = lines.filter(line => /^  (scored|error);/.test(line)).length;
  const activeCase = [...lines].reverse().find(line => line.startsWith('Running '));
  $('progressFill').style.width = `${Math.min(100, completed / total * 100)}%`;
  $('progressFill').parentElement.setAttribute('aria-valuenow', String(Math.round(completed / total * 100)));
  $('progressCount').textContent = `${completed} / ${total}`;
  $('progressText').textContent = !running ? (successful ? 'All scenarios finished' : 'Execution stopped — inspect log') : activeCase || 'Waiting for the first scenario';
}
async function pollStatus() {
  try {
    const state = await json('/api/status');
    $('runButton').disabled = state.running;
    $('model').disabled = state.running;
    $('repeats').disabled = state.running;
    $('mode').disabled = state.running;
    $('promptStyle').disabled = state.running;
    $('toolProfile').disabled = state.running;
    $('runLabel').textContent = state.running ? 'Benchmark running…' : 'Run benchmark';
    if (state.started_at) {
      $('runPanel').hidden = false;
      $('runLog').textContent = state.lines.join('\n');
      progress(state.lines, state.repeats || 1, state.running, state.returncode === 0, state.case_count || 20);
      $('runTitle').textContent = state.running ? 'Diagnosing live faults…' : state.returncode === 0 ? 'Benchmark complete' : 'Benchmark finished with issues';
      $('runBadge').className = `badge ${state.running ? 'running' : state.returncode === 0 ? 'done' : 'failed'}`;
      $('runBadge').textContent = state.running ? 'Running' : state.returncode === 0 ? 'Complete' : 'Check log';
    }
    if (lastRunning && !state.running && state.finished_at !== lastFinished) {
      lastFinished = state.finished_at;
      await loadReports(state.report);
    }
    lastRunning = state.running;
  } catch (error) {
    $('runTitle').textContent = `Connection issue: ${error.message}`;
  }
}
$('runButton').addEventListener('click', async () => {
  try {
    $('runButton').disabled = true;
    await json('/api/run', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({model: $('model').value.trim(), repeats: Number($('repeats').value), mode: $('mode').value, prompt_style: $('promptStyle').value, tool_profile: $('toolProfile').value})});
    $('runPanel').hidden = false;
    $('runPanel').scrollIntoView({behavior: 'smooth', block: 'center'});
    await pollStatus();
  } catch (error) {
    $('runButton').disabled = false;
    $('runPanel').hidden = false;
    $('runTitle').textContent = error.message;
    $('runBadge').className = 'badge failed';
    $('runBadge').textContent = 'Error';
  }
});
$('reportSelect').addEventListener('change', event => loadReport(event.target.value).catch(console.error));
$('refreshButton').addEventListener('click', () => loadReports('').catch(console.error));
loadReports('').catch(error => { $('emptyState').hidden = false; $('emptyState').querySelector('p').textContent = error.message; });
pollStatus();
setInterval(pollStatus, 1500);

(() => {
  const toggle = document.getElementById('sidebarToggle');
  const sidebar = document.getElementById('workspaceSidebar');
  let saved;
  try { saved = localStorage.getItem('sade-sidebar'); } catch (_) { /* Optional preference. */ }
  let collapsed = saved ? saved === 'hidden' : matchMedia('(max-width:750px)').matches;
  function setSidebar(hidden, persist = true) {
    collapsed = hidden;
    document.body.classList.toggle('sidebar-hidden', hidden);
    sidebar.inert = hidden;
    toggle.setAttribute('aria-expanded', String(!hidden));
    toggle.setAttribute('aria-label', hidden ? 'Show sidebar' : 'Hide sidebar');
    if (persist) { try { localStorage.setItem('sade-sidebar', hidden ? 'hidden' : 'visible'); } catch (_) {} }
  }
  setSidebar(collapsed, false);
  toggle.addEventListener('click', () => setSidebar(!collapsed));
  document.addEventListener('keydown', e => {
    if (e.key === 'Escape' && !collapsed) {setSidebar(true); toggle.focus();}
  });
  const reduced = matchMedia('(prefers-reduced-motion: reduce)');
  const targets = document.querySelectorAll('.evaluation-stage,.results-head,.stat-card,.chart-card,.table-card,.topology-metrics,.topology-layout');
  let observer;
  function setupMotion() {
    if (observer) observer.disconnect();
    document.body.classList.toggle('motion-ready', !reduced.matches);
    if (reduced.matches || !('IntersectionObserver' in window)) {
      targets.forEach(el => el.classList.add('in-view')); return;
    }
    observer = new IntersectionObserver(entries => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {entry.target.classList.add('in-view');observer.unobserve(entry.target);}
      });
    }, {threshold:0, rootMargin:'0px 0px -30px 0px'});
    targets.forEach((el,i) => {el.classList.add('scroll-reveal');el.style.setProperty('--reveal-delay', `${el.classList.contains('stat-card') ? i%4*65 : 0}ms`);observer.observe(el);});
  }
  setupMotion(); reduced.addEventListener('change', setupMotion);
  let queued = false;
  function paintScroll() {
    queued = false;
    const hero = document.querySelector('.hero');
    if (!hero || reduced.matches) return;
    const amount = Math.max(0, Math.min(1, -hero.getBoundingClientRect().top / Math.max(1, hero.offsetHeight)));
    hero.style.setProperty('--hero-shift', `${amount * 100}px`);
    hero.style.setProperty('--hero-rotate', `${amount * 24}deg`);
    document.querySelector('.topbar').classList.toggle('scrolled', window.scrollY > 24);
  }
  window.addEventListener('scroll', () => {if(!queued){queued=true;requestAnimationFrame(paintScroll);}}, {passive:true});
  window.addEventListener('hashchange', () => requestAnimationFrame(paintScroll));
  paintScroll();
})();
