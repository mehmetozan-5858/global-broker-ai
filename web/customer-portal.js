(function(){
"use strict";

var SB_URL='https://yhzdqrqzjruduohypvqf.supabase.co';
var SB_KEY='sb_publishable_fFtN0JmDBp8TP01lKJhTFQ_sx6mkt-w';
var accessState=null;
var requestState={};

function token(){try{return localStorage.getItem('gb_access_token')||''}catch(e){return ''}}
async function rpc(name,body){var t=token();if(!t)return null;try{var r=await fetch(SB_URL+'/rest/v1/rpc/'+name,{method:'POST',headers:{apikey:SB_KEY,Authorization:'Bearer '+t,'Content-Type':'application/json'},body:JSON.stringify(body||{}),cache:'no-store'});if(!r.ok)return null;return await r.json()}catch(e){return null}}
async function loadAccess(){return rpc('my_broker_access',{})}
async function loadRequests(){var rows=await rpc('my_introduction_requests',{});requestState={};(Array.isArray(rows)?rows:[]).forEach(function(r){if(r&&r.opportunity_id)requestState[r.opportunity_id]=r});return requestState}

function txt(v){return v==null?'':String(v).trim()}
function safe(v,fallback){var s=txt(v);return s||fallback}
function product(o){return safe(o.product_name,'Ürün bilgisi kaynakta henüz netleşmedi')}
function country(o){return safe(o.country||o.country_code,'Ülke bilgisi kaynakta henüz netleşmedi')}
function quantity(o){return safe(o.approx_quantity,'Miktar kaynakta belirtilmemiş')}
function deadline(o){return safe(o.deadline,'Son tarih kaynakta belirtilmemiş')}
function delivery(o){return safe(o.delivery_term,'Teslim / Incoterm bilgisi belirtilmemiş')}
function source(o){return safe(o.source_name||o.source_type,'Kaynak kategorisi belirtilmemiş')}
function opportunityType(o){return safe(o.opportunity_type,'Fırsat türü belirtilmemiş')}
function verification(o){return safe(o.verification_category,'Doğrulama kategorisi belirtilmemiş')}
function isGoods(o){return !!(o&&o.goods_status==='goods_candidate')}
function coverage(o){var n=Number(o&&o.source_backed_fields||0);return isFinite(n)&&n>=0?n:0}
function coverageTotal(o){var n=Number(o&&o.source_field_total||0);return isFinite(n)&&n>0?n:6}
function pricing(){return window.GlobalBrokerPricing||null}
function sectorOf(o){return String(o&&o.sector_id||'other')}
function countryCodeOf(o){return String(o&&o.country_code||'').toUpperCase()}
function entitlement(){return accessState&&accessState.entitlement||{plan_id:'free',sector_limit:1,country_limit:3,contact_credits_remaining:0,all_sectors:false}}
function preferences(){return accessState&&accessState.preferences||{selected_sectors:[],selected_countries:[]}}
function allowedByPlan(o){var e=entitlement(),p=preferences(),sec=sectorOf(o),cc=countryCodeOf(o);if(!e.all_sectors){if(!(p.selected_sectors||[]).length)return false;if((p.selected_sectors||[]).indexOf(sec)<0)return false}if((p.selected_countries||[]).length){if(!cc||(p.selected_countries||[]).indexOf(cc)<0)return false}return true}
function maskedBuyer(){return 'Alıcı kimliği kontrollü tanıştırma ile paylaşılır'}
function statusLabel(s){return {requested:'Talep alındı',verifying:'Doğrulanıyor',buyer_consent_pending:'Alıcı onayı bekleniyor',approved:'Onaylandı',introduced:'Tanıştırıldı',declined:'Uygun bulunmadı · kredi iade edildi',expired:'Süre doldu · kredi iade edildi',refunded:'Kredi iade edildi'}[s]||'Tanıştırma talebi'}
function activeRequest(o){return o&&o.opportunity_id?requestState[o.opportunity_id]:null}
function option(select,value,label){var el=document.createElement('option');el.value=value;el.textContent=label||value;select.appendChild(el)}
function field(parent,label,value,missing){var row=document.createElement('div');row.className='cp-fact';var k=document.createElement('span');k.className='cp-key';k.textContent=label;var v=document.createElement('strong');v.textContent=value;if(missing)v.className='cp-missing';row.appendChild(k);row.appendChild(v);parent.appendChild(row)}
function unique(rows,fn){var seen={},list=[];rows.forEach(function(o){var v=fn(o);if(v&&!seen[v]){seen[v]=true;list.push(v)}});return list.sort(function(a,b){return a.localeCompare(b,'tr')})}

async function requestIntroduction(o,button,box){
  var t=token();if(!t){box.textContent='Önce hesabınıza giriş yapın.';return}
  if(!o.opportunity_id){box.textContent='Bu fırsat için güvenli tanıştırma kimliği henüz hazır değil.';return}
  button.disabled=true;button.textContent='Talep gönderiliyor…';box.textContent='';
  try{
    var r=await fetch('/api/introduction',{method:'POST',headers:{Authorization:'Bearer '+t,'Content-Type':'application/json'},body:JSON.stringify({opportunity_id:o.opportunity_id}),cache:'no-store'});
    var data=await r.json().catch(function(){return {}});
    if(!r.ok){
      var messages={INTRODUCTION_CREDIT_REQUIRED:'Tanıştırma Krediniz kalmadı. Paketinizi yükseltebilirsiniz.',OPPORTUNITY_NOT_FOUND:'Fırsat doğrulama kuyruğunda. Kredi düşülmedi.',SECTOR_NOT_IN_PLAN:'Bu fırsat mevcut sektör paketinizin dışında.',COUNTRY_NOT_SELECTED:'Bu fırsat seçili ülke kapsamınızın dışında.',AUTHENTICATION_REQUIRED:'Oturumunuzu yenileyin.'};
      box.textContent=messages[data.status]||'Tanıştırma talebi şu anda oluşturulamadı.';
      button.disabled=false;button.textContent='Tanıştırma talebi gönder (1 kredi)';return;
    }
    requestState[o.opportunity_id]={request_id:data.request_id,opportunity_id:o.opportunity_id,status:data.request_status||'requested'};
    if(accessState&&accessState.entitlement)accessState.entitlement.contact_credits_remaining=data.credits_remaining;
    var credit=document.getElementById('cpCredits');if(credit)credit.textContent=data.credits_remaining==null?'Sınırsız':String(data.credits_remaining);
    box.className='cp-intro-status';box.textContent=data.already_requested?'Mevcut talep: '+statusLabel(data.request_status):'Tanıştırma talebiniz alındı. Alıcı ve erişim yolu doğrulanacak; uygun değilse kredi iade edilecek.';
    button.textContent=statusLabel(data.request_status||'requested');button.disabled=true;
  }catch(e){box.textContent='Bağlantı hatası nedeniyle tanıştırma talebi gönderilemedi.';button.disabled=false;button.textContent='Tanıştırma talebi gönder (1 kredi)'}
}

function mount(rows){
  rows=(rows||[]).filter(isGoods).filter(allowedByPlan);
  var cards=document.getElementById('cards');if(!cards)return;
  var old=document.getElementById('customerSearch');if(old)old.remove();
  var e=entitlement(),p=preferences(),policy=pricing();
  var selectedNames=(p.selected_sectors||[]).map(function(id){return policy&&policy.sectorClusters&&policy.sectorClusters[id]?policy.sectorClusters[id].name:id}).join(', ');
  var panel=document.createElement('section');panel.id='customerSearch';panel.className='cp-panel';
  panel.innerHTML='<div class="cp-head"><div><small>MÜŞTERİ FIRSAT PORTALI · '+String(e.plan_id||'free').toUpperCase()+'</small><h2>Sektörünüze uygun doğrulanabilir ticaret fırsatları</h2><p>'+(selectedNames?'Aktif sektörler: '+selectedNames+'. ':'Henüz sektör seçmediniz. Hesabım ekranından sektör kümenizi seçin. ')+'Bu ekranda yalnız müşteri için güvenli alanlar gösterilir. Alıcı kimliği ve iletişim bilgileri Tanıştırma Kredisi sonrasında kontrollü doğrulama süreciyle paylaşılır.</p></div><div class="cp-count" id="cpCount">0 fırsat</div></div><div class="cp-access"><span>Kalan Tanıştırma Kredisi: <b id="cpCredits">'+String(e.contact_credits_remaining==null?'Sınırsız':e.contact_credits_remaining)+'</b></span><a href="/account">Sektör / paket ayarları →</a></div><div class="cp-help"><b>Nasıl kullanılır?</b> Ürün ve ülke filtrelerini daraltın, karttaki kaynak kapsamını kontrol edin ve uygun fırsatta “Tanıştırma talebi gönder” düğmesini kullanın. Eksik alanlar tahmin edilmez; “belirtilmemiş” olarak gösterilir.</div><div class="cp-filters"><label>Ürün ara<input id="cpQuery" type="search" placeholder="Örn. pompa, mobilya, laboratuvar..." autocomplete="off"></label><label>Ülke<select id="cpCountry"><option value="">Tüm seçili ülkeler</option></select></label><label>Kaynak kapsamı<select id="cpQuality"><option value="0">Tümü</option><option value="2">En az 2 alan</option><option value="4">En az 4 alan</option><option value="6">6 alan</option></select></label></div><div id="cpResults" class="cp-results"></div>';
  cards.parentNode.insertBefore(panel,cards);
  var countrySel=document.getElementById('cpCountry'),qualitySel=document.getElementById('cpQuality'),query=document.getElementById('cpQuery'),results=document.getElementById('cpResults'),count=document.getElementById('cpCount');
  unique(rows,country).filter(function(v){return v.indexOf('henüz netleşmedi')<0}).forEach(function(v){option(countrySel,v)});
  function render(){
    var q=query.value.trim().toLocaleLowerCase('tr'),c=countrySel.value,minCoverage=Number(qualitySel.value||0);
    var filtered=rows.filter(function(o){var hay=(product(o)+' '+country(o)+' '+source(o)).toLocaleLowerCase('tr');return (!q||hay.indexOf(q)>=0)&&(!c||country(o)===c)&&coverage(o)>=minCoverage}).sort(function(a,b){var d=coverage(b)-coverage(a);return d||product(a).localeCompare(product(b),'tr')});
    count.textContent=filtered.length+' fırsat';results.textContent='';
    if(!filtered.length){var empty=document.createElement('div');empty.className='cp-empty';if(!(p.selected_sectors||[]).length)empty.innerHTML='<b>Henüz sektör seçmediniz.</b><br>Hesabım ekranından sektör kümenizi seçtiğinizde uygun fırsatlar burada görünür.';else empty.innerHTML='<b>Bu filtrelerle eşleşen fırsat yok.</b><br>Ürün aramasını temizleyin, ülke filtresini genişletin veya daha sonra yeniden kontrol edin.';results.appendChild(empty);return}
    filtered.slice(0,100).forEach(function(o){
      var card=document.createElement('article');card.className='cp-card';
      var top=document.createElement('div');top.className='cp-card-top';var title=document.createElement('h3');title.textContent=product(o);top.appendChild(title);var badge=document.createElement('span');badge.className='cp-badge';badge.textContent=(policy&&policy.sectorClusters&&policy.sectorClusters[sectorOf(o)]?policy.sectorClusters[sectorOf(o)].name:'Fiziksel ürün');top.appendChild(badge);card.appendChild(top);
      var facts=document.createElement('div');facts.className='cp-facts';field(facts,'Alıcı',maskedBuyer(),true);field(facts,'Ülke',country(o),!o.country&&!o.country_code);field(facts,'Yaklaşık miktar',quantity(o),!o.approx_quantity);field(facts,'Son tarih',deadline(o),!o.deadline);field(facts,'Teslim / Incoterm',delivery(o),!o.delivery_term);field(facts,'Fırsat türü',opportunityType(o),!o.opportunity_type);field(facts,'Kaynak',source(o),!o.source_name&&!o.source_type);field(facts,'Doğrulama',verification(o),!o.verification_category);card.appendChild(facts);
      var foot=document.createElement('div');foot.className='cp-foot';var cov=document.createElement('span');cov.textContent='Kaynak destekli alan: '+coverage(o)+'/'+coverageTotal(o);foot.appendChild(cov);
      var button=document.createElement('button');button.className='cp-unlock';var credits=entitlement().contact_credits_remaining,req=activeRequest(o);var status=document.createElement('div');status.className='cp-contact-msg';
      if(req&&['requested','verifying','buyer_consent_pending','approved','introduced'].indexOf(req.status)>=0){button.textContent=statusLabel(req.status);button.disabled=true;status.textContent=statusLabel(req.status)}
      else if(credits===0){button.textContent='Paket yükselt';button.onclick=function(){window.top.location.href='/pricing'}}
      else{button.textContent='Tanıştırma talebi gönder (1 kredi)';button.onclick=function(){requestIntroduction(o,button,status)}}
      foot.appendChild(button);card.appendChild(foot);card.appendChild(status);results.appendChild(card);
    });
  }
  [query,countrySel,qualitySel].forEach(function(el){el.addEventListener(el===query?'input':'change',render)});render();
}

function style(){var css=document.createElement('style');css.textContent='.cp-panel{margin:12px 14px 26px;padding:22px;border:1px solid #24465d;border-radius:18px;background:linear-gradient(145deg,#0c2b3e,#0a2030);box-shadow:0 16px 40px #0003}.cp-head{display:flex;justify-content:space-between;gap:18px;align-items:flex-start}.cp-head small{color:#f3bd67;letter-spacing:.12em;font-weight:800}.cp-head h2{margin:5px 0 6px;font-size:25px}.cp-head p{margin:0;color:#b8c9d4;max-width:760px;line-height:1.45}.cp-count{background:#173d55;border:1px solid #38627b;border-radius:999px;padding:8px 12px;font-weight:800;white-space:nowrap}.cp-access{display:flex;justify-content:space-between;gap:12px;align-items:center;margin:15px 0 0;padding:10px 12px;border-radius:10px;background:#102f43;color:#bcd0db;font-size:12px}.cp-access a{color:#8bc8ff;text-decoration:none}.cp-help{margin:10px 0 0;padding:11px 12px;border-radius:10px;border:1px solid #34576c;background:#0b2435;color:#b8c9d4;font-size:12px;line-height:1.5}.cp-help b{color:#fff}.cp-filters{display:grid;grid-template-columns:2fr 1fr 1fr;gap:10px;margin:18px 0}.cp-filters label{font-size:11px;color:#b8c9d4;font-weight:700}.cp-filters input,.cp-filters select{width:100%;margin-top:6px;padding:12px;border-radius:10px;border:1px solid #3b6077;background:#071b29;color:#fff;font:inherit}.cp-results{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:11px;max-height:720px;overflow:auto}.cp-card{border:1px solid #2e5268;background:#0a2234;border-radius:14px;padding:15px}.cp-card-top{display:flex;justify-content:space-between;gap:10px;align-items:flex-start}.cp-card h3{margin:0;font-size:16px;line-height:1.35}.cp-badge{font-size:10px;padding:5px 8px;border-radius:999px;background:#154938;color:#aef0c9;white-space:nowrap}.cp-facts{display:grid;grid-template-columns:1fr 1fr;gap:7px 12px;margin-top:13px}.cp-key{display:block;color:#8fa8b8;font-size:10px}.cp-fact strong{display:block;font-size:12px;line-height:1.4;overflow-wrap:anywhere}.cp-missing{color:#f5c877}.cp-foot{border-top:1px solid #26475c;margin-top:12px;padding-top:10px;display:flex;justify-content:space-between;align-items:center;gap:10px;font-size:11px;color:#9fb4c1}.cp-unlock{border:1px solid #d2a24d;background:#d2a24d;color:#071827;border-radius:9px;padding:8px 10px;font-weight:850;cursor:pointer}.cp-unlock:disabled{opacity:.65;cursor:default}.cp-contact-msg,.cp-intro-status{margin-top:9px;color:#efc675;font-size:11px;line-height:1.45}.cp-intro-status{padding:10px;background:#0b2a24;border:1px solid #285e4d;border-radius:9px;color:#aee7c6}.cp-empty{grid-column:1/-1;padding:20px;border:1px dashed #3b6077;border-radius:12px;color:#b8c9d4;line-height:1.55}.cp-empty b{color:#fff}@media(max-width:820px){.cp-filters{grid-template-columns:1fr 1fr}}@media(max-width:700px){.cp-panel{margin-left:8px;margin-right:8px;padding:16px}.cp-head{display:block}.cp-count{display:inline-block;margin-top:12px}.cp-access{align-items:flex-start;flex-direction:column}.cp-filters{grid-template-columns:1fr}.cp-results{grid-template-columns:1fr;max-height:none}.cp-facts{grid-template-columns:1fr 1fr}}';document.head.appendChild(css)}

async function boot(){style();accessState=await loadAccess();await loadRequests();fetch('/data/latest-opportunities.json?t='+Date.now(),{cache:'no-store'}).then(function(r){if(!r.ok)throw new Error('feed');return r.json()}).then(function(d){mount(d.opportunities||[])}).catch(function(){mount([])})}
boot();
})();