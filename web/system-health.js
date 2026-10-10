(function(){
'use strict';
var PAYLOAD=null;
function s(v){return String(v==null?'':v).trim()}
function esc(v){return s(v).replace(/[&<>\"]/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;'}[c]})}
function host(){return document.getElementById('content')||document.getElementById('pc')}
function count(obj,key){return Number((obj||{})[key]||0)}
function labels(o){return Object.keys(o||{}).filter(function(k){return o[k]})}
function pill(text,cls){return '<span class="gbh-pill '+(cls||'')+'">'+esc(text)+'</span>'}
function watchdogHtml(w){
  if(!w||typeof w!=='object')return '<div class="gbh-empty">Watchdog verisi henüz üretilmedi.</div>';
  var c=w.counts||{}, attention=Array.isArray(w.requires_attention)?w.requires_attention:[];
  var top=attention.slice(0,6).map(function(x){return '<li><b>'+esc(x.title||x.opportunity_id||'Fırsat')+'</b><small>'+esc(x.health||'')+' · '+esc(x.next_agent||'')+'</small><span>'+esc(x.reason||'')+'</span></li>'}).join('');
  return '<div class="gbh-metrics">'+pill('Sağlıklı '+count(c,'healthy'),'ok')+pill('Uyarı '+count(c,'warning'),'warn')+pill('Takıldı '+count(c,'stalled'),'bad')+pill('Ölçülemiyor '+count(c,'unobservable'),'muted')+pill('İnsan onayı '+count(c,'human_review'),'human')+'</div>'+
    (top?'<ul class="gbh-attn">'+top+'</ul>':'<div class="gbh-empty">Müdahale listesinde kayıt yok.</div>')+
    '<p class="gbh-note">Watchdog yalnız kanıtlı zaman damgalarıyla “takıldı” der. Zaman damgası yoksa durum “ölçülemiyor” kalır; dış işlem otomatik yeniden başlatılmaz.</p>';
}
function dealHtml(d){
  if(!d||typeof d!=='object')return '<div class="gbh-empty">Deal lifecycle özeti henüz üretilmedi.</div>';
  var states=d.state_counts||{};
  var statePills=Object.keys(states).map(function(k){return pill(k+' '+states[k],k==='commission_settled'?'ok':'')}).join('');
  return '<div class="gbh-metrics">'+pill('Deal dosyası '+Number(d.case_count||0))+pill('Blokeli '+Number(d.blocked_count||0),'warn')+pill('Komisyon tahsil kaydı '+Number(d.settled_count||0),'ok')+'</div>'+
    (statePills?'<div class="gbh-metrics gbh-states">'+statePills+'</div>':'')+
    '<p class="gbh-note">Bir fırsat yalnız açıkça <code>deal_cases</code> kaydına alınırsa yaşam döngüsüne girer. Ödeme, sözleşme, satış ve komisyon durumu kanıt olmadan ilerletilmez.</p>';
}
function launchHtml(r,g){
  var report=r&&typeof r==='object'?r:{}, gate=g&&typeof g==='object'?g:{};
  var blockers=Array.isArray(report.blockers)?report.blockers:(Array.isArray(gate.blockers)?gate.blockers:[]);
  var cats=report.categories||{};
  var catHtml=Object.keys(cats).map(function(k){var x=cats[k]||{};return '<div class="gbh-cat"><b>'+esc(k)+'</b><span>'+Number(x.passed||0)+' / '+Number(x.required||0)+'</span><small>'+(Array.isArray(x.pending)&&x.pending.length?'Bekleyen: '+esc(x.pending.join(', ')):'Hazır')+'</small></div>'}).join('');
  return '<div class="gbh-metrics">'+pill(report.production_launch_ready===true?'Production gate açık':'Shadow Mode','human')+pill('Blokaj '+blockers.length,blockers.length?'warn':'ok')+'</div>'+
    (catHtml?'<div class="gbh-cats">'+catHtml+'</div>':'')+
    (blockers.length?'<details class="gbh-details"><summary>Launch blokajlarını göster</summary><div>'+blockers.map(function(x){return pill(x,'muted')}).join('')+'</div></details>':'')+
    '<p class="gbh-note">Bu ekran doğrulanmış bir “canlıya hazır yüzdesi” üretmez. Domain, ödeme sağlayıcısı, hukuk ve gerçek müşteri kabulü gibi harici kapılar doğrulanmadan production iddiası yapılmaz.</p>';
}
function html(p){return '<section class="gbh-wrap"><div class="gbh-kicker">OPERASYON SAĞLIĞI</div><h3>Watchdog · Deal Lifecycle · Launch Gate</h3><p class="gbh-desc">Gerçek payload durumunu gösterir; eksik telemetri veya harici onaylar başarı varsayımıyla doldurulmaz.</p><div class="gbh-grid"><article><h4>Watchdog Brain</h4>'+watchdogHtml(p.watchdog)+'</article><article><h4>A12 Deal Lifecycle</h4>'+dealHtml(p.deal_lifecycle_summary)+'</article><article class="gbh-wide"><h4>Canlıya Çıkış Kapıları</h4>'+launchHtml(p.launch_readiness_report,p.launch_gate)+'</article></div></section>'}
function css(){if(document.getElementById('gbh-css'))return;var st=document.createElement('style');st.id='gbh-css';st.textContent='.gbh-wrap{margin:14px 0 22px;padding:16px;border:1px solid #31536a;border-radius:16px;background:#071b2a}.gbh-kicker{font-size:10px;letter-spacing:.12em;color:#f3a14d;font-weight:900}.gbh-wrap h3{margin:3px 0 6px;font-size:20px}.gbh-desc{margin:0 0 12px;color:#aebfca;font-size:12px;line-height:1.5}.gbh-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}.gbh-grid article{border:1px solid #284b62;background:#0b2537;border-radius:13px;padding:12px}.gbh-grid h4{margin:0 0 9px;font-size:13px}.gbh-wide{grid-column:1/-1}.gbh-metrics{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:8px}.gbh-pill{font-size:9px;padding:5px 7px;border-radius:999px;border:1px solid #31536a;color:#c7d4dc;background:#0d2a3e}.gbh-pill.ok{border-color:#35755d;color:#8ee0bd}.gbh-pill.warn{border-color:#7f6230;color:#efd08a}.gbh-pill.bad{border-color:#743e46;color:#f0a5ae}.gbh-pill.human{border-color:#476e98;color:#9ec8ff}.gbh-pill.muted{color:#9caab3}.gbh-attn{margin:8px 0 0;padding:0;list-style:none;display:grid;gap:6px}.gbh-attn li{padding:8px;border-radius:9px;background:#091f2f;border:1px solid #284b62}.gbh-attn b,.gbh-attn small,.gbh-attn span{display:block}.gbh-attn b{font-size:11px}.gbh-attn small{font-size:9px;color:#9ec8ff;margin-top:2px}.gbh-attn span{font-size:9px;color:#aebfca;margin-top:4px}.gbh-note,.gbh-empty{font-size:9px;line-height:1.5;color:#aebfca}.gbh-note{margin:8px 0 0}.gbh-cats{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:6px}.gbh-cat{padding:8px;border:1px solid #284b62;border-radius:9px;background:#091f2f}.gbh-cat b,.gbh-cat span,.gbh-cat small{display:block}.gbh-cat b{font-size:10px}.gbh-cat span{font-size:12px;font-weight:900;margin-top:3px}.gbh-cat small{font-size:8px;color:#9caab3;margin-top:3px}.gbh-details{margin-top:8px;font-size:9px}.gbh-details summary{cursor:pointer;color:#9ec8ff;margin-bottom:7px}.gbh-states{margin-top:6px}@media(max-width:650px){.gbh-grid{grid-template-columns:1fr}.gbh-wide{grid-column:auto}.gbh-cats{grid-template-columns:1fr}}';document.head.appendChild(st)}
function render(){css();var h=host();if(!h||!PAYLOAD)return;var old=h.querySelector('.gbh-wrap');if(old)old.remove();var box=document.createElement('div');box.innerHTML=html(PAYLOAD);h.insertBefore(box.firstChild,h.firstChild)}
function install(){var oc=window.openCard;if(typeof oc==='function'&&!oc.__gbh){window.openCard=function(k,t){oc(k,t);if(k==='report'||k==='agents'||k==='settings')setTimeout(render,15)};window.openCard.__gbh=true}var ot=window.openTab;if(typeof ot==='function'&&!ot.__gbh){window.openTab=function(k){ot(k);if(k==='report'||k==='settings')setTimeout(render,15)};window.openTab.__gbh=true}}
function start(){install();fetch('/data/latest-opportunities.json?t='+Date.now(),{cache:'no-store'}).then(function(r){if(!r.ok)throw new Error('payload');return r.json()}).then(function(x){PAYLOAD=x||{};window.__GB_SYSTEM_PAYLOAD=PAYLOAD}).catch(function(){PAYLOAD={}})}
start();
})();
