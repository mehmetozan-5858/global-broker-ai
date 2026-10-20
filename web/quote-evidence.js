(function(){'use strict';
function validateQuote(quote,today){
 var errors={},positive=/^[0-9]{1,12}(\.[0-9]{1,6})?$/;
 function date(value){return /^\d{4}-\d{2}-\d{2}$/.test(value)&&value>='0001-01-01'&&Number.isFinite(Date.parse(value+'T00:00:00Z'))&&new Date(value+'T00:00:00Z').toISOString().slice(0,10)===value}
 ['counterparty','reference','price_unit'].forEach(function(name){if(!String(quote[name]||'').trim())errors[name]='Bu alanı doldurun.'});
 ['amount','quantity'].forEach(function(name){var value=String(quote[name]||'').trim();if(!positive.test(value)||Number(value)<=0)errors[name]=(name==='amount'?'Birim fiyat':'Miktar')+' sıfırdan büyük olmalı; en fazla 12 tam ve 6 ondalık basamak kullanın. Ondalık ayırıcı noktadır.'});
 if(!/^[A-Za-z]{3}$/.test(String(quote.currency||'').trim()))errors.currency='Üç harfli para birimi kodunu yazın (ör. USD, EUR, TRY).';
 if(!date(quote.quote_date))errors.quote_date='Geçerli bir teklif tarihi seçin.';
 else if(quote.quote_date>today)errors.quote_date='Teklif tarihi gelecekte olamaz.';
 if(!date(quote.valid_until))errors.valid_until='Geçerli bir son geçerlilik tarihi seçin.';
 else if(!errors.quote_date&&quote.valid_until<quote.quote_date)errors.valid_until='Geçerlilik sonu teklif tarihinden önce olamaz.';
 var source=String(quote.source_url||'').trim();
 try{var url=new URL(source);if(!/^https:\/\/[A-Za-z0-9.-]+(:[0-9]{1,5})?(\/|$)/.test(source)||/\s/.test(source)||url.username||url.password)throw Error('url')}
 catch(e){errors.source_url='Kullanıcı adı veya parola içermeyen tam bir https:// belge bağlantısı yazın.'}
 return errors;
}
 if(typeof module==='object'&&module.exports)module.exports={validateQuote:validateQuote};
 if(typeof document==='undefined')return;
var base='https://yhzdqrqzjruduohypvqf.supabase.co/rest/v1/rpc/',key='sb_publishable_fFtN0JmDBp8TP01lKJhTFQ_sx6mkt-w';
var form=document.getElementById('quoteForm'),status=document.getElementById('status'),button=document.getElementById('save'),requestId=null,busy=false;
function message(s){status.textContent=s}
async function rpc(name,args){var token=localStorage.getItem('gb_access_token')||'';if(!token)throw Error('auth');var response=await fetch(base+name,{method:'POST',headers:{apikey:key,Authorization:'Bearer '+token,'Content-Type':'application/json'},body:JSON.stringify(args||{}),cache:'no-store'});if(response.status===401||response.status===403)throw Error('auth');if(!response.ok)throw Error('request');return response.json()}
function render(data){var select=document.getElementById('opportunity'),selected=select.value;select.replaceChildren();var empty=document.createElement('option');empty.value='';empty.textContent='Fırsatı seçin';select.appendChild(empty);(data.opportunities||[]).forEach(function(row){var opt=document.createElement('option');opt.value=row.id;opt.textContent=String(row.title||row.id).slice(0,180);select.appendChild(opt)});select.value=selected;var list=document.getElementById('quotes');list.replaceChildren();(data.quotes||[]).forEach(function(row){var q=row.quote||{},card=document.createElement('article'),title=document.createElement('strong');title.textContent=q.counterparty||'Teklif';card.appendChild(title);[q.reference, (q.party==='supplier'?'Alış':'Satış')+' · '+q.amount+' '+q.currency+' / '+q.price_unit,'Miktar: '+q.quantity,'Teklif: '+q.quote_date+' · Geçerlilik: '+q.valid_until,'Fırsat: '+row.opportunity_id,'Kaynak: '+q.source_url,'Durum: İnceleme bekliyor'].forEach(function(value){var p=document.createElement('p');p.textContent=value;card.appendChild(p)});list.appendChild(card)});if(!(data.quotes||[]).length)list.textContent='Henüz teklif kanıtı kaydedilmedi.';form.hidden=false;document.getElementById('inbox').hidden=false}
function failure(error){if(error.message==='auth'){form.hidden=true;document.getElementById('inbox').hidden=true;document.getElementById('quotes').replaceChildren();document.getElementById('signin').hidden=false;message('Yönetici oturumu ve MFA doğrulaması gerekiyor.')}else message('İşlem tamamlanamadı. Alanları ve bağlantınızı kontrol edip yeniden deneyin.')}
function clearValidation(){Array.from(form.elements).forEach(function(e){if(e.setCustomValidity)e.setCustomValidity('')})}
function edited(){if(!busy){requestId=null;clearValidation()}}
form.addEventListener('input',edited);form.addEventListener('change',edited);
form.addEventListener('submit',async function(event){event.preventDefault();if(busy)return;clearValidation();var fields=Array.from(form.elements).filter(function(e){return e.name}),quote={};fields.forEach(function(e){quote[e.name]=e.value.trim()});var today=new Date().toISOString().slice(0,10),errors=validateQuote(quote,today);form.elements.namedItem('quote_date').max=today;Object.keys(errors).forEach(function(name){form.elements.namedItem(name).setCustomValidity(errors[name])});if(!form.reportValidity()){var first=Array.from(form.elements).find(function(e){return e.validity&&!e.validity.valid});message('Kaydedilmedi: '+(first?first.validationMessage:'Alanları kontrol edin.'));return}busy=true;button.disabled=true;fields.forEach(function(e){e.disabled=true});document.getElementById('opportunity').disabled=true;quote.currency=quote.currency.toUpperCase();var opportunity=document.getElementById('opportunity').value;
try{if(!requestId)requestId=crypto.randomUUID();var saved=await rpc('gb_submit_quote_evidence',{p_request_id:requestId,p_opportunity_id:opportunity,p_quote:quote});if(saved.status!=='pending_review')throw Error('request');message('Kaydedildi. İnceleme bekliyor; fiyat veya marj onayı verilmedi.');requestId=null;form.reset();try{render(await rpc('gb_quote_evidence_workspace'))}catch(error){if(error.message==='auth')failure(error);else message('Kayıt saklandı; liste yenilenemedi. Sayfayı yenileyebilirsiniz.')}}catch(error){failure(error)}finally{busy=false;button.disabled=false;fields.forEach(function(e){e.disabled=false});document.getElementById('opportunity').disabled=false}});
rpc('gb_quote_evidence_workspace').then(function(data){render(data);message('Yönetici erişimi doğrulandı. Girilen teklifler inceleme bekler.')}).catch(failure);
})();
