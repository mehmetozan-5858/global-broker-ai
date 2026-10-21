const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
function render(comparison){
 const context={URL,baseCard:()=>'',esc:v=>String(v).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))};
 vm.createContext(context);vm.runInContext(fs.readFileSync('web/tender-dossier.js','utf8'),context);
 return context.baseCard({technical_comparison:comparison});
}
function sample(){return {lot_selection_required:true,scopes:[{scope:'LOTTO 1',models:[{manufacturer:'Manufacturer',model:'Model',clause_results:[
 {field:'length_mm',expected:{min:7000,max:8000},status:'source_supported',requirement_source_url:'https://example.test/spec.pdf',catalog_evidence:[{source_url:'https://example.test/model'}]},
 {field:'fuel',expected:'CNG',status:'configuration_confirmation_required'},
 {field:'emission',expected:'EURO6_STEP_E',status:'missing_evidence'}
]}]}]};}
test('partial comparison distinguishes source support from approval and keeps lot review',()=>{
 const html=render(sample());for(const text of ['Otomatik teknik ön karşılaştırma','Kapsam kısmi','Lot seçimi incelemesi açık','7–8 m','tam onay değil','konfigürasyonu teyit','Belge / teyit bekleniyor','İhale kanıtı','Üretici kanıtı'])assert.ok(html.includes(text),text);
});
test('comparison escapes model values and rejects unsafe source URLs',()=>{
 const s=sample();s.scopes[0].models[0].model='<img src=x onerror=alert(1)>';
 s.scopes[0].models[0].clause_results[0].requirement_source_url='javascript:alert(1)';
 s.scopes[0].models[0].clause_results[0].catalog_evidence[0].source_url='https://user:secret@example.test';
 const html=render(s);assert.ok(!html.includes('<img'));assert.ok(!html.includes('javascript:'));assert.ok(!html.includes('user:secret'));assert.ok(html.includes('&lt;img'));
});
test('no structured comparison does not fabricate a model result',()=>{
 assert.ok(!render({status:'requirements_not_structured',scopes:[]}).includes('Otomatik teknik ön karşılaştırma'));
});
test('new product family shows minimum source requirement with no borrowed model approval',()=>{
 const html=render({scopes:[{scope:'LOT 2 / Truck <x>',status:'manufacturer_research_required',requirements:[{field:'tank_capacity_l',expected:{min:4000},source_url:'https://example.test/notice'}],models:[]}]});
 for(const text of ['Truck &lt;x&gt;','En az 4000 litre','üretici kanıtı araştırılmalı','karşılaştırma yapılmadı','İhale kanıtı'])assert.ok(html.includes(text),text);
 assert.ok(!html.includes('Kaynakta destekleniyor'));
});
