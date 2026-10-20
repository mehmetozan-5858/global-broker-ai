// Browser RPC writes are intercepted; no customer or provider record is created.
const {chromium,webkit}=require('playwright'),assert=require('node:assert/strict');
const base=process.env.GB_MEMBERSHIP_BASE||'https://broker.aivisibilityworks.com';
(async()=>{for(const engine of [chromium,webkit]){const browser=await engine.launch();try{
for(const width of (engine===webkit?[390]:[320,390,1280])){
 const context=await browser.newContext({viewport:{width,height:900}}),page=await context.newPage();
 await page.addInitScript(()=>localStorage.setItem('gb_access_token','synthetic-membership-fixture'));
 const catalog=[{id:'sector',name:'Sector Access',amount_minor:8900,currency:'USD'},{id:'multi',name:'Multi-Sector',amount_minor:17900,currency:'USD'},{id:'global',name:'Global Access',amount_minor:34900,currency:'USD'}],rows=[],calls=[];
 await page.route('**/rest/v1/rpc/gb_membership_workspace',r=>r.fulfill({json:{checkout_enabled:false,current_plan:'free',catalog,requests:rows}}));
 await page.route('**/rest/v1/rpc/gb_request_membership',r=>{const body=r.request().postDataJSON();calls.push(body);if(!rows.length){rows.push({request_id:body.p_request_id,plan_id:body.p_plan_id,status:'awaiting_provider',invoice_status:'not_issued'});return r.fulfill({status:503,json:{}})}return r.fulfill({json:{request_id:rows[0].request_id,status:'awaiting_provider',duplicate:true}})});
 await page.goto(base+'/pricing');await page.getByRole('link',{name:'Üyelik talebi oluştur'}).nth(1).click();await page.locator('#workspace').waitFor({state:'visible'});
 assert.equal(await page.locator('#plan').inputValue(),'multi');assert.match(await page.locator('#price').innerText(),/179/);
 await page.locator('#save').click();assert.equal(calls.length,0,'acknowledgement is required');
 await page.locator('#consent').check();await page.locator('#save').click();await page.getByText(/İşlem tamamlanamadı/).waitFor();
 await page.locator('#save').click();await page.getByText(/Üyelik talebi kaydedildi/).waitFor();await page.locator('#requests li').filter({hasText:'Multi-Sector'}).waitFor();
 assert.equal(calls.length,2);assert.equal(calls[0].p_request_id,calls[1].p_request_id);assert.deepEqual(Object.keys(calls[0]).sort(),['p_plan_id','p_request_id','p_terms_accepted']);assert.equal(calls[0].p_terms_accepted,true);
 assert.equal(await page.locator('#requests li').count(),1);assert.equal(await page.locator('#currentPlan').innerText(),'free');assert.match(await page.locator('#requests').innerText(),/Fatura düzenlenmedi/);
 assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));assert.deepEqual(await page.evaluate(()=>Object.keys(localStorage)),['gb_access_token']);
 console.log('MEMBERSHIP_UI_PASS engine='+engine.name()+' width='+width+' retry=same_id amount=server_catalog current_plan=free checkout=closed external_writes=blocked');await context.close();
}
const denied=await browser.newContext(),page=await denied.newPage();await page.route('**/rest/v1/rpc/**',r=>r.fulfill({status:403,json:{}}));await page.goto(base+'/membership');await page.locator('#signin').waitFor({state:'visible'});assert.equal(await page.locator('#workspace').isVisible(),false);assert.match(await page.locator('#signin a').getAttribute('href'),/next=\/membership/);await denied.close();
}finally{await browser.close()}}})().catch(error=>{console.error(error);process.exitCode=1});
