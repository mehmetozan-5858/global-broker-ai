/* Exact deployed RFQ UI; no messages, quotes or payments are sent. */
const {chromium,webkit}=require('playwright'),fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'..'),base=process.env.GB_RFQ_BASE||'https://broker.aivisibilityworks.com';
async function deployed(file){const expected=fs.readFileSync(path.join(root,'web',file),'utf8');for(let i=0;i<18;i++){const response=await fetch(base+'/web/'+file+'?rfqQA='+Date.now());if(response.ok){const text=await response.text();if(text===expected)return text}await new Promise(r=>setTimeout(r,5000))}throw Error('reviewed RFQ asset not deployed: '+file)}
(async()=>{
 const source=await deployed('opportunity-dossier.js'),readiness=await deployed('evidence-readiness.js');
 for(const [name,engine,widths] of [['chromium',chromium,[320,390,1280]],['webkit',webkit,[390]]]){
  const browser=await engine.launch();
  try{
   for(const width of widths){
    const page=await browser.newPage({viewport:{width,height:900}});let writes=0;
    await page.route('**/*',route=>{if(route.request().method()!=='GET'){writes++;return route.abort()}return route.fulfill({contentType:'text/html',body:'<html lang="tr"><meta name="viewport" content="width=device-width,initial-scale=1"><body style="margin:0;color:white;background:#061725;font-family:system-ui"><div id="content"><article class="opp"><h3>Synthetic source table</h3></article></div></body></html>'})});
    await page.goto('https://fixture.invalid/');
    await page.evaluate(()=>{
     const row={id:'OP00000001',title_tr:'Synthetic source table',source:'WORLD_BANK',deadline_normalized:'2099-12-31',buyer_name:'PRIVATE-BUYER',contact_email:'private@example.invalid',source_lot_selection_required:true,document_extraction:{status:'parsed',refresh_policy:'every_scan',checked_at:new Date().toISOString()},source_line_items_evidence:{method:'explicit_notice_table',notice_id:'OP00000001',source_url:'https://search.worldbank.org/api/v2/procnotices?qterm=OP00000001'},source_line_items:[{lot_id:'1',lot_label:'North',product:'10 mm2 copper wire',quantity:'27840',unit:'m',destination:'Mzuzu'},{lot_id:'1',lot_label:'North',product:'95mm aerial cable',quantity:'522000',unit:'m',destination:'Mzuzu'},{lot_id:'2',lot_label:'Central',product:'Copper wire',quantity:'63075',unit:'m',destination:'Lilongwe'}]};
     window.__GB_OPPORTUNITY_ROWS=[row];Object.defineProperty(navigator,'clipboard',{configurable:true,value:{writeText:async text=>{window.__rfqCopied=text}}});
    });
    await page.addScriptTag({content:readiness});await page.addScriptTag({content:source});
    await page.getByRole('button',{name:'Dosyayı aç →',exact:true}).click();
    await page.getByText('İngilizce teklif talebi taslağı',{exact:true}).click();
    await page.getByRole('button',{name:'Taslağı hazırla',exact:true}).click();
    await page.getByText('Aynı ihale grubundan en az bir ürün satırı seçin.',{exact:true}).waitFor();
    const text=page.getByRole('textbox',{name:'İngilizce teklif talebi taslağı'}),inputs=page.locator('.gbd-rfq-row'),copy=page.getByRole('button',{name:'Taslağı kopyala',exact:true});
    await inputs.nth(0).check();await page.getByRole('button',{name:'Taslağı hazırla',exact:true}).click();
    let draft=await text.inputValue();assert.match(draft,/27840 m/);assert.match(draft,/Mzuzu/);
    for(const secret of ['PRIVATE-BUYER','private@example','OP00000001','worldbank.org','63075','522000'])assert(!draft.includes(secret));
    await copy.click();assert.equal(await page.evaluate(()=>window.__rfqCopied),draft);
    await inputs.nth(2).check();assert.equal(await text.inputValue(),'');assert(await copy.isDisabled());
    await page.getByRole('button',{name:'Taslağı hazırla',exact:true}).click();
    await page.getByText('Farklı ihale grupları karıştırılamaz. Tek gruptan ürün seçin.',{exact:true}).waitFor();
    await inputs.nth(2).uncheck();await inputs.nth(1).check();await page.getByRole('button',{name:'Taslağı hazırla',exact:true}).click();
    draft=await text.inputValue();assert.match(draft,/27840 m/);assert.match(draft,/522000 m/);assert(!draft.includes('549840'));
    assert.equal(writes,0);assert(!await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth));
    console.log('RFQ_DRAFT_UI_PASS',name,width);await page.close();
   }
  }finally{await browser.close()}
 }
})().catch(error=>{console.error(error.message);process.exitCode=1});
