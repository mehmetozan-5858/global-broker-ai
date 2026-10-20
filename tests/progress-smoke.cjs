const {chromium}=require('playwright');
const {spawn}=require('node:child_process');
const path=require('node:path');
const root=path.resolve(__dirname,'..');
(async()=>{
 const server=spawn('python3',['-u','-c',"from http.server import ThreadingHTTPServer; from render_server import Handler; s=ThreadingHTTPServer(('127.0.0.1',0),Handler); print(s.server_port,flush=True); s.serve_forever()"],{cwd:root,stdio:['ignore','pipe','ignore']});
 let browser;
 try{
  const port=await new Promise((resolve,reject)=>{server.stdout.once('data',d=>resolve(Number(String(d).trim())));server.once('error',reject);server.once('exit',c=>reject(Error('server exited '+c)))});
  browser=await chromium.launch();const page=await browser.newPage();
  for(const width of [390,1280]){
   await page.setViewportSize({width,height:900});await page.goto('http://127.0.0.1:'+port+'/progress');
   await page.getByText('%77',{exact:true}).waitFor();await page.getByText('%72',{exact:true}).waitFor();
   await page.getByText(/Yol haritasındaki yazılım adımları: [0-9]+ \/ 13 tamamlandı/).waitFor();await page.getByText('Gerçek veri / kullanım kabulü: 0 / 6 tamamlandı',{exact:true}).waitFor();
   if(await page.locator('#packages details').count()!==8)throw Error('missing packages');
   await page.getByLabel('Göster').selectOption('complete');
   if(await page.locator('#packages details').count()!==2)throw Error('complete count');
   await page.getByLabel('Göster').selectOption('open');
   if(await page.locator('#packages details').count()!==6)throw Error('open count');
   await page.locator('#packages summary').first().click();
   if(!await page.locator('#packages details').first().evaluate(e=>e.open))throw Error('acceptance not expanded');
   if(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth))throw Error('overflow '+width);
   console.log('PROGRESS_UI_PASS',width);
  }
  await page.route('**/delivery-progress.json',r=>r.fulfill({status:503,json:{error:'progress_unavailable'}}));
  await page.getByRole('button',{name:'Durumu yenile'}).click();await page.getByText('Güncel ilerleme kaydı alınamadı. Yenile düğmesiyle tekrar deneyin.',{exact:true}).waitFor();
  if(await page.locator('#stepProgress').isVisible())throw Error('stale step counts displayed');
  if(await page.locator('.percent').count())throw Error('stale percentage displayed as current');
  console.log('PROGRESS_OUTAGE_FAIL_CLOSED_PASS');
 }finally{if(browser)await browser.close();server.kill()}
})().catch(e=>{console.error(e.message);process.exitCode=1});
