(function(){
"use strict";

var SB_URL='https://yhzdqrqzjruduohypvqf.supabase.co';
var SB_KEY='sb_publishable_fFtN0JmDBp8TP01lKJhTFQ_sx6mkt-w';
var accessState=null;
function token(){try{return localStorage.getItem('gb_access_token')||''}catch(e){return ''}}
async function loadAccess(){var t=token();if(!t)return null;try{var r=await fetch(SB_URL+'/rest/v1/rpc/my_broker_access',{method:'POST',headers:{apikey:SB_KEY,Authorization:'Bearer '+t,'Content-Type':'application/json'},body:'{}',cache:'no-store'});if(!r.ok)return null;return await r.json()}catch(e){return null}}

function txt(v){if(v==null)return '';if(Array.isArray(v))return v.map(txt).filter(Boolean).join(', ');if(typeof v==='object')return Object.keys(v).map(function(k){return txt(v[k])}).filter(Boolean).join(' ');return String(v).trim()}
function pick(o,keys){for(var i=0;i<keys.length;i++){var v=txt(o[keys[i]]);if(v)return v}return ''}
function evidence(o,key){var ev=(o.field_evidence||{})[key]||{};return {value:txt(ev.value),status:ev.status==='source_backed'?'source_backed':'missing'}}
function country(o){return evidence(o,'country').value||pick(o,['buyer-country','country_name','project_ctry_name','country','country_code'])||'Ülke belirtilmemiş'}
function city(o){return evidence(o,'city').value||pick(o,['place-of-performance-city-lot','place_of_performance_city','buyer_city','delivery_city','city','project_city'])||'Şehir belirtilmemiş'}
function product(o){return evidence(o,'product').value||pick(o,['product_name','product','title_tr','title_original','bid_description','notice-title','title'])||'Ürün adı belirtilmemiş'}
function quantity(o){return evidence(o,'quantity').value||pick(o,['quantity-lot','quantity','requested_quantity','qty'])||'Miktar belirtilmemiş'}
function deadline(o){return evidence(o,'deadline').value||pick(o,['deadline-receipt-tender-date-lot','responseDeadLine','deadline_date','submission_deadline_date','deadline','closing_date'])||'Son tarih belirtilmemiş'}
function source(o){return pick(o,['source','source_name'])||'Kaynak belirtilmemiş'}
function isGoods(o){return !!(o.export_goods_review&&o.export_goods_review.status==='goods_candidate')}
function coverage(o){var c=o.core_field_coverage||{},n=Number(c.verified_or_source_backed||0);return isFinite(n)?n:0}
function pricing(){return window.GlobalBrokerPricing||null}
function sectorOf(o){var p=pricing();return p&&p.inferSector?p.inferSector(o):String(o.sector_id||'')}
function countryCodeOf(o){var p=pricing();return p&&p.opportunityCountryCode?p.opportunityCountryCode(o):String(o.country_code||o.buyer_country_code||'').toUpperCase()}
function entitlement(){return accessState&&accessState.entitlement||{plan_id:'free',sector_limit:1,country_limit:3,contact_credits_remaining:0,all_sectors:false}}
function preferences(){return accessState&&accessState.preferences||{selected_sectors:[],selected_countries:[]}}
function allowedByPlan(o){var e=entitlement(),p=preferences(),sec=sectorOf(o),cc=countryCodeOf(o);if(!e.all_sectors){if(!(p.selected_sectors||[]).length)return false;if(!sec||(p.selected_sectors||[]).indexOf(sec)<0)return false}if((p.selected_countries||[]).length&&cc&&(p.selected_countries||[]).indexOf(cc)<0)return false;return true}
function maskedBuyer(){return '🔒 Doğrulanmış alıcı — kontak kredisi ile açılır'}

function option(select,value,label){var el=document.createElement('option');el.value=value;el.textContent=label||value;select.appendChild(el)}
function field(parent,label,value,missing){var row=document.createElement('div');row.className='cp-fact';var k=document.createElement('span');k.className='cp-key';k.textContent=label;var v=document.createElement('strong');v.textContent=value;if(missing)v.className='cp-missing';row.appendChild(k);row.appendChild(v);parent.appendChild(row)}
function unique(rows,fn){var seen={},list=[];rows.forEach(function(o){var v=fn(o);if(v&&!seen[v]){seen[v]=true;list.push(v)}});return list.sort(function(a,b){return a.localeCompare(b,'tr')})}
function safeLink(value,type){var a=document.createElement('a');a.target=type==='web'?'_blank':'_self';a.rel='noopener noreferrer';a.textContent=value;if(type==='email')a.href='mailto:'+value;else if(type==='phone')a.href='tel:'+value.replace(/[^+0-9]/g,'');else if(/^https:\/\//i.test(value))a.href=value;else a.removeAttribute('href');return a}

async function unlockContact(o,button,box){
  var t=token();if(!t){box.textContent='Önce hesabınıza giriş yapın.';return}
  if(!o.opportunity_id){box.textContent='Bu fırsat için güvenli erişim kimliği henüz hazır değil.';return}
  button.disabled=true;button.textContent='Kontak açılıyor…';box.textContent='';
  try{
    var r=await fetch('/api/contact_unlock',{method:'POST',headers:{Authorization:'Bearer '+t,'Content-Type':'application/json'},body:JSON.stringify({opportunity_id:o.opportunity_id}),cache:'no-store'});
    var data=await r.json().catch(function(){return {}});
    if(!r.ok){
      var messages={CONTACT_CREDIT_REQUIRED:'Kontak krediniz kalmadı. Paketinizi yükseltebilirsiniz.',CONTACT_NOT_AVAILABLE:'Bu fırsatta doğrulanmış doğrudan kontak henüz bulunmuyor; kredi düşülmedi.',SECTOR_NOT_IN_PLAN:'Bu fırsat mevcut sektör paketinizin dışında.',COUNTRY_NOT_SELECTED:'Bu fırsat seçili ülke kapsamınızın dışında.',INVALID_SESSION:'Oturumunuzu yenileyin.'};
      box.textContent=messages[data.status]||'Kontak şu anda açılamadı. Lütfen daha sonra tekrar deneyin.';
      button.disabled=false;button.textContent='Kontak aç (1 kredi)';return;
    }
    var c=data.contact||{};box.className='cp-contact';
    var rows=[];
    if(c.buyer_name)rows.push(['Firma',c.buyer_name,'text']);
    if(c.contact_person)rows.push(['Yetkili',c.contact_person,'text']);
    if(c.email)rows.push(['E-posta',c.email,'email']);
    if(c.phone)rows.push(['Telefon',c.phone,'phone']);
    if(c.website)rows.push(['Web',c.website,'web']);
    if(c.linkedin)rows.push(['LinkedIn',c.linkedin,'web']);
    if(c.address)rows.push(['Adres',c.address,'text']);
    if(c.source_url)rows.push(['Kaynak ilan',c.source_url,'web']);
    box.textContent='';
    var head=document.createElement('div');head.className='cp-contact-head';head.textContent=data.already_unlocked?'Kontak daha önce açılmıştı — yeniden kredi düşmedi.':'Kontak açıldı — 1 kredi kullanıldı.';box.appendChild(head);
    rows.forEach(function(rw){var line=document.createElement('div');line.className='cp-contact-row';var k=document.createElement('span');k.textContent=rw[0];var v=document.createElement('strong');if(rw[2]==='text')v.textContent=rw[1];else v.appendChild(safeLink(rw[1],rw[2]));line.appendChild(k);line.appendChild(v);box.appendChild(line)});
    if(accessState&&accessState.entitlement)accessState.entitlement.contact_credits_remaining=data.credits_remaining;
    var credit=document.getElementById('cpCredits');if(credit)credit.textContent=data.credits_remaining==null?'Sınırsız':String(data.credits_remaining);
    button.textContent='Kontak açık';button.disabled=true;
  }catch(e){box.textContent='Bağlantı hatası nedeniyle kontak açılamadı.';button.disabled=false;button.textContent='Kontak aç (1 kredi)'}
}

function mount(rows){
  rows=(rows||[]).filter(isGoods).filter(allowedByPlan);
  var cards=document.getElementById('cards');if(!cards)return;
  var old=document.getElementById('customerSearch');if(old)old.remove();
  var e=entitlement(),p=preferences(),policy=pricing();
  var selectedNames=(p.selected_sectors||[]).map(function(id){return policy&&policy.sectorClusters&&policy.sectorClusters[id]?policy.sectorClusters[id].name:id}).join(', ');
  var panel=document.createElement('section');panel.id='customerSearch';panel.className='cp-panel';
  panel.innerHTML='<div class="cp-head"><div><small>MÜŞTERİ FIRSAT PORTALI · '+String(e.plan_id||'free').toUpperCase()+'</small><h2>Sektörünüze uygun fiziksel ürün talepleri</h2><p>'+(selectedNames?'Aktif sektörler: '+selectedNames+'.':'Henüz sektör seçmediniz. Hesabım ekranından sektör kümenizi seçin.')+' Firma adı ve doğrudan kontak verileri kredi kullanılmadan gösterilmez.</p></div><div class="cp-count" id="cpCount">0 fırsat</div></div><div class="cp-access"><span>Kalan kontak kredisi: <b id="cpCredits">'+String(e.contact_credits_remaining==null?'Sınırsız':e.contact_credits_remaining)+'</b></span><a href="/account">Sektör / paket ayarları →</a></div><div class="cp-filters"><label>Ürün ara<input id="cpQuery" type="search" placeholder="Örn. pompa, mobilya, hastane..." autocomplete="off"></label><label>Ülke<select id="cpCountry"><option value="">Tüm seçili ülkeler</option></select></label><label>Şehir<select id="cpCity"><option value="">Tüm şehirler</option></select></label><label>Kaynak kapsamı<select id="cpQuality"><option value="0">Tümü</option><option value="4">En az 4/6 alan</option><option value="5">En az 5/6 alan</option><option value="6">6/6 tam</option></select></label></div><div id="cpResults" class="cp-results"></div>';
  cards.parentNode.insertBefore(panel,cards);
  var countrySel=document.getElementById('cpCountry'),citySel=document.getElementById('cpCity'),qualitySel=document.getElementById('cpQuality'),query=document.getElementById('cpQuery'),results=document.getElementById('cpResults'),count=document.getElementById('cpCount');
  unique(rows,country).forEach(function(v){option(countrySel,v)});unique(rows,city).filter(function(v){return v!=='Şehir belirtilmemiş'}).forEach(function(v){option(citySel,v)});
  function render(){
    var q=query.value.trim().toLocaleLowerCase('tr'),c=countrySel.value,ct=citySel.value,minCoverage=Number(qualitySel.value||0);
    var filtered=rows.filter(function(o){var hay=(product(o)+' '+country(o)+' '+city(o)).toLocaleLowerCase('tr');return (!q||hay.indexOf(q)>=0)&&(!c||country(o)===c)&&(!ct||city(o)===ct)&&coverage(o)>=minCoverage}).sort(function(a,b){var d=coverage(b)-coverage(a);return d||product(a).localeCompare(product(b),'tr')});
    count.textContent=filtered.length+' fırsat';results.textContent='';
    if(!filtered.length){var empty=document.createElement('div');empty.className='cp-empty';empty.textContent=(p.selected_sectors||[]).length?'Seçili sektör ve filtrelere uygun fırsat bulunamadı.':'Önce Hesabım ekranından sektör kümenizi seçin.';results.appendChild(empty);return}
    filtered.slice(0,100).forEach(function(o){
      var card=document.createElement('article');card.className='cp-card';var top=document.createElement('div');top.className='cp-card-top';var title=document.createElement('h3');title.textContent=product(o);top.appendChild(title);var badge=document.createElement('span');badge.className='cp-badge';badge.textContent=(policy&&policy.sectorClusters&&policy.sectorClusters[sectorOf(o)]?policy.sectorClusters[sectorOf(o)].name:'Fiziksel ürün');top.appendChild(badge);card.appendChild(top);
      var facts=document.createElement('div');facts.className='cp-facts';field(facts,'Alıcı',maskedBuyer(),true);field(facts,'Ülke',country(o),evidence(o,'country').status!=='source_backed');field(facts,'Şehir',city(o),evidence(o,'city').status!=='source_backed');field(facts,'Miktar',quantity(o),evidence(o,'quantity').status!=='source_backed');field(facts,'Son tarih',deadline(o),evidence(o,'deadline').status!=='source_backed');field(facts,'Kaynak',source(o),false);card.appendChild(facts);
      var foot=document.createElement('div');foot.className='cp-foot';var cov=document.createElement('span');cov.textContent='Kaynak alanı: '+coverage(o)+'/'+((o.core_field_coverage||{}).total||6);foot.appendChild(cov);
      var button=document.createElement('button');button.className='cp-unlock';var credits=entitlement().contact_credits_remaining;if(credits===0){button.textContent='Paket yükselt';button.onclick=function(){window.top.location.href='/pricing'}}else{button.textContent='Kontak aç (1 kredi)'}foot.appendChild(button);card.appendChild(foot);
      var contact=document.createElement('div');contact.className='cp-contact-msg';card.appendChild(contact);if(credits!==0)button.onclick=function(){unlockContact(o,button,contact)};
      results.appendChild(card);
    });
  }
  [query,countrySel,citySel,qualitySel].forEach(function(el){el.addEventListener(el===query?'input':'change',render)});render();
}

function style(){var css=document.createElement('style');css.textContent='.cp-panel{margin:12px 14px 26px;padding:22px;border:1px solid #24465d;border-radius:18px;background:linear-gradient(145deg,#0c2b3e,#0a2030);box-shadow:0 16px 40px #0003}.cp-head{display:flex;justify-content:space-between;gap:18px;align-items:flex-start}.cp-head small{color:#f3bd67;letter-spacing:.12em;font-weight:800}.cp-head h2{margin:5px 0 6px;font-size:25px}.cp-head p{margin:0;color:#b8c9d4;max-width:680px;line-height:1.45}.cp-count{background:#173d55;border:1px solid #38627b;border-radius:999px;padding:8px 12px;font-weight:800;white-space:nowrap}.cp-access{display:flex;justify-content:space-between;gap:12px;align-items:center;margin:15px 0 0;padding:10px 12px;border-radius:10px;background:#102f43;color:#bcd0db;font-size:12px}.cp-access a{color:#8bc8ff;text-decoration:none}.cp-filters{display:grid;grid-template-columns:2fr 1fr 1fr 1fr;gap:10px;margin:18px 0}.cp-filters label{font-size:11px;color:#b8c9d4;font-weight:700}.cp-filters input,.cp-filters select{width:100%;margin-top:6px;padding:12px;border-radius:10px;border:1px solid #3b6077;background:#071b29;color:#fff;font:inherit}.cp-results{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:11px;max-height:720px;overflow:auto}.cp-card{border:1px solid #2e5268;background:#0a2234;border-radius:14px;padding:15px}.cp-card-top{display:flex;justify-content:space-between;gap:10px;align-items:flex-start}.cp-card h3{margin:0;font-size:16px;line-height:1.35}.cp-badge{font-size:10px;padding:5px 8px;border-radius:999px;background:#154938;color:#aef0c9;white-space:nowrap}.cp-facts{display:grid;grid-template-columns:1fr 1fr;gap:7px 12px;margin-top:13px}.cp-key{display:block;color:#8fa8b8;font-size:10px}.cp-fact strong{display:block;font-size:12px;line-height:1.4;overflow-wrap:anywhere}.cp-missing{color:#f5c877}.cp-foot{border-top:1px solid #26475c;margin-top:12px;padding-top:10px;display:flex;justify-content:space-between;align-items:center;gap:10px;font-size:11px;color:#9fb4c1}.cp-unlock{border:1px solid #d2a24d;background:#d2a24d;color:#071827;border-radius:9px;padding:8px 10px;font-weight:850;cursor:pointer}.cp-unlock:disabled{opacity:.6;cursor:default}.cp-contact-msg{margin-top:9px;color:#efc675;font-size:11px}.cp-contact{margin-top:12px;padding:12px;background:#071b29;border:1px solid #31556d;border-radius:11px}.cp-contact-head{font-size:11px;color:#aee7c6;margin-bottom:8px}.cp-contact-row{display:grid;grid-template-columns:86px 1fr;gap:8px;padding:5px 0;border-top:1px solid #17384d;font-size:12px}.cp-contact-row:first-of-type{border-top:0}.cp-contact-row span{color:#8fa8b8}.cp-contact-row strong,.cp-contact-row a{color:#fff;overflow-wrap:anywhere}.cp-empty{padding:20px;border:1px dashed #3b6077;border-radius:12px;color:#b8c9d4}@media(max-width:820px){.cp-filters{grid-template-columns:1fr 1fr}}@media(max-width:700px){.cp-panel{margin-left:8px;margin-right:8px;padding:16px}.cp-head{display:block}.cp-count{display:inline-block;margin-top:12px}.cp-access{align-items:flex-start;flex-direction:column}.cp-filters{grid-template-columns:1fr}.cp-results{grid-template-columns:1fr;max-height:none}.cp-facts{grid-template-columns:1fr 1fr}}';document.head.appendChild(css)}

async function boot(){style();accessState=await loadAccess();fetch('/data/latest-opportunities.json?t='+Date.now(),{cache:'no-store'}).then(function(r){if(!r.ok)throw new Error('feed');return r.json()}).then(function(d){mount(d.opportunities||[])}).catch(function(){mount([])})}
boot();
})();
