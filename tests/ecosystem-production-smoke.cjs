/* Read-only production acceptance: never send a lead, message or payment. */
const assert=require('node:assert/strict');
const {chromium}=require('playwright');
const contract=require('../web/ecosystem-contract.js');
const broker='https://global-broker-ai-visibility2.vercel.app';
(async()=>{
 const browser=await chromium.launch({headless:true});
 try{
  for(const width of [390,1280]){
   const context=await browser.newContext({viewport:{width,height:900}}),page=await context.newPage();
   const writes=[];
   await context.route('**/*',route=>{
    const req=route.request();
    if(!['GET','HEAD','OPTIONS'].includes(req.method())){writes.push(req.url());return route.abort();}
    return route.continue();
   });
   const data={businessName:'Global Broker QA',website:'https://example.com/',country:'Türkiye',sector:'B2B / Sanayi'};
   await page.goto(broker+'/',{waitUntil:'domcontentloaded'});
   if(width===390)await page.getByRole('button',{name:'Menüyü aç'}).click();
   await page.getByRole('link',{name:'AI Visibility Ekosistemi'}).click();
   await page.getByRole('heading',{name:'Ticaret fırsatından dijital görünürlüğe'}).waitFor();
   assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
   for(const key of ['businessName','website','country'])await page.locator('[name='+key+']').fill(data[key]);
   await page.locator('[name=sector]').selectOption(data.sector);
   await page.getByRole('button',{name:'Bilgilerimle AI Visibility’ye geç'}).click();
   const incoming=page.getByRole('region',{name:'Global Broker firma bilgileri'});
   await incoming.waitFor();
   assert.equal(await page.getByLabel('İşletme adı',{exact:true}).inputValue(),'');
   await page.getByRole('button',{name:'Bu firma bilgilerini kullan'}).click();
   assert.equal(await page.getByLabel('İşletme adı',{exact:true}).inputValue(),data.businessName);
   assert.equal(await page.getByLabel('Web sitesi',{exact:true}).inputValue(),data.website);
   assert.equal(await page.locator('form select').nth(1).inputValue(),data.sector);
   await page.getByRole('button',{name:'Global Broker’a geç'}).click();
   await page.getByRole('button',{name:'Bilgileri forma al'}).click();
   for(const key of ['businessName','website','country'])assert.equal(await page.locator('[name='+key+']').inputValue(),data[key]);
   assert.equal(await page.locator('[name=sector]').inputValue(),data.sector);
   assert.equal(page.url().includes('#business='),false);
   // Every page transition must remain read-only. No generated profile is submitted.
   assert.equal(writes.filter(url=>/\/api\/(leads|payment|private_room|introduction|contact_unlock)/.test(url)).length,0);
   await page.goto(broker+'/customer',{waitUntil:'domcontentloaded'});
   await page.frameLocator('#portal').getByRole('link',{name:'AI Visibility Ekosistemi'}).click();
   await page.getByRole('heading',{name:'Ticaret fırsatından dijital görünürlüğe'}).waitFor();
   await page.goto(broker+'/web/app.html',{waitUntil:'domcontentloaded'});
   await page.getByRole('link',{name:'AI Visibility Ekosistemi'}).click();
   await page.getByRole('heading',{name:'Ticaret fırsatından dijital görünürlüğe'}).waitFor();
   console.log('PRODUCTION_ECOSYSTEM_PASS width='+width+' profile_roundtrip=reviewed external_writes=blocked');
   await context.close();
  }
 }finally{await browser.close();}
})().catch(error=>{console.error(error.message);process.exitCode=1;});
