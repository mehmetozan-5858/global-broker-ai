// Every sandbox and membership POST is intercepted; Paddle is a local stub.
const {chromium,webkit}=require('playwright'),assert=require('node:assert/strict');
const base=process.env.GB_MEMBERSHIP_BASE||'https://broker.aivisibilityworks.com';
(async()=>{for(const engine of [chromium,webkit]){const browser=await engine.launch();try{for(const width of (engine===webkit?[390]:[390,1280])){
 const context=await browser.newContext({viewport:{width,height:900}}),page=await context.newPage();
 await page.addInitScript(()=>{localStorage.setItem('gb_access_token','synthetic-billing-fixture');window.billingTest={opens:[],settings:[]};window.Paddle={Environment:{set:x=>window.billingTest.environment=x},Initialize:x=>{window.billingTest.settings.push(x.token);window.billingTest.callback=x.eventCallback},Checkout:{open:x=>window.billingTest.opens.push(x.transactionId)}}});
 const request='33333333-3333-4333-8333-333333333333',txn='txn_'+'0'.repeat(26);let receipt=false,checkoutCalls=0,invalid=true;
 await page.route('**/rest/v1/rpc/gb_membership_workspace',r=>r.fulfill({json:{checkout_enabled:false,current_plan:'free',catalog:[{id:'sector',name:'Sector Access',amount_minor:8900,currency:'USD'}],requests:[{request_id:request,plan_id:'sector'}]}}));
 await page.route('**/functions/v1/broker-billing-sandbox/**',r=>{
  const path=new URL(r.request().url()).pathname.split('/').pop();
  if(path==='workspace')return r.fulfill({json:{checkout_enabled:true,environment:'sandbox',production_access_changed:false,records:receipt?[{request_id:request,plan_id:'sector',state:'created',receipt_status:'sandbox_completed'}]:[]}});
  assert.equal(path,'checkout');assert.deepEqual(r.request().postDataJSON(),{request_id:request});checkoutCalls++;
  return r.fulfill({json:{environment:invalid?'live':'sandbox',transaction_id:txn,client_token:'test_fixture',production_access_changed:false}});
 });
 await page.goto(base+'/membership');const box=page.locator('#sandboxBilling');await box.waitFor({state:'visible'});
 assert.equal(await page.locator('#currentPlan').innerText(),'free');
 await box.getByRole('button',{name:'Test ödeme ekranını aç'}).click();await box.getByText(/Test ekranı açılamadı/).waitFor();assert.equal(await page.evaluate(()=>window.billingTest.opens.length),0,'live response rejected');
 invalid=false;await box.getByRole('button',{name:'Test ödeme ekranını aç'}).click();await box.getByText(/Test ortamı açıldı/).waitFor();
 assert.equal(await page.evaluate(()=>window.billingTest.environment),'sandbox');assert.deepEqual(await page.evaluate(()=>window.billingTest.opens),[txn]);
 await page.evaluate(()=>window.billingTest.callback({name:'checkout.completed'}));await box.getByText(/İmzalı test ödeme kaydı bekleniyor/).waitFor();assert.equal(await box.getByText(/İmzalı test ödeme kaydı doğrulandı/).count(),0,'browser callback cannot confirm a payment');
 receipt=true;await page.locator('#sandboxRefresh').click();await box.getByText(/İmzalı test ödeme kaydı doğrulandı/).waitFor();assert.equal(await box.getByRole('button',{name:'Test ödeme ekranını aç'}).isDisabled(),true);
 assert.equal(await page.locator('#currentPlan').innerText(),'free');assert.equal(checkoutCalls,2);assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
 console.log('BROKER_SANDBOX_UI_PASS engine='+engine.name()+' width='+width+' provider=stub callback_cannot_confirm=true real_access=unchanged');await context.close();
}}finally{await browser.close()}}})().catch(error=>{console.error(error);process.exitCode=1});
