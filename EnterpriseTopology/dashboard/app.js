const $ = (id) => document.getElementById(id);
const axes = [
  ['detection_correct', 'Detection', 'Detect'],
  ['device_correct', 'Device', 'Device'],
  ['localization_correct', 'Resource', 'Resource'],
  ['fault_type_correct', 'Fault type', 'Fault'],
  ['rca_exact', 'Exact RCA', 'Exact RCA'],
];
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
function matrix(report) {
  const box = $('matrixChart');
  box.replaceChildren();
  const grid = element('div', 'matrix-grid');
  grid.append(element('div', 'matrix-col', 'ATTEMPT'));
  axes.forEach(([, , short]) => grid.append(element('div', 'matrix-col', short.toUpperCase())));
  const counts = {};
  (report.runs || []).forEach((run, runIndex) => {
    counts[run.case] = (counts[run.case] || 0) + 1;
    const name = caseNames[run.case] || run.case || 'Unknown';
    grid.append(element('div', 'matrix-row', `${name} · ${String(counts[run.case]).padStart(2, '0')}`));
    axes.forEach(([key]) => {
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
  $('exactValue').textContent = pct(rate(report, 'rca_exact'));
  $('exactCount').textContent = `${report.metrics?.rca_exact?.correct ?? 0} / ${report.attempted ?? 0} attempts`;
  $('completeValue').textContent = `${report.complete_runs ?? 0}/${report.attempted ?? 0}`;
  const seconds = runs.map(r => r.wall_seconds).filter(v => typeof v === 'number');
  $('timeValue').textContent = seconds.length ? `${fmtNumber(seconds.reduce((a, b) => a + b, 0) / seconds.length)}s` : '—';
  const calls = runs.map(r => r.tool_calls).filter(v => typeof v === 'number');
  $('callsValue').textContent = calls.length ? String(calls.reduce((a, b) => a + b, 0)) : '—';
  $('reportMeta').textContent = `${report.attempted ?? 0} ATTEMPTS · ${report.scored ?? 0} SCORED`;
  radar(report); matrix(report);
  bars(report, 'durationChart', 'wall_seconds', 's');
  bars(report, 'toolChart', 'tool_calls', '');
  const table = $('runsTable'); table.replaceChildren();
  runs.forEach(run => {
    const tr = element('tr');
    tr.append(element('td', 'table-case', caseNames[run.case] || run.case));
    tr.append(element('td', '', run.model || '—'));
    [run.score?.rca_exact, run.injection_verified, run.repair_verified].forEach(v => {
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
    const option = element('option', '', `${date} · ${pct(item.exact_rate)} · ${item.model || 'Unknown'}`);
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
function progress(lines, repeats, running, successful) {
  const total = repeats * 3;
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
    $('runLabel').textContent = state.running ? 'Benchmark running…' : 'Run benchmark';
    if (state.started_at) {
      $('runPanel').hidden = false;
      $('runLog').textContent = state.lines.join('\n');
      progress(state.lines, state.repeats || 1, state.running, state.returncode === 0);
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
    await json('/api/run', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({model: $('model').value.trim(), repeats: Number($('repeats').value)})});
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
