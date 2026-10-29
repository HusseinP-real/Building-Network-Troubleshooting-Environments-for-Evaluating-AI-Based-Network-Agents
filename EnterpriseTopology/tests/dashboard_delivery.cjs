/* Browser regression tests against the visibly labelled MOCK executor fixture.
 * Requires Node + Playwright and an installed Chromium/Chrome; no model calls.
 * NODE_PATH=<node_modules> BROWSER_EXECUTABLE=<chrome> node --test tests/dashboard_delivery.cjs
 */
const test = require('node:test');
const assert = require('node:assert/strict');
const {spawn} = require('node:child_process');
const path = require('node:path');
const {chromium} = require('playwright');

test('Client benchmark browser workflows (MOCK execution only)', {timeout: 120000}, async t => {
  const fixture = spawn(process.env.NIKA_TEST_PYTHON || 'python3',
    [path.join(__dirname, 'serve_dashboard_fixture.py'), '--port', '0'],
    {stdio: ['ignore', 'pipe', 'pipe']});
  let errors = '', output = '';
  fixture.stderr.on('data', chunk => { errors += chunk; });
  t.after(() => fixture.kill('SIGINT'));
  const url = await new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(Error('Fixture start timed out: ' + errors)), 10000);
    fixture.stdout.on('data', chunk => {
      output += chunk;
      const match = output.match(/http:\/\/127\.0\.0\.1:\d+/);
      if (match) { clearTimeout(timer); resolve(match[0]); }
    });
    fixture.once('exit', code => { clearTimeout(timer); reject(Error(`Fixture exited ${code}: ${errors}`)); });
  });
  const browser = await chromium.launch({headless: true,
    ...(process.env.BROWSER_EXECUTABLE ? {executablePath: process.env.BROWSER_EXECUTABLE} : {})});
  t.after(() => browser.close());
  async function open(viewport = {width: 1440, height: 1000}) {
    const page = await browser.newPage({viewport, reducedMotion: 'reduce'});
    await page.goto(url);
    await page.waitForFunction(() => !document.getElementById('runButton').disabled);
    assert.match(await page.locator('body').innerText(), /MOCK executor/);
    await page.locator('#evaluationSettings > summary').click();
    await choose(page, 'evaluationScope', 'Selected generic fault');
    return page;
  }
  async function choose(page, id, title) {
    await page.locator(`#${id}Trigger`).click();
    await page.locator(`#${id}Menu`).getByText(title, {exact: true}).click();
  }

  await t.test('original suite submits twenty tickets with Opus and a fixed Haiku judge', async () => {
    const page = await open();
    try {
      await choose(page, 'evaluationScope', 'Original Enterprise benchmark · 20 tickets');
      await choose(page, 'model', 'Claude Opus 5.5');
      await choose(page, 'judgeModel', 'Claude Haiku 5.5');
      assert.match(await page.locator('#evaluationTarget').innerText(), /20 diagnoses/);
      assert.equal(await page.locator('#faultSelect').isDisabled(), true);
      const submitted = page.waitForRequest(request => request.url().endsWith('/api/run') && request.method() === 'POST');
      await page.locator('#runButton').click();
      const payload = (await submitted).postDataJSON();
      assert.equal(payload.scope, 'enterprise20');
      assert.equal(payload.repeats, 1);
      assert.equal(payload.model, 'claude-opus-5-5');
      assert.equal(payload.judge_model, 'claude-haiku-5-5');
      await page.waitForFunction(() => document.getElementById('runBadge').textContent === 'Complete');
      await page.waitForFunction(() => document.getElementById('runsTable').textContent.includes('compound-ospf-gateway'));
    } finally { await page.close(); }
  });

  await t.test('GPT options explicitly submit Codex subscription agent and judge', async () => {
    const page = await open();
    try {
      await choose(page, 'evaluationScope', 'Original Enterprise benchmark · 20 tickets');
      await choose(page, 'model', 'GPT-6.1 Sol · Codex subscription');
      await choose(page, 'judgeModel', 'GPT-6.1 Terra · Codex subscription');
      const submitted = page.waitForRequest(request => request.url().endsWith('/api/run') && request.method() === 'POST');
      await page.locator('#runButton').click();
      const payload = (await submitted).postDataJSON();
      assert.equal(payload.model, 'gpt-6.1-sol');
      assert.equal(payload.judge_model, 'gpt-6.1-terra');
      assert.equal(payload.scope, 'enterprise20');
      await page.waitForFunction(() => document.getElementById('runBadge').textContent === 'Complete');
    } finally { await page.close(); }
  });

  await t.test('selected generic fault and topology reach the benchmark report', async () => {
    const page = await open();
    try {
      const submitted = page.waitForRequest(request => request.url().endsWith('/api/run') && request.method() === 'POST');
      await page.locator('#runButton').click();
      const payload = (await submitted).postDataJSON();
      assert.equal(payload.topology_id, 'enterprise-75');
      assert.equal(payload.fault_id, 'link_down');
      assert.equal(payload.scope, 'selected');
      await page.waitForFunction(() => document.getElementById('runBadge').textContent === 'Complete');
      await page.waitForFunction(() => document.getElementById('runsTable').textContent.includes('link_down'));
      assert.match(await page.locator('#reportContext').innerText(), /MOCK FIXTURE/);
    } finally { await page.close(); }
  });

  await t.test('all thirteen maps offer the same five generic faults', async () => {
    const page = await open();
    try {
      assert.equal(await page.locator('#topologySelect option').count(), 13);
      await page.locator('#navTopology').click();
      const ids = await page.locator('#mapTopologySelect option').evaluateAll(options => options.map(option => option.value));
      for (const id of ids) {
        await page.locator('#mapTopologySelect').selectOption(id);
        await page.waitForFunction(id => document.getElementById('topologySelect').value === id &&
          !document.getElementById('faultSelect').disabled && document.getElementById('faultSelect').options.length === 5, id);
        assert.deepEqual(await page.locator('#faultSelect option').evaluateAll(options => options.map(option => option.value)),
          ['link_down', 'wrong_gateway', 'route_blackhole', 'traffic_filter', 'healthy_control']);
        const inventory = await (await page.request.get(`${url}/api/topology?id=${id}`)).json();
        assert.ok(Object.values(inventory.nodes).filter(node => !node.virtual).length >= 75);
      }
    } finally { await page.close(); }
  });

  await t.test('validation enables only the selected topology and fault', async () => {
    const page = await open();
    try {
      await page.locator('#navTopology').click();
      await page.locator('#mapTopologySelect').selectOption('multisite');
      await page.waitForFunction(() => document.getElementById('topologySelect').value === 'multisite' && !document.getElementById('validateFaultButton').disabled);
      await page.locator('#navDashboard').click();
      assert.equal(await page.locator('#runButton').isDisabled(), true);
      await choose(page, 'faultSelect', 'Incorrect default gateway');
      await page.locator('#validateFaultButton').click();
      await page.waitForFunction(() => !document.getElementById('runButton').disabled);
      await choose(page, 'faultSelect', 'Destination route blackhole');
      assert.equal(await page.locator('#runButton').isDisabled(), true);
      await choose(page, 'faultSelect', 'Incorrect default gateway');
      const submitted = page.waitForRequest(request => request.url().endsWith('/api/run') && request.method() === 'POST');
      await page.locator('#runButton').click();
      const payload = (await submitted).postDataJSON();
      assert.equal(payload.topology_id, 'multisite');
      assert.equal(payload.fault_id, 'wrong_gateway');
      await page.waitForFunction(() => document.getElementById('runBadge').textContent === 'Complete');
    } finally { await page.close(); }
  });

  await t.test('pending generic injection blocks runs until recovery completes', async () => {
    const page = await open();
    try {
      await page.locator('#manualTools > summary').click();
      await page.locator('#injectButton').click();
      await page.waitForFunction(() => document.getElementById('manualStatus').textContent.includes('succeeded'));
      assert.equal(await page.locator('#runButton').isDisabled(), true);
      assert.match(await page.locator('#recoveryNoticeText').innerText(), /1 pending/);
      await page.locator('#recoverButton').click();
      await page.waitForFunction(() => !document.getElementById('runButton').disabled);
    } finally { await page.close(); }
  });

  await t.test('healthy control has no injection and can be validated independently', async () => {
    const page = await open();
    try {
      await choose(page, 'faultSelect', 'Healthy network');
      await page.locator('#manualTools > summary').click();
      assert.equal(await page.locator('#injectButton').isDisabled(), true);
      await page.locator('#validateFaultButton').click();
      await page.waitForFunction(() => !document.getElementById('runButton').disabled);
      assert.match(await page.locator('#faultKind').innerText(), /no fault injected/);
    } finally { await page.close(); }
  });

  await t.test('mobile form remains usable without horizontal page overflow', async () => {
    const page = await open({width: 390, height: 844});
    try {
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);
      await page.locator('#faultSelectTrigger').focus();
      await page.keyboard.press('ArrowDown');
      await page.keyboard.press('End');
      await page.keyboard.press('Enter');
      assert.equal(await page.locator('#faultSelect').inputValue(), 'healthy_control');
    } finally { await page.close(); }
  });
});
