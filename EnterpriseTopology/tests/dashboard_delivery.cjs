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
    return page;
  }
  async function choose(page, id, title) {
    await page.locator(`#${id}Trigger`).click();
    await page.locator(`#${id}Menu`).getByText(title, {exact: true}).click();
  }

  await t.test('selected topology/fault reaches the benchmark and its report', async () => {
    const page = await open();
    try {
      await choose(page, 'faultSelect', 'Gateway service · r8');
      const submitted = page.waitForRequest(request => request.url().endsWith('/api/run') && request.method() === 'POST');
      await page.locator('#runButton').click();
      const payload = (await submitted).postDataJSON();
      assert.equal(payload.topology_id, 'enterprise-75');
      assert.equal(payload.fault_id, 'gateway-service-r8');
      assert.equal(payload.scope, 'selected');
      await page.waitForFunction(() => document.getElementById('runBadge').textContent === 'Complete');
      await page.waitForFunction(() => document.getElementById('runsTable').textContent.includes('gateway-service-r8'));
      assert.match(await page.locator('#reportContext').innerText(), /MOCK FIXTURE/);
      assert.equal(await page.locator('#manualTools').getAttribute('open'), null);
    } finally { await page.close(); }
  });

  await t.test('topology selection refreshes faults and disables unadapted benchmark', async () => {
    const page = await open();
    try {
      // Use the real topology explorer selector, which synchronizes the run form.
      await page.locator('#navTopology').click();
      await page.locator('#mapTopologySelect').selectOption('multisite');
      await page.waitForFunction(() => document.getElementById('faultSelect').options[0]?.value === 'F01');
      assert.equal(await page.locator('#topologySelect').inputValue(), 'multisite');
      assert.equal(await page.locator('#runButton').isDisabled(), true);
      await page.locator('#navDashboard').click();
      assert.match(await page.locator('#benchmarkSupport').innerText(), /not yet adapted/);
      assert.match(await page.locator('#reportContext').innerText(), /Enterprise Topology/);
    } finally { await page.close(); }
  });

  await t.test('partial compound injection blocks benchmark until targeted recovery', async () => {
    const page = await open();
    try {
      await choose(page, 'faultSelect', 'Uplink + backend ACL');
      await page.locator('#manualTools > summary').click();
      await page.locator('#injectButton').click();
      await page.waitForFunction(() => document.getElementById('manualStatus').textContent.includes('failed'));
      assert.equal(await page.locator('#runButton').isDisabled(), true);
      assert.match(await page.locator('#recoveryNoticeText').innerText(), /2 pending/);
      await page.locator('#recoverButton').click();
      await page.waitForFunction(() => document.getElementById('manualStatus').textContent.includes('recover') && document.getElementById('manualStatus').textContent.includes('succeeded'));
      await page.waitForFunction(() => !document.getElementById('runButton').disabled);
    } finally { await page.close(); }
  });

  await t.test('healthy control cannot be manually injected', async () => {
    const page = await open();
    try {
      await choose(page, 'faultSelect', 'Healthy network');
      await page.locator('#manualTools > summary').click();
      assert.equal(await page.locator('#injectButton').isDisabled(), true);
      assert.equal(await page.locator('#runButton').isDisabled(), false);
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
      assert.equal(await page.locator('#faultSelect').inputValue(), 'compound-ospf-gateway');
    } finally { await page.close(); }
  });
});
