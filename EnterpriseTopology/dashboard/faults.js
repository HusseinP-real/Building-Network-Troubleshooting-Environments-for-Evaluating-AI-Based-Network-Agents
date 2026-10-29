/* Material-style select presentation; native selects retain all application state. */
(() => {
  const fields = [], arrow = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="m7 10 5 5 5-5"/></svg>';
  let active = null;
  function close() {
    if (!active) return;
    const field = active; active = null;
    field.trigger.setAttribute('aria-expanded', 'false');
    field.trigger.removeAttribute('aria-activedescendant');
    field.anchor.classList.remove('menu-open');
    if (field.menu.hidePopover && field.menu.matches(':popover-open')) field.menu.hidePopover();
    field.menu.hidden = true;
  }
  function position(field) {
    if (active !== field) return;
    const rect = field.anchor.getBoundingClientRect(), gap = 8, inset = 16;
    if (rect.bottom < 0 || rect.top > innerHeight) return close();
    const below = innerHeight - rect.bottom - inset - gap, above = rect.top - inset - gap;
    const bottom = below >= Math.min(field.menu.scrollHeight, 240) || below >= above;
    const height = Math.max(80, Math.min(352, bottom ? below : above));
    const width = Math.min(Math.max(rect.width, 280), innerWidth - inset * 2);
    Object.assign(field.menu.style, {width: `${width}px`, maxHeight: `${height}px`,
      left: `${Math.max(inset, Math.min(rect.left, innerWidth - width - inset))}px`,
      top: `${bottom ? rect.bottom + gap : Math.max(inset, rect.top - gap - Math.min(field.menu.scrollHeight, height))}px`});
  }
  function highlight(field, index) {
    field.index = index;
    field.items.forEach((item, i) => item.classList.toggle('active-option', i === index));
    const item = field.items[index];
    if (item) {
      field.trigger.setAttribute('aria-activedescendant', item.id);
      item.scrollIntoView({block: 'nearest'});
    }
  }
  function choose(field, index) {
    const option = field.select.options[index];
    if (!option || option.disabled || field.select.disabled) return;
    field.select.value = option.value;
    close(); field.sync();
    field.select.dispatchEvent(new Event('input', {bubbles: true}));
    field.select.dispatchEvent(new Event('change', {bubbles: true}));
    field.trigger.focus({preventScroll: true});
  }
  function build(field) {
    field.menu.replaceChildren(); field.items = [];
    Array.from(field.select.options).forEach((option, index) => {
      const item = document.createElement('div');
      item.id = `${field.select.id}-option-${index}`; item.className = 'md-menu-option';
      item.setAttribute('role', 'option'); item.setAttribute('aria-selected', String(option.selected));
      item.setAttribute('aria-disabled', String(option.disabled));
      const copy = document.createElement('span'), title = document.createElement('span'), check = document.createElement('span');
      copy.className = 'md-option-copy'; title.className = 'md-option-title'; title.textContent = option.textContent;
      copy.append(title);
      if (option.dataset.supportingText) {
        const supporting = document.createElement('span'); supporting.className = 'md-option-support';
        supporting.textContent = option.dataset.supportingText; copy.append(supporting);
      }
      check.className = 'md-option-check'; check.setAttribute('aria-hidden', 'true'); check.textContent = option.selected ? '✓' : '';
      item.append(copy, check);
      item.addEventListener('pointerdown', event => event.preventDefault());
      item.addEventListener('click', () => choose(field, index));
      item.addEventListener('pointermove', () => { if (!option.disabled) highlight(field, index); });
      field.menu.append(item); field.items.push(item);
    });
  }
  function open(field) {
    if (field.select.disabled || !field.select.options.length) return;
    close(); active = field; build(field);
    field.menu.hidden = false;
    if (field.menu.showPopover) field.menu.showPopover();
    field.anchor.classList.add('menu-open'); field.trigger.setAttribute('aria-expanded', 'true');
    position(field);
    highlight(field, Math.max(0, field.select.selectedIndex));
  }
  document.querySelectorAll('select[data-md-select]').forEach(select => {
    const anchor = select.parentElement, label = anchor.querySelector('label');
    const trigger = document.createElement('input'), chevron = document.createElement('span'), menu = document.createElement('div');
    trigger.id = `${select.id}Trigger`; trigger.type = 'text'; trigger.readOnly = true;
    trigger.className = 'md-select-trigger'; trigger.setAttribute('role', 'combobox');
    trigger.setAttribute('aria-haspopup', 'listbox'); trigger.setAttribute('aria-expanded', 'false');
    trigger.setAttribute('aria-autocomplete', 'none'); trigger.setAttribute('autocomplete', 'off');
    if (select.getAttribute('aria-describedby')) trigger.setAttribute('aria-describedby', select.getAttribute('aria-describedby'));
    menu.id = `${select.id}Menu`; menu.className = 'md-select-menu'; menu.hidden = true;
    menu.setAttribute('role', 'listbox'); menu.setAttribute('aria-labelledby', label.id);
    if ('showPopover' in menu) menu.setAttribute('popover', 'manual');
    trigger.setAttribute('aria-controls', menu.id);
    label.htmlFor = trigger.id;
    chevron.className = 'md-field-chevron'; chevron.innerHTML = arrow;
    anchor.append(trigger, chevron); anchor.classList.add('is-enhanced');
    select.hidden = true; document.body.append(menu);
    const field = {select, anchor, trigger, menu, index: 0, items: [], signature: '', value: null, buffer: '', typedAt: 0};
    field.sync = () => {
      trigger.disabled = select.disabled;
      trigger.value = select.selectedOptions[0]?.textContent || 'Select an option';
      const signature = Array.from(select.options).map(option => [option.value, option.textContent, option.disabled, option.dataset.supportingText].join('|')).join('\n');
      const changed = signature !== field.signature || select.value !== field.value;
      field.signature = signature; field.value = select.value;
      if (select.disabled && active === field) close();
      if (changed && active === field) { build(field); position(field); highlight(field, Math.max(0, select.selectedIndex)); }
      anchor.classList.toggle('is-disabled', select.disabled);
    };
    trigger.addEventListener('click', () => active === field ? close() : open(field));
    trigger.addEventListener('keydown', event => {
      const options = Array.from(select.options), enabled = options.map((option, i) => option.disabled ? -1 : i).filter(i => i !== -1);
      if (event.key === 'Escape') { if (active === field) { event.preventDefault(); close(); } return; }
      if (event.key === 'Tab') { close(); return; }
      if (['ArrowDown', 'ArrowUp'].includes(event.key)) {
        event.preventDefault();
        if (active !== field) return open(field);
        const position = enabled.indexOf(field.index), offset = event.key === 'ArrowDown' ? 1 : -1;
        if (enabled.length) highlight(field, enabled[(position + offset + enabled.length) % enabled.length]);
      } else if (event.key === 'Enter' || event.key === ' ') {
        event.preventDefault(); active === field ? choose(field, field.index) : open(field);
      } else if (active === field && ['Home', 'End'].includes(event.key)) {
        event.preventDefault(); if (enabled.length) highlight(field, event.key === 'Home' ? enabled[0] : enabled.at(-1));
      } else if (event.key.length === 1 && !event.ctrlKey && !event.metaKey && !event.altKey) {
        event.preventDefault();
        const now = Date.now(); field.buffer = (now - field.typedAt < 700 ? field.buffer : '') + event.key.toLowerCase(); field.typedAt = now;
        if (active !== field) open(field);
        const index = enabled.find(i => options[i].textContent.trim().toLowerCase().startsWith(field.buffer));
        if (index !== undefined) highlight(field, index);
      }
    });
    select.addEventListener('change', field.sync);
    new MutationObserver(field.sync).observe(select, {childList: true, subtree: true, attributes: true, characterData: true});
    fields.push(field); field.sync();
  });
  document.addEventListener('pointerdown', event => { if (active && !active.anchor.contains(event.target) && !active.menu.contains(event.target)) close(); });
  document.addEventListener('focusin', event => { if (active && event.target !== active.trigger && !active.menu.contains(event.target)) close(); });
  window.addEventListener('resize', () => { if (active) position(active); });
  window.addEventListener('scroll', event => { if (active && !active.menu.contains(event.target)) position(active); }, true);
  window.materialFields = {sync: () => fields.forEach(field => field.sync())};
})();

