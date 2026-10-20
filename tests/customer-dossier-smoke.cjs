/* Fixture-only customer review; browser requests never reach external services. */
const {chromium,webkit}=require('playwright');
const {execFileSync}=require('node:child_process');
const fs=require('node:fs');
const path=require('node:path');
const root=path.resolve(__dirname,'..');
const fixtures=JSON.parse(execFileSync('python3',['-c',`
import json
from src.public_opportunity_projection import project_public_opportunity as project
rows=[]
for identity,source,changes in [('scope','WORLD_BANK',{'source_lot_selection_required':True}),('result','TED',{'form-type':'result','ted_lot_count':2,'ted_lot_selection_required':True}),('pending','WORLD_BANK',{})]:
 r={'id':'fixture-'+identity,'product_name':'Fixture '+identity,'source':source,'country_code':'DE','country_name':'Germany','quantity':'999 units','export_goods_review':{'status':'goods_candidate'},'data_completion':{'missing_fields':['quantity_or_budget','deadline','PRIVATE-MISSING-NOTE']},'buyer_name':'PRIVATE-BUYER','document_extracted_text':'PRIVATE-DOCUMENT fixture@example.invalid','document_extraction':{'parsed_count':0 if identity=='pending' else 1,'attempts':[{'status':'parsed','format':'world_bank_notice_json'}] if identity=='scope' else []}}
 r.update(changes)
 rows.append(project(project(r)))
print(json.dumps(rows))
`],{cwd:root,encoding:'utf8'}));
(async()=>{
 const expected=fs.readFileSync(path.join(root,'web/customer-portal.js'),'utf8');
 const base=process.env.GB_CUSTOMER_BASE||'https://broker.aivisibilityworks.com';
 let deployed='';
 for(let i=0;i<18;i++){
  const response=await fetch(base+'/web/customer-portal.js?customerDossierQA='+Date.now());
  if(response.ok){deployed=await response.text();if(deployed===expected)break;}
  await new Promise(r=>setTimeout(r,5000));
 }
 if(deployed!==expected)throw Error('reviewed customer portal asset not deployed');
 for(const [name,engine,widths] of [['chromium',chromium,[320,390,1280]],['webkit',webkit,[390]]]){
  const browser=await engine.launch();
  try{
   const page=await browser.newPage();
   await page.addInitScript(()=>localStorage.setItem('gb_access_token','synthetic-fixture-only'));
   await page.route('**/*',route=>{
    const url=route.request().url();
    if(url.includes('/rpc/my_broker_access'))return route.fulfill({json:{entitlement:{all_sectors:true,plan_id:'fixture'},preferences:{}}});
    if(url.includes('/rpc/my_introduction_requests'))return route.fulfill({json:[]});
    if(url.includes('/data/latest-opportunities.json'))return route.fulfill({json:{opportunities:fixtures}});
    if(route.request().method()!=='GET')throw Error('unexpected write request');
    return route.fulfill({contentType:'text/html',body:'<html lang="tr"><meta name="viewport" content="width=device-width,initial-scale=1"><body style="margin:0;background:#061725;color:white;font-family:system-ui"><div><section id="cards"></section></div></body></html>'});
   });
   for(const width of widths){
    await page.setViewportSize({width,height:900});await page.goto('https://fixture.invalid/');
    await page.addScriptTag({content:deployed});
    await page.getByRole('heading',{name:'Fixture scope',exact:true}).waitFor();
    await page.getByText('Ayrıntılı resmî ilan metni okundu',{exact:true}).waitFor();
    await page.getByText('Kaynak okuması doğrulanamadı',{exact:true}).waitFor();
    await page.getByText('Alım kalemi kapsamı inceleme bekliyor; toplam miktar ve bütçe doğrulanmadı',{exact:true}).waitFor();
    if(!await page.getByRole('button',{name:'Araştırma kaydı',exact:true}).isDisabled())throw Error('result notice request enabled');
    const text=await page.locator('body').innerText();
    for(const privateText of ['PRIVATE-BUYER','PRIVATE-DOCUMENT','PRIVATE-MISSING-NOTE','fixture@example','0 ayrı kalem'])if(text.includes(privateText))throw Error('unsafe or invented customer text');
    if((await page.locator('.cp-card').filter({has:page.getByRole('heading',{name:'Fixture scope',exact:true})}).innerText()).includes('999 units'))throw Error('scope quantity leaked');
    if(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth))throw Error('horizontal overflow '+name+' '+width);
    console.log('CUSTOMER_DOSSIER_UI_PASS',name,width);
   }
  }finally{await browser.close()}
 }
})().catch(error=>{console.error(error.message);process.exitCode=1});
