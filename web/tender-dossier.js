/* Evidence-first tender dossier: show sourced terms, never invent requirements. */
(function(){
  'use strict';
  if(typeof baseCard!=='function'||typeof esc!=='function')return;
  var previous=baseCard;
  function value(o,keys){
    for(var i=0;i<keys.length;i++){
      var v=o&&o[keys[i]];
      if(v!==null&&v!==undefined&&String(v).trim()!=='')return String(v);
    }
    return '';
  }
  function readable(v){
    return v&&!/[\u3400-\u9fff]/.test(v)?v:'';
  }
  function row(label,v){
    return '<div class="section"><div class="label">'+esc(label)+'</div><div class="value">'+esc(readable(v)||'Kaynakta doğrulanamadı / Türkçe inceleme bekliyor')+'</div></div>';
  }
  function evidence(items){
    if(!Array.isArray(items)||!items.length)return '';
    return items.slice(0,5).map(function(x){
      var t=typeof x==='string'?x:(x&&typeof x==='object'?(x.text||x.excerpt||x.value||''):'');
      t=readable(String(t)).slice(0,450);
      return t?'<li>'+esc(t)+'</li>':'';
    }).join('');
  }
  function block(label,items){
    var html=evidence(items);
    return '<div class="section"><div class="label">'+esc(label)+'</div><div class="value">'+(html?'<ul>'+html+'</ul>':'Kaynakta doğrulanamadı / Türkçe inceleme bekliyor')+'</div></div>';
  }
  function dossier(o){
    var spec=o&&o.specification_analysis||{};
    var extraction=o&&o.document_extraction||{};
    var eligibility=spec.eligibility_evidence||[];
    var tech=spec.technical_evidence||[];
    var docs=spec.documents||[];
    var docLinks=Array.isArray(docs)?docs.filter(function(x){return typeof x==='string'&&/^https:\/\//.test(x)}):[];
    var src=value(o,['source_url','official_url','notice_url','url']);
    var status=extraction.status==='parsed'?'Kaynak veya ek belge metni okundu':'Kaynak/şartname okuma doğrulanamadı';
    var blocked=!eligibility.length||!tech.length||!value(o,['submission_deadline_date','deadline-receipt-tender-date-lot','deadline']);
    var html='<details class="opp"><summary><b>İhale şartları, belgeler ve katılım kontrolü</b></summary>';
    html+='<div class="note">'+esc(status)+' · '+(blocked?'Katılım kararı için eksik bilgi var':'Katılım şartları ayrıca teyit edilmeli')+'</div>';
    html+=row('Tam olarak ne alınıyor?',value(o,['product_name','product','technical-specification','technical_specification']));
    html+=row('Teklif son tarihi',value(o,['submission_deadline_date','deadline-receipt-tender-date-lot','deadline']));
    html+=row('İhale dokümanı temin son tarihi',value(o,['document_purchase_deadline','document_deadline']));
    html+=row('Teslim şekli / Incoterms',value(o,['delivery_terms','incoterms']));
    html+=row('Teklif teminatı',value(o,['bid_bond','bid_security','tender_guarantee']));
    html+=row('Ödeme koşulları',value(o,['payment_terms','payment_conditions']));
    html+=block('Teknik özelliklere ilişkin kaynak bulguları',tech);
    html+=block('Katılım / yeterlilik şartlarına ilişkin kaynak bulguları',eligibility);
    html+=block('Miktar / adet kanıtları',spec.quantity_evidence);
    html+=block('Teslim şartlarına ilişkin kaynak bulguları',spec.delivery_evidence);
    html+=block('Değerlendirme / ihale kriterleri',spec.award_evidence);
    html+=row('İstenen belge listesi',value(o,['required_documents','documents_required','submission_documents']));
    html+='<div class="section"><div class="label">Kaynak ve ek belgeler</div><div class="value">';
    if(src&&/^https?:\/\//.test(src))html+='<a target="_blank" rel="noopener noreferrer" href="'+esc(src)+'">İlan kaynağını aç</a> ';
    docLinks.slice(0,3).forEach(function(url){html+='<a target="_blank" rel="noopener noreferrer" href="'+esc(url)+'">Ek belge</a> '});
    if(!src&&!docLinks.length)html+='Bağlantı doğrulanamadı';
    html+='</div></div><div class="note">Kaynakta açıkça bulunmayan şartlar tahmin edilmez. Kaynak metninin bulunması, alıcının veya teklif uygunluğunun doğrulandığı anlamına gelmez.</div></details>';
    return html;
  }
  baseCard=function(o){return previous(o)+dossier(o)};
})();
