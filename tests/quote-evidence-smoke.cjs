// Synthetic browser requests are intercepted; no real quotation is submitted.
const {chromium}=require('playwright'),assert=require('node:assert/strict');
const base=process.env.GB_QUOTE_BASE||'https://broker.aivisibilityworks.com';
(async()=>{const browser=await chromium.launch();try{
 for(const width of [390,1280]){
  const context=await browser.newContext({viewport:{width,height:900}}),page=await context.newPage();
  await page.addInitScript(()=>localStorage.setItem('gb_access_token','synthetic-quote-browser-fixture'));
  const calls=[],quotes=[];let attempts=0;
  await page.route('**/rest/v1/rpc/gb_quote_evidence_workspace',r=>r.fulfill({json:{opportunities:[{id:'fixture-opportunity',title:'Synthetic pump opportunity'}],quotes}}));
  await page.route('**/rest/v1/rpc/gb_submit_quote_evidence',r=>{const body=r.request().postDataJSON();calls.push(body);if(++attempts===1)return r.fulfill({status:503,json:{}});quotes.push({request_id:body.p_request_id,opportunity_id:body.p_opportunity_id,quote:body.p_quote,status:'pending_review'});return r.fulfill({json:{request_id:body.p_request_id,status:'pending_review'}})});
  await page.goto(base+'/quote-evidence?fixture='+Date.now(),{waitUntil:'domcontentloaded'});
  await page.locator('#quoteForm').waitFor({state:'visible'});
  await page.locator('#opportunity').selectOption('fixture-opportunity');
  const values={counterparty:'<img src=x onerror=alert(1)>',reference:'SYNTHETIC-NOT-A-REAL-QUOTE',quote_date:new Date().toISOString().slice(0,10),valid_until:'2099-12-31',amount:'10.50',currency:'usd',quantity:'25',price_unit:'piece',source_url:'https://example.invalid/quote'};
  for(const [name,value] of Object.entries(values))await page.locator('[name="'+name+'"]').fill(value);
  await page.locator('#save').click();
  await page.waitForFunction(()=>document.getElementById('status').textContent.includes('İşlem tamamlanamadı'));
  assert.equal(quotes.length,0);
  await page.locator('#save').click();
  await page.waitForFunction(()=>document.getElementById('status').textContent.includes('Kaydedildi'));
  await page.locator('#quotes article').waitFor();
  assert.equal(calls.length,2);assert.equal(calls[0].p_request_id,calls[1].p_request_id);
  assert.equal(calls[1].p_quote.currency,'USD');assert.equal(quotes.length,1);
  assert.match(await page.locator('#quotes').innerText(),/İnceleme bekliyor/);
  assert.equal(await page.locator('#quotes img').count(),0);
  assert.ok((await page.locator('#quotes').innerText()).includes(values.counterparty));
  assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
  assert.deepEqual(await page.evaluate(()=>Object.keys(localStorage)),['gb_access_token']);
  console.log('QUOTE_EVIDENCE_UI_PASS width='+width+' retry=same_request status=pending_review external_writes=blocked');
  await context.close();
 }
 for(const authenticated of [false,true]){
  const context=await browser.newContext(),page=await context.newPage();
  if(authenticated)await page.addInitScript(()=>localStorage.setItem('gb_access_token','synthetic-aal1'));
  await page.route('**/rest/v1/rpc/**',r=>r.fulfill({status:403,json:{message:'admin_aal2_required'}}));
  await page.goto(base+'/quote-evidence?denied='+Date.now(),{waitUntil:'domcontentloaded'});
  await page.locator('#signin').waitFor({state:'visible'});
  assert.equal(await page.locator('#quoteForm').isVisible(),false);
  assert.equal(await page.locator('#inbox').isVisible(),false);
  await context.close();
 }
 console.log('QUOTE_EVIDENCE_AUTH_UI_PASS anonymous_and_rejected_session');
}finally{await browser.close()}})().catch(e=>{console.error(e);process.exitCode=1});
