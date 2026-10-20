(function(root){
'use strict';
// Presentation of server evidence gates. File coverage never grants trade authority.
function assess(o,now){
 o=o||{};var core=o.data_completion||{},price=o.price_margin_gate||{},offer=o.offer_risk_gate||{},feasibility=o.commercial_feasibility||{},buyer=o.buyer_verification||{},spec=o.specification_analysis||{};
 var today=(now||new Date()).toISOString().slice(0,10);
 function date(v){return typeof v==='string'&&/^\d{4}-\d{2}-\d{2}$/.test(v)&&!isNaN(Date.parse(v))&&new Date(v).toISOString().slice(0,10)===v?v:null}
 var deadline=date(o.deadline_normalized),expiry=date(price.quote_valid_until);
 var lots=o.ted_lot_selection_required===true;
 var sourceContext=o.source!=="TED"||(o.notice_context||{}).call_for_tenders===true;
 var state={core:core.core_complete===true&&!lots,live:!!deadline&&deadline>=today,buyer:buyer.verified===true||['verified','source_verified'].includes(buyer.status),supplier:(o.supplier_research||{}).candidate_suppliers instanceof Array&&(o.supplier_research.candidate_suppliers).some(function(c){return c.verified===true&&c.financial_evidence_eligible===true&&c.exact_spec_match_verified===true}),quote:price.price_ready===true&&!!expiry&&expiry>=today,margin:price.margin_ready===true,logistics:feasibility.landed_cost_ready===true,risk:offer.draft_offer_ready===true&&offer.risk_review_required===false&&Array.isArray(offer.risk_flags)&&offer.risk_flags.length===0,specification:spec.supplier_sourcing_ready===true,lotSelection:lots,externalActionAuthorized:false};
 state.ready=sourceContext&&state.core&&state.live&&state.buyer&&state.specification&&state.supplier&&state.quote&&state.margin&&state.logistics&&state.risk;
 state.key=!sourceContext?'research':state.ready?'ready':!state.core||!state.live?'missing':state.quote?'strong':'research';
 state.label=!sourceContext?((o.notice_context||{}).label_tr||'İlan türü doğrulanmalı'):state.ready?'İnsan incelemesine hazır':!state.live?'Son tarih doğrulaması gerekli':!state.core?'Eksik dosya':state.quote?'Kaynaklı fiyat mevcut':'Araştırma sürüyor';
 var steps=[[!sourceContext,'Yeni ihale çağrısını araştır; mevcut ilan türünü incele','Source Agent','dosya'],[lots,'Kalem seçimini ve kapsamını doğrula','Specification Agent','dosya'],[!state.core,'Kaynaklı dosyanın eksik alanlarını tamamla','Opportunity Agent','dosya'],[!state.live,'Güncel son tarihi kaynaktan doğrula','Source Agent','dosya'],[!state.buyer,'Alıcı kimliğini bağımsız kaynaktan doğrula','Buyer Agent','buyer'],[!state.specification,'Şartnameyi ve ürün kapsamını doğrula','Specification Agent','dosya'],[!state.supplier,'Tam şartnameye uygun tedarikçiyi doğrula','Supplier Agent','supplier'],[!state.quote,'Geçerli gerçek tedarikçi teklifini tamamla','Price Agent','price'],[!state.margin,'Alıcı fiyatı, para birimi ve miktarı doğrula','Price Agent','price'],[!state.logistics,'Kaynaklı navlun, teslim ve maliyetleri tamamla','Logistics Agent','logistics'],[!state.risk,'Risk ve ticari koşulları incele','Risk Agent','risk']];
 state.task=steps.find(function(s){return s[0]})||[true,'İnsan ticari onayı bekleniyor','CEO / Human Review','human'];state.task=state.task.slice(1);state.next=state.task[0];return state;
}
function financials(o,now){
 var state=assess(o,now),pm=((o||{}).workflow||{}).pricing_margin||{},result={supplier_quote:null,sell_price:null,gross_margin:null,commission:null};
 function amount(value,minimum){
  if(typeof value!=='number'&&typeof value!=='string')return null;
  var text=String(value).trim();if(!text||text.length>80||!/^[-]?\d+(\.\d+)?$/.test(text)||!Number.isFinite(Number(text))||Number(text)<minimum)return null;
  return typeof value==='number'?value:text;
 }
 if(!state.quote||state.lotSelection)return result;
 var buy=amount(pm.supplier_quote,0),sell=amount(pm.sell_price,0);
 if(buy===null||Number(buy)<=0)return result;
 result.supplier_quote=buy;
 if(!state.margin||sell===null||Number(sell)<=0)return result;
 result.sell_price=sell;result.gross_margin=amount(pm.gross_margin,-Infinity);result.commission=amount(pm.commission,0);
 return result;
}
root.GBEvidenceReadiness={assess:assess,financials:financials};
if(typeof module==='object'&&module.exports)module.exports=root.GBEvidenceReadiness;
})(typeof window==='object'?window:globalThis);
