const {test}=require('node:test');
const assert=require('node:assert/strict');
const {assess}=require('../web/evidence-readiness.js');
const now=new Date('2026-10-20T10:00:00Z');
function complete(){return {data_completion:{core_complete:true},deadline_normalized:'2026-11-30',buyer_verification:{status:'verified'},specification_analysis:{supplier_sourcing_ready:true},supplier_research:{candidate_suppliers:[{verified:true,financial_evidence_eligible:true,exact_spec_match_verified:true}]},price_margin_gate:{price_ready:true,margin_ready:true,quote_valid_until:'2026-10-30'},commercial_feasibility:{landed_cost_ready:true},offer_risk_gate:{draft_offer_ready:true,risk_review_required:false,risk_flags:[]}}}
test('coverage, nonempty prices and status strings never authorize readiness',()=>{const r=assess({buyer_verified:true,supplier_status:'verified',workflow:{opportunity_dossier:{completeness_percent:100},pricing_margin:{supplier_quote:99},logistics:{status:'unverified'},risk:{status:'review_pending'}}},now);assert.equal(r.ready,false);assert.equal(r.quote,false);assert.equal(r.logistics,false);assert.equal(r.risk,false)});
test('unselected lots block complete-looking records',()=>{const r=assess({...complete(),ted_lot_selection_required:true},now);assert.equal(r.ready,false);assert.match(r.next,/Kalem/)});
test('expired or unknown deadline blocks readiness',()=>{for(const d of ['2026-10-19',null,'2026-02-30'])assert.equal(assess({...complete(),deadline_normalized:d},now).ready,false)});
test('expired quote is blocked even with a stale true server flag',()=>{const o=complete();o.price_margin_gate.quote_valid_until='2026-10-19';const r=assess(o,now);assert.equal(r.quote,false);assert.equal(r.ready,false);assert.match(r.next,/teklif/)});
test('category verification does not establish exact-spec supplier eligibility',()=>{const o=complete();delete o.supplier_research.candidate_suppliers[0].exact_spec_match_verified;assert.equal(assess(o,now).ready,false)});
test('each missing authoritative gate fails closed',()=>{for(const k of ['data_completion','buyer_verification','specification_analysis','supplier_research','price_margin_gate','commercial_feasibility','offer_risk_gate']){const o=complete();delete o[k];assert.equal(assess(o,now).ready,false,k)}});
test('risk flags are blocking even when draft gate passed',()=>{const o=complete();o.offer_risk_gate.risk_flags=['single_verified_supplier'];assert.equal(assess(o,now).ready,false)});
test('complete evidence permits internal review only',()=>{const r=assess(complete(),now);assert.equal(r.ready,true);assert.equal(r.externalActionAuthorized,false);assert.match(r.next,/İnsan/)});
test('historical or unclassified TED notice cannot become a current offer',()=>{for(const context of [undefined,{form_type:'result',call_for_tenders:false,label_tr:'Sonuç ilanı'}]){const r=assess({...complete(),source:'TED',notice_context:context},now);assert.equal(r.ready,false);assert.match(r.next,/Yeni ihale çağrısı/)}assert.equal(assess({...complete(),source:'TED',notice_context:{call_for_tenders:true}},now).ready,true)});

