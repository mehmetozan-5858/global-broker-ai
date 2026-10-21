/* Evidence-first tender dossier: show sourced terms, never invent requirements. */
(function(){
  'use strict';
  if(typeof baseCard!=='function'||typeof esc!=='function')return;
  var previous=baseCard;
  function value(o,keys){
    for(var i=0;i<keys.length;i++){
      var v=o&&o[keys[i]];
      if(v!==null&&v!==undefined&&String(v).trim()!=='')return clean(v);
    }
    return '';
  }
  function clean(v){
    if(Array.isArray(v)){
      var vals=v.map(function(x){return String(x||'').trim()}).filter(Boolean);
      return vals.filter(function(x,i){return vals.indexOf(x)===i}).join(', ');
    }
    if(v&&typeof v==='object')return String(v.text||v.value||'');
    var t=String(v||'').trim();
    var parts=t.split(',').map(function(x){return x.trim()}).filter(Boolean);
    if(parts.length>1&&parts.every(function(x){return /^\\d{4}-\\d{2}-\\d{2}(?:[T+].*)?$/.test(x)})){
      return parts.filter(function(x,i){return parts.indexOf(x)===i}).join(', ');
    }
    return t;
  }
  function isKnown(v){return !!(v&&String(v).trim()&&!/[\\u3400-\\u9fff]/.test(String(v)))}
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
  function technicalComparison(result){
    if(!result||!Array.isArray(result.scopes)||!result.scopes.length)return '';
    var labels={length_mm:'Uzunluk',passenger_capacity:'Toplam yolcu',vehicle_class:'Araç sınıfı',emission:'Emisyon',fuel:'Yakıt'};
    var states={source_supported:'Kaynakta destekleniyor; tam onay değil',conflict:'Koşulla çelişiyor',configuration_confirmation_required:'Teklif konfigürasyonu teyit edilmeli',catalog_unavailable:'Üretici kaynağı okunamadı',conflicting_catalog_evidence:'Üretici belgelerinde çelişki var'};
    function source(url,label){
      try{var u=new URL(url);if(u.protocol!=='https:'||u.username||u.password)return '';
        return ' <a target="_blank" rel="noopener noreferrer" href="'+esc(u.href)+'">'+esc(label)+'</a>';
      }catch(e){return ''}
    }
    function expected(c){
      var v=c.expected;
      if(c.field==='length_mm'&&v&&typeof v==='object'&&Number.isFinite(v.min)&&Number.isFinite(v.max))return (v.min/1000)+'–'+(v.max/1000)+' m';
      return {M3_CLASS_I:'M3 / Sınıf I',EURO6_STEP_E:'Euro 6 Step E',CNG:'CNG'}[v]||String(v===undefined?'':v).slice(0,80);
    }
    var html='<details class="section"><summary><b>Otomatik teknik ön karşılaştırma</b></summary><div class="note">Kapsam kısmi; diğer zorunlu maddeler ve üretici onayı bekleniyor.</div>';
    if(result.lot_selection_required===true)html+='<div class="note">Lot seçimi incelemesi açık; farklı lotların sonuçları birleştirilmez.</div>';
    result.scopes.slice(0,4).forEach(function(scope){
      if(!scope||typeof scope!=='object')return;
      html+='<div class="label">'+esc(String(scope.scope||'İnceleme kapsamı'))+'</div>';
      (Array.isArray(scope.models)?scope.models:[]).slice(0,3).forEach(function(model){
        if(!model||typeof model!=='object')return;
        html+='<div class="section"><b>'+esc(String(model.manufacturer||''))+' — '+esc(String(model.model||''))+'</b><ul>';
        (Array.isArray(model.clause_results)?model.clause_results:[]).slice(0,10).forEach(function(c){
          if(!c||typeof c!=='object')return;
          html+='<li>'+esc(labels[c.field]||'Şartname maddesi')+': '+esc(expected(c))+' · '+esc(states[c.status]||'Belge / teyit bekleniyor');
          html+=source(c.requirement_source_url,'İhale kanıtı');
          var facts=Array.isArray(c.catalog_evidence)?c.catalog_evidence:[];
          if(facts[0])html+=source(facts[0].source_url,'Üretici kanıtı');
          html+='</li>';
        });
        html+='</ul></div>';
      });
    });
    return html+'</details>';
  }
  function dossier(o){
    var spec=o&&o.specification_analysis||{};
    var extraction=o&&o.document_extraction||{};
    var eligibility=spec.eligibility_evidence||[];
    var tech=spec.technical_evidence||[];
    var docs=spec.documents||[];
    var docLinks=Array.isArray(docs)?docs.filter(function(x){return typeof x==='string'&&/^https:\/\//.test(x)}):[];
    var src=value(o,['source_url','official_url','notice_url','url']);
    var parsed=extraction.status==='parsed'||Number(extraction.parsed_count||0)>0;
    var status=parsed?'Kaynak veya ek belge metni okundu':'Kaynak/şartname okuma doğrulanamadı';
    var blocked=!eligibility.length||!tech.length||!value(o,['submission_deadline_date','deadline-receipt-tender-date-lot','deadline']);
    var fields=[['Teklif son tarihi',value(o,['submission_deadline_date','deadline-receipt-tender-date-lot','deadline'])],['Teknik özellikler',tech.length?'kanıt var':''],['Katılım şartları',eligibility.length?'kanıt var':''],['İstenen belgeler',value(o,['required_documents','documents_required','submission_documents'])],['Teklif teminatı',value(o,['bid_bond','bid_security','tender_guarantee'])],['Ödeme koşulları',value(o,['payment_terms','payment_conditions'])],['Teslim şartları',value(o,['delivery_terms','incoterms'])]];
    var missing=fields.filter(function(x){return !isKnown(x[1])}).map(function(x){return x[0]});
    var html='<details class="opp"><summary><b>İhale şartları, belgeler ve katılım kontrolü</b></summary>';
    html+='<div class="note">'+esc(status)+' · '+(blocked?'Katılım kararı için eksik bilgi var':'Katılım şartları ayrıca teyit edilmeli')+'</div>';
    html+='<div class="section"><div class="label">Dosya kontrolü</div><div class="value">'+(fields.length-missing.length)+' / '+fields.length+' temel alan için bilgi veya kaynak bulgusu mevcut. Bu oran belge doğrulaması değildir.</div></div>';
    if(missing.length)html+='<div class="section"><div class="label">Eksik / teyit bekleyen alanlar</div><div class="value">'+esc(missing.join(' · '))+'</div></div>';
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
    html+=technicalComparison(o&&o.technical_comparison);
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
