/* All Auth requests are intercepted; never sends email or updates real passwords. */
const assert=require('node:assert/strict');
const {chromium}=require('playwright');
const {spawn}=require('node:child_process');
const path=require('node:path');
const root=path.resolve(__dirname,'..');
(async()=>{
 const server=spawn('python3',['-u','-c',"from http.server import ThreadingHTTPServer; from render_server import Handler; s=ThreadingHTTPServer(('127.0.0.1',0),Handler); print(s.server_port,flush=True); s.serve_forever()"],{cwd:root,stdio:['ignore','pipe','ignore']});let browser;
 try{
  const port=await new Promise((resolve,reject)=>{server.stdout.once('data',d=>resolve(Number(String(d).trim())));server.once('error',reject);server.once('exit',c=>reject(Error('server exited '+c)))});
  browser=await chromium.launch();const page=await browser.newPage();const base='http://127.0.0.1:'+port;
  let validSession=true,updateStatus=200;const writes=[];
  await page.route('https://yhzdqrqzjruduohypvqf.supabase.co/**',route=>{
   const req=route.request(),u=new URL(req.url());
   if(req.method()!=='GET')writes.push({path:u.pathname,query:u.search,method:req.method(),body:req.postDataJSON()});
   if(u.pathname==='/auth/v1/user'&&req.method()==='GET')return route.fulfill(validSession?{json:{id:'fixture-user',email:'fixture@example.com'}}:{status:401,json:{error:'expired'}});
   if(u.pathname==='/auth/v1/user'&&req.method()==='PUT')return route.fulfill({status:updateStatus,json:updateStatus===200?{id:'fixture-user'}:{error:'insufficient_aal'}});
   if(u.pathname==='/rest/v1/user_roles')return route.fulfill({json:[{role:'customer'}]});
   if(u.pathname.endsWith('/my_broker_access'))return route.fulfill({json:{entitlement:{plan_id:'free'},preferences:{}}});
   if(u.pathname==='/auth/v1/recover')return route.fulfill({json:{}});
   return route.fulfill({status:400,json:{error:'unexpected_fixture_request'}});
  });
  async function clear(){await page.goto(base+'/progress',{waitUntil:'domcontentloaded'});await page.evaluate(()=>{localStorage.clear();sessionStorage.clear()})}
  for(const width of [390,1280]){
   await clear();writes.length=0;validSession=true;updateStatus=200;await page.setViewportSize({width,height:900});
   await page.goto(base+'/account#type=recovery&access_token=fixture-only-access&refresh_token=fixture-only-refresh');
   await page.locator('#recoveryForm').waitFor({state:'visible'});
   assert.equal(await page.evaluate(()=>location.hash),'');assert.equal(writes.length,0);
   await page.getByLabel('Yeni şifre',{exact:true}).fill('fixture-password-1');
   await page.getByLabel('Yeni şifre tekrar',{exact:true}).fill('fixture-password-2');
   await page.getByRole('button',{name:'Yeni şifreyi kaydet'}).click();await page.getByText('Şifreler eşleşmiyor.',{exact:true}).waitFor();assert.equal(writes.length,0);
   await page.getByLabel('Yeni şifre tekrar',{exact:true}).fill('fixture-password-1');
   await page.getByRole('button',{name:'Yeni şifreyi kaydet'}).click();await page.getByText('Yeni şifreniz kaydedildi.',{exact:true}).waitFor();
   assert.equal(writes.filter(x=>x.method==='PUT').length,1);assert.equal(await page.locator('#newPassword').inputValue(),'');
   assert.equal(await page.evaluate(()=>sessionStorage.getItem('gb_password_recovery_pending')),null);
   assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
   console.log('PASSWORD_RECOVERY_UI_PASS',width);
  }
  await clear();writes.length=0;
  await page.goto(base+'/account#error=access_denied&error_code=otp_expired');await page.getByText('Bağlantı geçersiz veya süresi dolmuş. Yeni bir şifre sıfırlama bağlantısı isteyin.',{exact:true}).waitFor();
  assert.equal(writes.length,0);assert.equal(await page.evaluate(()=>location.hash),'');assert.equal(await page.locator('#recoveryForm').isVisible(),false);
  await clear();validSession=false;
  await page.goto(base+'/account#type=recovery&access_token=fixture-expired&refresh_token=fixture-refresh');await page.getByText('Şifre yenileme oturumu doğrulanamadı. Yeni bağlantı isteyin.',{exact:true}).waitFor();
  assert.equal(await page.evaluate(()=>localStorage.getItem('gb_access_token')),null);assert.equal(writes.filter(x=>x.method==='PUT').length,0);
  await clear();validSession=true;updateStatus=403;writes.length=0;
  await page.goto(base+'/account#type=recovery&access_token=fixture-only-access&refresh_token=fixture-only-refresh');await page.locator('#recoveryForm').waitFor({state:'visible'});
  await page.locator('#newPassword').fill('fixture-password-1');await page.locator('#confirmPassword').fill('fixture-password-1');await page.getByRole('button',{name:'Yeni şifreyi kaydet'}).click();
  await page.getByText(/Güvenlik doğrulaması gerekli/).waitFor();assert.equal(await page.evaluate(()=>sessionStorage.getItem('gb_password_recovery_pending')),'1');
  assert.equal(await page.getByText('Yeni şifreniz kaydedildi.',{exact:true}).count(),0);
  await clear();writes.length=0;await page.goto(base+'/account');await page.getByLabel('E-posta',{exact:true}).fill('fixture@example.com');await page.getByRole('button',{name:'Şifre sıfırla',exact:true}).click();
  await page.getByText(/Şifre yenileme bağlantısı istenmiştir/).waitFor();const recovery=writes.find(x=>x.path==='/auth/v1/recover');assert.ok(recovery);assert.equal(new URLSearchParams(recovery.query).get('redirect_to'),'https://global-broker-opal.vercel.app/account');
  console.log('PASSWORD_RECOVERY_NEGATIVE_AND_REDIRECT_PASS');
 }finally{if(browser)await browser.close();server.kill()}
})().catch(e=>{console.error(e.message);process.exitCode=1});