function dossier(row,shared=true,hostId='content'){
 const fs=require('node:fs'),vm=require('node:vm');
 const api=require('../web/evidence-readiness.js');
 let source=fs.readFileSync(require('node:path').join(__dirname,'../web/opportunity-dossier.js'),'utf8');
 source=source.replace(/\nload\(\);\n\}\)\(\);\s*$/, '\nwindow.testDossier={render:render,statusClass:statusClass,cardMatch:cardMatch,setRows:function(rows){ROWS=rows}};\n})();');
 const window={scrollTo(){}};if(shared)window.GBEvidenceReadiness=api;
 vm.runInNewContext(source,{window,URL,Date});
 const host={id:hostId,innerHTML:'',querySelector:()=>null};
 window.testDossier.render(row,host,null,()=>{},hostId==='content');
 return {html:host.innerHTML,api:window.testDossier};
}
function priced(){const r=complete();r.deadline_normalized='2099-12-31';r.price_margin_gate.quote_valid_until='2099-12-31';r.workflow={pricing_margin:{supplier_quote:11111,sell_price:22222,gross_margin:33333,commission:44444},logistics:{status:'unverified'},risk:{status:'review_pending'}};return r;}
test('detail dossier does not promote legacy statuses or display unsupported amounts',()=>{const r={buyer_verified:true,supplier_status:'verified',workflow:priced().workflow};const {html}=dossier(r);assert(!html.includes('Hazır inceleme'));assert(!html.includes('Ticari veri güçlü'));for(const value of ['11111','22222','33333','44444'])assert(!html.includes(value));assert.match(html,/Geçerli gerçek teklif bekleniyor/)});
test('detail dossier hides expired quote and derived amounts despite stale gates',()=>{const r=priced();r.price_margin_gate.quote_valid_until='2020-01-01';const {html}=dossier(r);for(const value of ['11111','22222','33333','44444'])assert(!html.includes(value));assert(!html.includes('İnsan incelemesine hazır'))});
test('detail dossier allows evidence-backed internal review without trade authority',()=>{const {html}=dossier(priced());assert.match(html,/İnsan incelemesine hazır/);for(const value of ['11111','22222','33333','44444'])assert(html.includes(value));assert.match(html,/İnsan onayı zorunlu/)});
test('detail dossier fails closed when shared evidence module is absent',()=>{const {html}=dossier(priced(),false);assert.match(html,/Kanıt doğrulaması bekleniyor/);assert(!html.includes('11111'))});
test('negative status names cannot produce a positive detail badge',()=>{const {api}=dossier({});for(const value of ['unverified','not_verified','expired','invalid','review_pending'])assert.notEqual(api.statusClass(value),'good');assert.equal(api.statusClass('verified'),'good')});
test('admin dossier links only a stable opportunity ID to private quote intake',()=>{
 const {html}=dossier({id:'gb_fixture:lot-1',title_tr:'Fixture'});assert.match(html,/quote-evidence\?opportunity=gb_fixture%3Alot-1/);assert.match(html,/target="_top">Bu fırsata teklif kaydet/);
 for(const id of [undefined,'','https://evil.invalid','a" onclick="bad'])assert.ok(!dossier({id}).html.includes('quote-evidence?'));
 assert.ok(!dossier({id:'gb_fixture'},true,'pc').html.includes('quote-evidence?'));
});
test('admin opportunity cards use stable IDs, never titles or public introduction IDs',()=>{
 const fs=require('node:fs'),vm=require('node:vm');const source=fs.readFileSync(require('node:path').join(__dirname,'../web/app.html'),'utf8');
 const context={encodeURIComponent};vm.createContext(context);vm.runInContext(source.match(/^function quoteAction\(o\).*$/m)[0],context);
 assert.match(context.quoteAction({id:'gb_fixture',title_tr:'Other title'}),/opportunity=gb_fixture/);
 assert.equal(context.quoteAction({opportunity_id:'public-request-id'}),'');assert.equal(context.quoteAction({id:'bad" onclick="alert(1)'}),'');
});

