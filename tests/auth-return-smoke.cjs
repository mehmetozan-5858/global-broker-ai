// Authentication/MFA are mocked; no password, factor or real account is changed.
const {chromium}=require('playwright'),assert=require('node:assert/strict');
const base=process.env.GB_AUTH_RETURN_BASE||'https://broker.aivisibilityworks.com';
const sdk=`window.supabase={createClient:()=>({auth:{setSession:async s=>({data:{session:s},error:null}),mfa:{getAuthenticatorAssuranceLevel:async()=>({data:{currentLevel:localStorage.getItem('gb_access_token')==='fixture-aal2'?'aal2':'aal1'}}),listFactors:async()=>({data:{totp:[{id:'fixture-factor',status:'verified',friendly_name:'Fixture TOTP'}]}}),challenge:async()=>({data:{id:'fixture-challenge'}}),verify:async o=>o.code==='222222'?{data:{access_token:'fixture-aal2',refresh_token:'fixture-refresh'}}:{error:{message:'fixture invalid code'}},enroll:async()=>{throw Error('unexpected enrollment')}}}})};`;
async function routes(page,valid=true){
 await page.route('https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2',r=>r.fulfill({contentType:'text/javascript',body:sdk}));
 await page.route('https://yhzdqrqzjruduohypvqf.supabase.co/**',r=>{const u=new URL(r.request().url()),token=r.request().headers().authorization||'';
  if(u.pathname==='/auth/v1/token')return r.fulfill({json:{access_token:'fixture-aal1',refresh_token:'fixture-refresh'}});
  if(u.pathname==='/auth/v1/user')return r.fulfill(valid?{json:{id:'fixture-user',email:'fixture@example.invalid'}}:{status:401,json:{error:'invalid session'}});
  if(u.pathname==='/rest/v1/user_roles')return r.fulfill({json:[{role:'admin'}]});
  if(u.pathname.endsWith('/my_broker_access'))return r.fulfill({json:{entitlement:{plan_id:'free'},preferences:{}}});
  if(u.pathname.endsWith('/gb_quote_evidence_workspace'))return r.fulfill(token==='Bearer fixture-aal2'?{json:{opportunities:[],quotes:[]}}:{status:403,json:{message:'admin_aal2_required'}});
  return r.fulfill({status:400,json:{error:'unexpected mock request'}});
 });
}
(async()=>{const browser=await chromium.launch();try{
 for(const width of [390,1280]){
  const context=await browser.newContext({viewport:{width,height:900}}),page=await context.newPage();await routes(page);
  await page.goto(base+'/quote-evidence',{waitUntil:'domcontentloaded'});await page.locator('#signin').waitFor({state:'visible'});
  const login=page.getByRole('link',{name:'Hesabınıza giriş yapın'});assert.equal(new URL(await login.getAttribute('href'),base).searchParams.get('next'),'/quote-evidence');await login.click();
  await page.locator('#email').fill('fixture@example.invalid');await page.locator('#password').fill('fixture-password-not-real');await page.locator('#login').click();
  try{await page.waitForURL(u=>u.pathname==='/security'&&u.searchParams.get('next')==='/quote-evidence',{waitUntil:'domcontentloaded'})}catch(error){console.error('AUTH_RETURN_DIAGNOSTIC',JSON.stringify({url:page.url(),status:await page.locator('#status').textContent().catch(()=>''),scripts:await page.locator('script[src]').evaluateAll(es=>es.map(e=>e.src))}));throw error}await page.locator('#challenge').waitFor({state:'visible'});
  assert.equal(new URL(page.url()).searchParams.get('next'),'/quote-evidence');
  await page.locator('#challengeCode').fill('111111');await page.locator('#verifyExisting').click();await page.getByText(/Kod doğrulanamadı/).waitFor();assert.equal(new URL(page.url()).pathname,'/security');
  await page.locator('#challengeCode').fill('222222');await page.locator('#verifyExisting').click();await page.waitForURL('**/quote-evidence',{waitUntil:'domcontentloaded'});await page.locator('#quoteForm').waitFor({state:'visible'});
  assert.equal(new URL(page.url()).search,'');assert.equal(new URL(page.url()).hash,'');assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
  console.log('AUTH_QUOTE_RETURN_PASS width='+width+' invalid_mfa_blocked=true external_writes=blocked');await context.close();
 }
 const context=await browser.newContext(),page=await context.newPage();await routes(page);await page.addInitScript(()=>{localStorage.setItem('gb_access_token','fixture-aal2');localStorage.setItem('gb_refresh_token','fixture-refresh')});
 await page.goto(base+'/security?next=/quote-evidence');await page.waitForURL('**/quote-evidence',{waitUntil:'domcontentloaded'});await page.locator('#quoteForm').waitFor({state:'visible'});
 await page.goto(base+'/security?next='+encodeURIComponent('https://evil.invalid'));await page.getByText('MFA doğrulandı. Bu oturum AAL2 seviyesinde.',{exact:true}).waitFor();assert.equal(new URL(page.url()).origin,base);assert.equal(new URL(page.url()).pathname,'/security');await context.close();
 const denied=await browser.newContext(),bad=await denied.newPage();await routes(bad,false);await bad.addInitScript(()=>{localStorage.setItem('gb_access_token','fixture-aal2');localStorage.setItem('gb_refresh_token','fixture-refresh')});await bad.goto(base+'/security?next=/quote-evidence');await bad.getByText(/Oturum doğrulanamadı. Hesabım ekranından/).waitFor();assert.equal(new URL(bad.url()).pathname,'/security');await denied.close();
 console.log('AUTH_RETURN_VERIFIED_SESSION_AND_SAFE_DESTINATION_PASS');
}finally{await browser.close()}})().catch(e=>{console.error(e);process.exitCode=1});
