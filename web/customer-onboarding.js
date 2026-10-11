(function(){
  'use strict';
  var KEY='gb_customer_onboarding_v1';
  function done(){try{return localStorage.getItem(KEY)==='done'}catch(e){return false}}
  function mark(){try{localStorage.setItem(KEY,'done')}catch(e){}}
  function show(){
    if(done()||document.getElementById('gbOnboarding'))return;
    var wrap=document.createElement('div');wrap.id='gbOnboarding';wrap.setAttribute('role','dialog');wrap.setAttribute('aria-modal','true');wrap.setAttribute('aria-label','Global Broker başlangıç rehberi');
    wrap.innerHTML='<div class="gb-on-card"><button class="gb-on-x" aria-label="Kapat">×</button><small>GLOBAL BROKER · HIZLI BAŞLANGIÇ</small><h2>3 adımda kullanmaya başlayın</h2><div class="gb-on-step"><b>1 · Sektör ve ülke</b><span>Hesabım bölümünde çalıştığınız sektörleri ve hedef ülkeleri seçin.</span></div><div class="gb-on-step"><b>2 · Fırsatları inceleyin</b><span>Fırsatlar ekranında ürün, miktar, son tarih ve kaynak kapsamını kontrol edin.</span></div><div class="gb-on-step"><b>3 · Kontrollü tanıştırma</b><span>Uygun fırsatta Tanıştırma Talebi gönderin. Ham iletişim bilgisi satılmaz; doğrulama tamamlandıktan sonra süreç kontrollü yürütülür.</span></div><div class="gb-on-actions"><button data-go="opps">Fırsatları gör</button><a href="/account">Sektör / ülke ayarları</a></div></div>';
    var s=document.createElement('style');s.textContent='#gbOnboarding{position:fixed;inset:0;background:rgba(2,10,17,.76);z-index:99999;display:grid;place-items:center;padding:18px}.gb-on-card{position:relative;width:min(560px,100%);background:#0a2234;border:1px solid #31536a;border-radius:18px;padding:22px;box-shadow:0 28px 80px #0008;color:#fff}.gb-on-card small{color:#f3bd67;font-weight:900;letter-spacing:.1em}.gb-on-card h2{margin:7px 34px 15px 0}.gb-on-step{display:grid;gap:4px;padding:11px 0;border-top:1px solid #24465d}.gb-on-step span{color:#c3d0d9;font-size:13px;line-height:1.45}.gb-on-x{position:absolute;right:12px;top:12px;border:0!important;background:#173d55!important;color:#fff!important;border-radius:999px!important;width:34px;height:34px;padding:0!important;font-size:21px}.gb-on-actions{display:flex;gap:10px;flex-wrap:wrap;margin-top:16px}.gb-on-actions button,.gb-on-actions a{display:inline-block;text-decoration:none;border:0;border-radius:10px;padding:11px 14px;background:#d3a04e;color:#081521;font-weight:800;font-size:13px}.gb-on-actions a{background:#173d55;color:#dce8ef}';document.head.appendChild(s);
    document.body.appendChild(wrap);
    function close(){mark();wrap.remove();s.remove()}
    wrap.querySelector('.gb-on-x').onclick=close;
    wrap.addEventListener('click',function(e){if(e.target===wrap)close()});
    var go=wrap.querySelector('[data-go="opps"]');if(go)go.onclick=function(){close();if(typeof window.openCard==='function')window.openCard('opps','Fırsatlar')};
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',function(){setTimeout(show,250)});else setTimeout(show,250);
})();