test('duplicate opportunity titles cannot change a stable card identity',()=>{const {api}=dossier({});const a={id:'gb_a',title_tr:'Same title'},b={id:'gb_b',title_tr:'Same title'};api.setRows([a,b]);const card=id=>({dataset:{opportunityId:id},querySelector:()=>({textContent:'Same title'}),textContent:'Same title'});assert.equal(api.cardMatch(card('gb_b')).row,b);assert.equal(api.cardMatch(card('gb_b')).trusted,true);assert.equal(api.cardMatch(card('gb_missing')).row,undefined)});
test('financial projection hides expired, missing and unselected-lot evidence',()=>{
 const {financials}=require('../web/evidence-readiness.js');
 for(const row of [{workflow:priced().workflow},{...priced(),ted_lot_selection_required:true},{...priced(),price_margin_gate:{price_ready:true,margin_ready:true,quote_valid_until:'2020-01-01'}}])assert.ok(Object.values(financials(row)).every(v=>v===null));
 const row=priced();row.price_margin_gate.margin_ready=false;assert.deepEqual(financials(row),{supplier_quote:11111,sell_price:null,gross_margin:null,commission:null});
});
test('financial projection rejects malformed amounts while retaining real losses and zero commission',()=>{
 const {financials}=require('../web/evidence-readiness.js'),row=priced();
 row.workflow.pricing_margin.gross_margin=-33;row.workflow.pricing_margin.commission=0;assert.equal(financials(row).gross_margin,-33);assert.equal(financials(row).commission,0);
 for(const value of [true,{},[],NaN,Infinity,'NaN','1e9','12,34','',-1,0]){row.workflow.pricing_margin.supplier_quote=value;assert.ok(Object.values(financials(row)).every(v=>v===null),String(value));}
 row.workflow.pricing_margin.supplier_quote='11111.00';row.workflow.pricing_margin.sell_price=null;assert.equal(financials(row).supplier_quote,'11111.00');assert.equal(financials(row).commission,null);
});
function financialSurface(file,row,shared=true){
 const fs=require('node:fs'),vm=require('node:vm'),path=require('node:path'),nodes={};
 const html=fs.readFileSync(path.join(__dirname,'../web/'+file),'utf8');let code=html.match(/<script>\s*([\s\S]*?)<\/script>/)[1];
 const window={};if(shared)window.GBEvidenceReadiness=require('../web/evidence-readiness.js');
 const context={window,URL,Date,document:{getElementById:id=>nodes[id]||(nodes[id]={innerHTML:'',style:{}})}};
 if(file==='app.html')code=code.replace(/E\('q'\)\.addEventListener[\s\S]*$/,'');
 else code=code.replace('renderCards();load();','window.testRows=function(rows){DATA={opportunities:rows}};');
 vm.createContext(context);vm.runInContext(code,context);if(file==='index.html')window.testRows([row]);
 return key=>{if(file==='app.html')return context.specificCard(key,row);window.openCard(key,key);return nodes.pc.innerHTML};
}
test('web and app pricing, commission and payment views hide unsupported financial values',()=>{
 for(const file of ['app.html','index.html'])for(const row of [{workflow:priced().workflow}, {...priced(),price_margin_gate:{price_ready:true,margin_ready:true,quote_valid_until:'2020-01-01'}}]){
  const view=financialSurface(file,row);for(const key of ['pricing','commission','payments'])for(const value of ['11111','22222','33333','44444'])assert.ok(!view(key).includes(value),file+': '+key+': '+value);
 }
});
test('web and app show evidence-backed values, keep losses visible and fail closed without the shared module',()=>{
 for(const file of ['app.html','index.html']){
  const row=priced();row.workflow.pricing_margin.gross_margin=-33333;const view=financialSurface(file,row);for(const value of ['11111','22222','-33333','44444'])assert.ok(view('pricing').includes(value));
  assert.ok(view('payments').includes('-33333'));assert.ok(view('commission').includes('44444'));
  const missing=financialSurface(file,row,false);for(const key of ['pricing','commission','payments'])for(const value of ['11111','22222','33333','44444'])assert.ok(!missing(key).includes(value));
 }
});

test('source-table scope blocks complete-looking evidence without a TED flag',()=>{const r=assess({...complete(),source_lot_selection_required:true},now);assert.equal(r.ready,false);assert.equal(r.lotSelection,true);assert.match(r.next,/Kalem/)});
test('source line items remain separated and escaped in the admin dossier',()=>{const r=priced();r.source_lot_selection_required=true;r.source_line_items=[{lot_id:'1',lot_label:'North',product:'Cable <script>bad()</script>',quantity:'27840',unit:'m',destination:'Mzuzu'},{lot_id:'2',lot_label:'Central',product:'Copper cable',quantity:'63075',unit:'m',destination:'Lilongwe'}];const {html}=dossier(r);assert.match(html,/27840 m/);assert.match(html,/63075 m/);assert.match(html,/Mzuzu/);assert.match(html,/Lilongwe/);assert(!html.includes('<script>bad()'));assert(!html.includes('İnsan incelemesine hazır'));assert(!html.includes('11111'))});