/* Shared benchmark configuration and optional operator controls. All commands and targets are resolved by the server. */
(() => {
  const el = id => document.getElementById(id);
  let topology = '', rows = [], state = null, automatic = false, autoSubmitting = false, submitted = false, sequence = 0, loading = true, mapReady = false;
  const buttons = {baseline: 'baselineButton', inject: 'injectButton', verify: 'verifyButton', recover: 'recoverButton', validate: 'validateFaultButton'};
  const faultTitles = {'core-uplink': 'Core uplink · r5', 'core-uplink-r6': 'Core uplink · r6', 'gateway-service': 'Gateway service · r5', 'gateway-service-r8': 'Gateway service · r8', 'database-acl': 'Backend ACL · app', 'database-ingress-acl': 'Backend ACL · database', 'ospf-passive-r7': 'OSPF passive interface · r7', 'compound-uplink-acl': 'Uplink + backend ACL', 'compound-ospf-gateway': 'OSPF + gateway service', 'healthy': 'Healthy network'};
  const row = () => rows.find(item => item.id === el('faultSelect').value);
  async function request(url, options) {
    const response = await fetch(url, options);
    const data = await response.json();
    if (!response.ok) throw Error(data.error || 'Request failed');
    return data;
  }
  function render() {
    const selected = row();
    const originalOption = el('evaluationScope').querySelector('option[value=enterprise20]');
    originalOption.disabled = topology !== 'enterprise-75';
    if (originalOption.disabled && el('evaluationScope').value === 'enterprise20') el('evaluationScope').value = 'selected';
    const enterprise20 = el('evaluationScope').value === 'enterprise20';
    const canEvaluate = enterprise20 ? topology === 'enterprise-75' : selected?.evaluation_enabled;
    const pending = state?.pending || [];
    const busy = submitted || !!state?.busy || automatic || autoSubmitting;
    const ready = mapReady && !loading && selected?.execution_enabled && state?.execution_enabled;
    el('faultSelect').disabled = busy || loading || !rows.length || enterprise20;
    el('topologySelect').disabled = submitted || automatic || autoSubmitting;
    el('mapTopologySelect').disabled = el('topologySelect').disabled;
    Object.values(buttons).forEach(id => { el(id).disabled = !ready || busy; });
    el('validateFaultButton').hidden = enterprise20;
    el('validateFaultButton').disabled ||= !!pending.length;
    el('injectButton').disabled ||= selected?.kind === 'healthy' || !!pending.length;
    const owns = selected?.components.some(fault => pending.includes(fault));
    el('verifyButton').disabled ||= !owns;
    el('recoverButton').disabled ||= !owns;
    el('runButton').disabled = !ready || loading || busy || !!pending.length || !canEvaluate;
    el('evaluationScope').disabled = automatic || loading;
    const allReady = rows.filter(item => item.generic).length === 5 && rows.filter(item => item.generic).every(item => item.evaluation_enabled);
    el('evaluationScope').querySelector('option[value=all]').disabled = !allReady;
    if (!allReady && el('evaluationScope').value === 'all') el('evaluationScope').value = 'selected';
    const scope = enterprise20 ? 'Original 20 tickets · ' + (20 * Number(el('repeats').value)) + ' diagnoses · max 20 turns each' : !selected?.evaluation_enabled ? 'Fault catalog' : el('evaluationScope').value === 'all' ? '5 generic cases' : `${selected?.case_ids.length || 0} ticket case${selected?.case_ids.length === 1 ? '' : 's'}`;
    el('evaluationTarget').textContent = `${el('topologySelect').selectedOptions[0]?.textContent || topology} · ${scope}`;
    const status = busy ? ['running', automatic ? 'Benchmark running' : state?.operation?.action === 'validate' ? 'Validating selected fault…' : 'Lab busy']
      : pending.length ? ['recovery', 'Recovery required']
      : !ready ? ['catalog', selected?.execution_enabled ? 'Preparing' : 'Lab unavailable']
      : !canEvaluate ? ['catalog', 'Validation required'] : ['ready', 'Ready to run'];
    el('setupStatus').dataset.state = status[0];
    el('setupStatus').textContent = status[1];
    el('runLabel').textContent = automatic ? 'Benchmark running…' : 'Run benchmark';
    el('benchmarkSupport').textContent = loading ? 'Loading supported fault scenarios…' : enterprise20 ? 'Original 20-ticket suite, seed 42, standard investigation and individual commands. Each ticket checks the full baseline, injects its own fault(s), scores the diagnosis and restores the network. Keep the judge on Haiku 5.5 to compare with the previous 55% result.' : !selected?.evaluation_enabled
      ? selected?.execution_enabled ? 'Validate the selected fault first. This checks baseline, injects the fault, verifies its effect and restores the lab without calling a model.' : selected?.support_reason || 'Deploy the selected lab before validation.'
      : !mapReady ? 'Loading the selected topology…' : !state ? 'Unable to confirm laboratory status. Benchmark execution is disabled until the server responds.' : '';
    if (!busy && state?.operation?.action === 'validate' && state.operation.status === 'failed') el('benchmarkSupport').textContent = 'Validation failed. See Advanced laboratory debugging for the failed check and recovery details.';
    el('validateFaultButton').textContent = busy && state?.operation?.action === 'validate' ? 'Validating & restoring…' : 'Validate selected fault & recovery';
    el('recoveryNotice').hidden = !pending.length || busy;
    el('recoveryNoticeText').textContent = `${pending.length} pending laboratory change(s): ${pending.join(', ')}. Recover them to enable this benchmark.`;
    el('faultSupport').textContent = !mapReady ? 'Loading topology map; execution is disabled until the selected map is ready.' : selected?.support_reason || (loading ? 'Loading fault catalog…' : 'Fault catalog unavailable');
    el('executionTarget').textContent = state?.target ? `Execution target: ${state.target}` : 'Execution disabled for this topology.';
    el('pendingFaults').replaceChildren();
    el('pendingFaults').dataset.dirty = String(!!pending.length);
    el('pendingFaults').append(document.createTextNode(pending.length ? automatic ? `Benchmark changes awaiting automatic recovery (${pending.length}): ` : `Pending recovery (${pending.length}): ` : selected?.execution_enabled ? 'No recorded pending faults. Run a live baseline to confirm health.' : 'Catalog only. Live environment state is unavailable.'));
    pending.forEach(fault => {
      const button = document.createElement('button');
      button.textContent = automatic ? `${fault} · benchmark in progress` : `${fault} · select for recovery`;
      button.disabled = busy;
      button.onclick = () => { el('faultSelect').value = fault; details(); render(); };
      el('pendingFaults').append(button);
    });
    const op = state?.operation;
    if (op) {
      el('manualStatus').dataset.status = op.status;
      el('manualStatus').textContent = `${op.action} · ${op.fault_id} · ${op.status} · ${op.phase}${op.error ? ' · ' + op.error : ''}`;
      el('manualProgress').hidden = false;
      el('manualProgress').max = op.total;
      el('manualProgress').value = op.completed;
      el('manualLog').textContent = (op.lines || []).join('\n');
    } else {
      el('manualStatus').dataset.status = '';
      el('manualStatus').textContent = busy ? 'Experiment is busy. Manual actions are locked.' : selected?.execution_enabled ? 'Ready. Check the environment and baseline before injecting.' : 'Catalog only. Manual execution is unavailable.';
      el('manualLog').textContent = '';
      el('manualProgress').hidden = true;
    }
    window.materialFields?.sync();
  }
  function details() {
    const selected = row();
    el('faultDetail').replaceChildren();
    if (!selected) return;
    const variants = selected.case_ids.length;
    el('faultKind').textContent = selected.kind === 'healthy' ? 'Healthy control · no fault injected' : `${selected.kind === 'compound' ? 'Compound fault' : 'Actual fault'} · ${variants ? `${variants} ticket variant${variants === 1 ? '' : 's'}` : 'native scenario catalog'}`;
    for (const [label, text] of [['Description', selected.description], ['Targets / interfaces', selected.targets.join(' · ') || 'None — healthy baseline'], ['Expected impact', selected.expected_impact]]) {
      const p = document.createElement('p'), strong = document.createElement('strong');
      strong.textContent = label + ': ';
      p.append(strong, document.createTextNode(text));
      el('faultDetail').append(p);
    }
  }
  async function refresh() {
    const expected = sequence, target = topology;
    if (!target) return;
    try {
      const data = await request(`/api/manual/status?topology_id=${encodeURIComponent(target)}`);
      if (expected !== sequence) return;
      state = data;
      const catalog = await request(`/api/faults?topology_id=${encodeURIComponent(target)}`);
      if (expected !== sequence) return;
      rows = catalog;
      render();
    } catch (error) {
      if (expected !== sequence) return;
      state = null;
      render();
      el('manualStatus').textContent = `Status unavailable: ${error.message}`;
    }
  }
  async function load(id) {
    const expected = ++sequence;
    topology = id; rows = []; state = null; loading = true; mapReady = false;
    el('faultSelect').replaceChildren(); el('faultDetail').replaceChildren(); el('faultKind').textContent = '';
    render();
    try {
      const data = await request(`/api/faults?topology_id=${encodeURIComponent(id)}`);
      if (expected !== sequence) return;
      rows = data;
      data.forEach(item => {
        const option = document.createElement('option');
        option.value = item.id;
        option.textContent = item.title || faultTitles[item.id] || item.id.replace(/[-_]/g, ' ').replace(/\b(acl|ospf|bgp|dhcp|dns)\b/gi, word => word.toUpperCase()).replace(/^./, letter => letter.toUpperCase());
        option.dataset.supportingText = `${{fault: 'Actual fault', healthy: 'Healthy control', compound: 'Compound fault'}[item.kind]}${item.targets.length ? ' · ' + item.targets.join(', ') : ' · no injection'}`;
        el('faultSelect').append(option);
      });
      loading = false;
      details();
      await refresh();
    } catch (error) {
      if (expected !== sequence) return;
      loading = false; render();
      el('manualStatus').textContent = error.message;
    }
  }
  for (const [action, id] of Object.entries(buttons)) el(id).onclick = async () => {
    if (submitted || loading || !row()) return;
    submitted = true; render();
    let errorMessage = '';
    try {
      state = await request('/api/manual', {method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({topology_id: topology, fault_id: row().id, action})});
      el('manualLogDetails').open = true;
    } catch (error) {
      errorMessage = error.message;
    } finally { submitted = false; await refresh(); if (errorMessage) el('manualStatus').textContent = errorMessage; }
  };
  el('reviewRecovery').onclick = () => { el('manualTools').open = true; el('manualTools').scrollIntoView({behavior: 'smooth', block: 'center'}); };
  el('faultSelect').onchange = () => { details(); render(); };
  el('evaluationScope').onchange = render;
  el('repeats').addEventListener('change', render);
  window.addEventListener('topology-loaded', event => { if (event.detail.id === topology) { mapReady = true; render(); } });
  window.addEventListener('topology-error', event => { if (event.detail.id === topology) { mapReady = false; render(); el('faultSupport').textContent = 'Selected topology could not be loaded; execution is disabled.'; } });
  window.addEventListener('topology-selected', event => load(event.detail.id));
  window.addEventListener('benchmark-submitting', event => { autoSubmitting = event.detail; render(); });
  window.addEventListener('benchmark-status', event => { automatic = event.detail.running; render(); });
  window.faultWorkspace = {refresh, request: () => {
    if (!mapReady || loading || !row() || !state || state.busy || state.pending.length || automatic || (el('evaluationScope').value === 'enterprise20' ? topology !== 'enterprise-75' : !row().evaluation_enabled)) throw Error('Selected experiment is not ready for automatic evaluation');
    return {topology_id: topology, fault_id: row().id, scope: el('evaluationScope').value};
  }};
  setInterval(refresh, 1200);
})();
