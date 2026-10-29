/* Isolated browser acceptance. All remote requests are mocked or rejected. */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {spawn, execFileSync} = require('node:child_process');
const {chromium} = require('playwright');
const root = path.resolve(__dirname, '..');
const contract = require('../web/ecosystem-contract.js');
const peer = require(path.resolve(process.env.AI_VISIBILITY_ROOT, 'lib/ecosystem-contract.cjs'));
const fixture = JSON.parse(execFileSync('python3', ['-c', `
import json
from src.public_opportunity_projection import project_public_opportunity
row={'id':'release-fixture','source':'TED','title':'Fixture equipment','country_code':'DE',
     'quantity':'999 units','source_lot_selection_required':True,
     'export_goods_review':{'status':'goods_candidate'},
     'buyer_name':'PRIVATE-BUYER','document_extracted_text':'PRIVATE-DOCUMENT',
     'specification_analysis':{'document_coverage_blockers':['source_text_truncated','attachment_candidates_skipped','attachment_downloads_failed','document_versions_require_review']}}
print(json.dumps(project_public_opportunity(project_public_opportunity(row))))
`], {cwd: root, encoding: 'utf8'}));

async function noOverflow(page, label) {
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false, label);
}

(async () => {
  const server = spawn('python3', ['-u', '-c', "from http.server import ThreadingHTTPServer; from render_server import Handler; s=ThreadingHTTPServer(('127.0.0.1',0),Handler); print(s.server_port,flush=True); s.serve_forever()"], {cwd: root, stdio: ['ignore', 'pipe', 'ignore']});
  let browser;
  try {
    const port = await new Promise((resolve, reject) => {
      const timer = setTimeout(() => reject(Error('local server startup timeout')), 15000);
      server.stdout.once('data', data => { clearTimeout(timer); resolve(Number(String(data).trim())); });
      server.once('error', reject);
      server.once('exit', code => { clearTimeout(timer); reject(Error('local server exited '+code)); });
    });
    const base = 'http://127.0.0.1:' + port;
    for (const route of ['/api/opportunities', '/data/latest-opportunities.json', '/api/admin_opportunities', '/api/private_room']) {
      assert.equal((await fetch(base + route)).status, 401, route);
    }
    browser = await chromium.launch({executablePath: process.env.CHROME_PATH || undefined});
    for (const width of [320, 390, 1280]) {
      const context = await browser.newContext({viewport: {width, height: 900}, serviceWorkers: 'block'});
      const page = await context.newPage();
      page.setDefaultTimeout(10000);
      let mode = 'success', contactStatus = 503;
      const contactIds = [], unexpected = [], errors = [];
      page.on('pageerror', error => errors.push(error.message));
      await context.route('**/*', route => {
        const req = route.request(), url = new URL(req.url());
        if (url.pathname.endsWith('/rpc/my_broker_access')) return route.fulfill({json: {entitlement: {all_sectors: true, plan_id: 'fixture'}, preferences: {}}});
        if (url.pathname.endsWith('/rpc/my_introduction_requests')) return route.fulfill({json: []});
        if (url.origin === base && url.pathname === '/api/contact') {
          const data = req.postDataJSON(); contactIds.push(data.id);
          return route.fulfill({status: contactStatus, json: contactStatus === 200 ? {ok: true, id: data.id, state: 'email_accepted'} : {error: 'unavailable', to: 'PRIVATE-OWNER'}});
        }
        if (url.origin === base && url.pathname === '/data/latest-opportunities.json') {
          if (typeof mode === 'number') return route.fulfill({status: mode, json: {error: 'PRIVATE-TRACE'}});
          if (mode === 'network') return route.abort();
          if (mode === 'malformed') return route.fulfill({json: {private: 'PRIVATE-TRACE'}});
          return route.fulfill({json: {opportunities: mode === 'empty' ? [] : [fixture]}});
        }
        // Navigation is captured before reaching AI Visibility; no lead is sent.
        if (url.origin === 'https://www.aivisibilityworks.com' && url.pathname === '/yeni-musteri') return route.fulfill({contentType: 'text/html', body: '<title>Captured handoff only</title>'});
        if (url.origin === base && req.method() === 'GET') return route.continue();
        unexpected.push(req.method() + ' ' + url.origin + url.pathname);
        return route.abort();
      });
      await page.addInitScript(() => localStorage.setItem('gb_access_token', 'fixture-only'));
      for (const language of ['tr', 'en']) {
        for (const [state, heading] of [['success', 'Fixture equipment'], [401, 'Yeniden giriş yapın'], [403, 'Hesap erişiminizi kontrol edin'], [429, 'İstek sınırına ulaşıldı'], [503, 'Fırsatlar yüklenemedi'], ['network', 'Fırsatlar yüklenemedi'], ['malformed', 'Fırsatlar yüklenemedi'], ['empty', null]]) {
          mode = state;
          await page.goto(base + '/privacy');
          await page.setContent('<html lang="'+language+'"><head><meta name="viewport" content="width=device-width,initial-scale=1"></head><body style="margin:0;font-family:system-ui"><main><section id="cards"></section></main></body></html>');
          await page.addScriptTag({path: path.join(root, 'web/customer-portal.js')});
          if (heading) await page.getByRole('heading', {name: heading, exact: true}).waitFor();
          else await page.getByText('Bu filtrelerle eşleşen fırsat yok.', {exact: true}).waitFor();
          const body = await page.locator('body').innerText();
          for (const secret of ['PRIVATE-BUYER', 'PRIVATE-DOCUMENT', 'PRIVATE-TRACE', '999 units']) assert.equal(body.includes(secret), false);
          if (state === 'success') {
            const warnings = language === 'tr' ? ['Resmî belge metni eksik okundu', 'Bazı resmî teknik ekler incelenemedi', 'Bazı resmî belgeler okunamadı', 'Birden fazla belge sürümü bulundu'] : ['Official document text is incomplete', 'Some official annexes have not been reviewed', 'Some official documents could not be read', 'Multiple document versions were found'];
            for (const warning of warnings) assert(body.includes(warning), language+' missing '+warning);
          }
          await noOverflow(page, 'customer '+width+' '+language+' '+state);
        }
        console.log('CUSTOMER_NEGATIVE_MATRIX_PASS', width, language, 'cases=8');
      }
      await page.goto(base + '/contact');
      for (const [label, value] of [['Adınız', 'Fixture Person'], ['Yanıt alacağınız e-posta', 'fixture@example.test'], ['Konu', 'Local acceptance'], ['Mesajınız', 'This is isolated fixture data; never send externally.']]) await page.getByLabel(label, {exact: true}).fill(value);
      await page.getByRole('button', {name: 'Mesajı gönder', exact: true}).click();
      await page.getByText(/Mesajınızın kaydedildiği doğrulanamadı/).waitFor();
      const receipt = contactIds.at(-1); contactStatus = 200;
      await page.getByRole('button', {name: 'Mesajı gönder', exact: true}).click();
      await page.getByText(/e-posta servisine iletildi/).waitFor();
      assert.equal(contactIds.at(-1), receipt);
      assert.equal((await page.locator('body').innerText()).includes('PRIVATE-OWNER'), false);
      await noOverflow(page, 'contact '+width);
      console.log('CONTACT_FIXTURE_PASS', width, 'retry_receipt=preserved external_send=false');

      const profile = {businessName: 'Fixture & <Company>', website: 'https://example.com/?token=PRIVATE#secret', country: 'Türkiye', sector: 'B2B / Sanayi', email: 'PRIVATE', access_token: 'PRIVATE'};
      await page.goto(base + '/web/ecosystem.html');
      for (const key of ['businessName', 'website', 'country']) await page.locator('[name='+key+']').fill(profile[key]);
      await page.locator('[name=sector]').selectOption(profile.sector);
      await page.getByRole('button', {name: /Bilgilerimle AI Visibility’ye geç/}).click();
      await page.waitForURL('https://www.aivisibilityworks.com/yeni-musteri#**');
      const transferred = peer.parse(new URL(page.url()).hash);
      assert.deepEqual(transferred.business, {...contract.clean(profile)});
      assert.deepEqual(Object.keys(transferred.business).sort(), ['businessName', 'country', 'sector', 'website']);
      const back = new URL(peer.build(transferred.business, 'broker'));
      assert.deepEqual(contract.parse(back.hash).business, transferred.business);
      await page.goto(base + back.pathname + back.hash);
      await page.getByRole('button', {name: 'Bilgileri forma al', exact: true}).click();
      assert.equal(new URL(page.url()).hash, '');
      for (const key of ['businessName', 'website', 'country', 'sector']) assert.equal(await page.locator('[name='+key+']').inputValue(), transferred.business[key]);
      await noOverflow(page, 'handoff '+width);
      console.log('PINNED_PEER_CONTRACT_AND_BROKER_UI_PASS', width, 'visibility_ui_and_live_acceptance=false');
      await page.evaluate(() => localStorage.clear());
      await page.goto(base + '/app');
      await page.waitForURL('**/account?next=/app');
      assert.equal(await page.locator('#app').count(), 0);
      assert.deepEqual(unexpected, []);
      assert.deepEqual(errors, []);
      await context.close();
    }
    console.log('RELEASE_BROWSER_EVIDENCE_PASS widths=320,390,1280 languages=tr,en live_writes=false');
  } finally {
    if (browser) await browser.close();
    server.kill();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
