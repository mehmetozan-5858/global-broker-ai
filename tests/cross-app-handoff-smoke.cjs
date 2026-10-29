/* Real Broker/AI Visibility UIs on localhost; no remote write or lead submit. */
const {chromium} = require('playwright');
const assert = require('node:assert/strict');
const {spawn} = require('node:child_process');
const {createServer} = require('node:net');
const path = require('node:path');
const root = path.resolve(__dirname, '..');
const peer = path.resolve(process.env.AI_VISIBILITY_ROOT);
const contract = require('../web/ecosystem-contract.js');
async function port() {
  const server = createServer();
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  const value = server.address().port;
  await new Promise(resolve => server.close(resolve));
  return value;
}
async function ready(url, processHandle) {
  for (let attempt=0; attempt<100; attempt++) {
    if (processHandle.exitCode !== null) throw Error('server exited before readiness');
    try { if ((await fetch(url, {signal: AbortSignal.timeout(1000)})).ok) return; } catch {}
    await new Promise(resolve => setTimeout(resolve, 100));
  }
  throw Error('server readiness timeout');
}
(async () => {
  const brokerPort = await port(), visibilityPort = await port();
  const brokerBase = 'http://127.0.0.1:'+brokerPort, visibilityBase = 'http://127.0.0.1:'+visibilityPort;
  const broker = spawn('python3', ['-u','-c', `from http.server import ThreadingHTTPServer; from render_server import Handler; ThreadingHTTPServer(('127.0.0.1',${brokerPort}),Handler).serve_forever()`], {cwd:root, stdio:'ignore'});
  const visibility = spawn(process.execPath, ['node_modules/next/dist/bin/next', 'start', '--hostname', '127.0.0.1', '--port', String(visibilityPort)], {cwd:peer, stdio:'ignore', env:{...process.env, NEXT_TELEMETRY_DISABLED:'1'}});
  let browser;
  try {
    await Promise.all([ready(brokerBase+'/contact',broker), ready(visibilityBase+'/yeni-musteri',visibility)]);
    browser = await chromium.launch({executablePath:process.env.CHROME_PATH || undefined});
    for (const width of [320,390,1280]) {
      const context = await browser.newContext({viewport:{width,height:900}, serviceWorkers:'block'});
      const page = await context.newPage(); page.setDefaultTimeout(15000);
      const writes = [], external = [], errors = [];
      page.on('pageerror', error => errors.push(error.message));
      await context.route('**/*', async route => {
        const request = route.request(), url = new URL(request.url());
        if (request.method() !== 'GET') { writes.push(request.method()+' '+url.pathname); return route.abort(); }
        if ([brokerBase,visibilityBase].includes(url.origin)) return route.continue();
        const local = url.origin === 'https://www.aivisibilityworks.com' ? visibilityBase : url.origin === 'https://broker.aivisibilityworks.com' ? brokerBase : null;
        if (local) return route.fulfill({response:await route.fetch({url:local+url.pathname+url.search})});
        external.push(url.origin+url.pathname); return route.abort();
      });
      const profile={businessName:'Fixture <Company>',website:'https://example.com/?token=PRIVATE#secret',country:'Türkiye',sector:'B2B / Sanayi'};
      await page.goto(brokerBase+'/web/ecosystem.html');
      for (const key of ['businessName','website','country']) await page.locator('[name='+key+']').fill(profile[key]);
      await page.locator('[name=sector]').selectOption(profile.sector);
      await page.getByRole('button',{name:/Bilgilerimle AI Visibility’ye geç/}).click();
      const incoming = page.getByRole('region',{name:'Global Broker firma bilgileri'});
      await incoming.waitFor();
      assert.equal(new URL(page.url()).hash,'');
      assert.equal(await page.getByLabel('İşletme adı',{exact:true}).inputValue(),'');
      await page.getByRole('button',{name:'Bu firma bilgilerini kullan',exact:true}).click();
      assert.equal(await page.getByLabel('İşletme adı',{exact:true}).inputValue(),profile.businessName);
      assert.equal(await page.getByLabel('Web sitesi',{exact:true}).inputValue(),'https://example.com/');
      assert.equal(await page.getByLabel('E-posta',{exact:true}).inputValue(),'');
      assert.equal(await page.getByLabel('Telefon / WhatsApp',{exact:true}).inputValue(),'');
      assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false,'visibility overflow '+width);
      await page.getByRole('button',{name:'Global Broker’a geç →',exact:true}).click();
      await page.getByRole('button',{name:'Bilgileri forma al',exact:true}).click();
      for (const [key,value] of Object.entries(contract.clean(profile))) assert.equal(await page.locator('[name='+key+']').inputValue(),value);
      assert.equal(new URL(page.url()).hash,'');
      assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false,'broker overflow '+width);
      assert.deepEqual(writes,[], 'no application/payment/analytics submissions');
      assert.deepEqual(external,[], 'no real external requests');
      assert.deepEqual(errors,[]);
      console.log('TWO_APPLICATION_UI_ROUNDTRIP_PASS',width,'human_apply_required=true email_and_phone_empty=true remote_writes=0');
      await context.close();
    }
  } finally {
    if (browser) await browser.close();
    broker.kill(); visibility.kill();
  }
})().catch(error=>{console.error(error);process.exitCode=1;});
