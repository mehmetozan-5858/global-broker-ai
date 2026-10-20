/* UI regression using real researched capabilities, with every request intercepted. */
const {chromium}=require('playwright');
const {execFileSync}=require('node:child_process');
const path=require('node:path');
const root=path.resolve(__dirname,'..');
const fixture=JSON.parse(execFileSync('python3',['-c',`
import json
from src.enrichment import enrich_opportunity
from src.supplier_research import prepare
from src.public_opportunity_projection import project_public_opportunity
# Synthetic result-notice context exercises the research-only customer label.
r={'source':'TED','form-type':'result','publication-number':'681487-2026','opportunity_id':'existing-identity','title_original':'Denmark – Machines and apparatus for testing and measuring – One Photonic Wafer Probe Station and one Photonic Assembly Station','title_tr':'Makine / ekipman alımı','product_name':'Makine / ekipman alımı','specification_analysis':{'supplier_sourcing_ready':True},'export_goods_review':{'status':'goods_candidate'}}
enrich_opportunity(r)
prepare(r)
print(json.dumps({'admin':r,'public':project_public_opportunity(r)}))
`],{cwd:root,encoding:'utf8'}));
(async()=>{
 const browser=await chromium.launch();
 try{
  const page=await browser.newPage();
  await page.addInitScript(()=>localStorage.setItem('gb_access_token','synthetic-fixture-only'));
  await page.route('**/*',r=>{const u=r.request().url();if(u.includes('/rpc/my_broker_access'))return r.fulfill({json:{entitlement:{all_sectors:true,plan_id:'fixture'},preferences:{}}});if(u.includes('/rpc/my_introduction_requests'))return r.fulfill({json:[]});if(u.includes('/data/latest-opportunities.json'))return r.fulfill({json:{opportunities:[fixture.public]}});return r.fulfill({contentType:'text/html',body:'<html lang="tr"><meta name="viewport" content="width=device-width,initial-scale=1"><body style="margin:0"><div><section id="cards"></section></div></body></html>'});});
  for(const width of [390,1280]){
   await page.setViewportSize({width,height:900});await page.goto('https://fixture.invalid/');
   await page.addScriptTag({path:path.join(root,'web/customer-portal.js')});
   await page.getByRole('heading',{name:fixture.public.product_detail,exact:true}).waitFor();
   await page.getByText('Sonuç ilanı — yeni alım çağrısı değil',{exact:true}).first().waitFor();
   if(!await page.getByRole('button',{name:'Araştırma kaydı',exact:true}).isDisabled())throw Error('historical notice introduction enabled');
   await page.getByText('2 üreticinin ürün kabiliyeti kaynakla eşleşti; tam şartname ve teklif onayı bekleniyor',{exact:true}).waitFor();
   if((await page.locator('body').innerText()).includes('FormFactor'))throw Error('supplier identity in public projection');
   await page.goto('https://fixture.invalid/');
   await page.evaluate(row=>{window.__GB_OPPORTUNITY_ROWS=[row];document.body.innerHTML='<div id="content"><article class="opp"><h3></h3></article></div>';document.querySelector('h3').textContent=row.title_tr;},fixture.admin);
   await page.addScriptTag({path:path.join(root,'web/opportunity-dossier.js')});
   await page.getByRole('button',{name:'Dosyayı aç →'}).click();
   await page.locator('.gbd-state').getByText('Tam şartname onayı bekleniyor',{exact:true}).waitFor();
   await page.getByText('FormFactor, Inc.',{exact:true}).waitFor();
   await page.getByText('ficonTEC Service GmbH',{exact:true}).waitFor();
   if(await page.getByRole('link',{name:'Üretici kaynağı',exact:true}).count()!==5)throw Error('missing requirement source links');
   await page.getByText(/RF up to 40 GHz/).waitFor();
   if(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth))throw Error('overflow '+width);
   console.log('SUPPLIER_CAPABILITY_UI_PASS',width);
  }
 }finally{await browser.close()}
})().catch(e=>{console.error(e.message);process.exitCode=1});
