(function(){
  'use strict';
  // Customer-only explanatory content. Never synthesizes counts, verified buyers, quotes or deals.
  var sections={
    agents:{title:'Dijital ticaret asistanları',intro:'Ajanlar araştırma ve hazırlık süreçlerini destekler; ekranda gösterilmeyen bir işlem gerçekleşmiş sayılmaz.',steps:[['Fırsat araştırması','Kaynağı ve ürün kapsamı okunabilen talepleri inceleyin.'],['Uygunluk kontrolü','Sektör, ülke ve belge kapsamını kontrol edin.'],['İnsan onayı','Tanıştırma, fiyat ve bağlayıcı işlemler doğrulanmadan otomatik yapılmaz.']],action:'Fırsatlara geç',target:'opps'},
    opps:{title:'Fırsat bulma rehberi',intro:'İlanlar ticari işlem veya doğrulanmış alıcı garantisi değildir. Eksik miktar, şartname ve alıcı bilgileri tahmin edilmez.',steps:[['Sektör ve ülke','Hesap tercihlerinizin fırsat havuzuyla eşleştiğini kontrol edin.'],['Kaynak kanıtı','İlan bağlantısı, kapsam ve son tarihi inceleyin.'],['Tanıştırma','Uygun fırsatta kontrollü tanıştırma isteği oluşturun.']],action:'Sektör / ülke ayarları',href:'/account'},
    report:{title:'İşlem takibi nasıl çalışır?',intro:'Rapor alanları yalnız kayıtlı ve yetkili müşteri işlemlerinden oluşmalıdır. Kayıt yoksa başarı veya faaliyet sayısı gösterilmez.',steps:[['İncelenen fırsatlar','Önce fırsat kartlarını ve kaynak kapsamını kontrol edin.'],['Tanıştırma istekleri','İsteğin durumu onay ve doğrulama aşamalarına bağlıdır.'],['Teklif ve sözleşme','Gerçek, doğrulanmış ticari kanıt oluşmadan tamamlandı gösterilmez.']],action:'Fırsatları incele',target:'opps'},
    settings:{title:'Hesabınızı hazır hale getirin',intro:'Gördüğünüz fırsatlar sektör, ülke seçimi ve erişim kapsamınıza göre değişebilir.',steps:[['Sektör seçimi','Çalıştığınız fiziksel ürün gruplarını seçin.'],['Hedef pazar','İlgilendiğiniz ülkeleri güncelleyin.'],['Erişim ve güvenlik','Tanıştırma kredisi ve hesap erişiminizi gözden geçirin.']],action:'Hesap ve paket ayarları',href:'/account'},
    markets:{title:'Pazarları değerlendirin',intro:'Pazar araştırması, canlı alıcı veya mevcut ticari teklif bulunduğu anlamına gelmez.',steps:[['Ülke seçimi','Hedef coğrafyanızı belirleyin.'],['Ürün kontrolü','Sektörünüze uygun fiziksel ürün taleplerini filtreleyin.'],['Kaynak inceleme','Her fırsatın resmi kaynağını ve doğrulama durumunu kontrol edin.']],action:'Fırsatlara geç',target:'opps'}
  };
  function el(tag,cls,txt){var n=document.createElement(tag);if(cls)n.className=cls;if(txt)n.textContent=txt;return n}
  function render(key){
    var host=document.getElementById('pc');if(!host)return;
    var old=host.querySelector('.gb-customer-readiness');if(old)old.remove();
    var item=sections[key];if(!item)return;
    var card=el('section','gb-customer-readiness');
    card.setAttribute('aria-label','Bu bölümde nasıl ilerlenir');
    card.appendChild(el('div','gb-cr-kicker','GLOBAL BROKER · KULLANIM REHBERİ'));
    card.appendChild(el('h3','',item.title));
    card.appendChild(el('p','gb-cr-intro',item.intro));
    var grid=el('div','gb-cr-grid');
    item.steps.forEach(function(step,i){var tile=el('div','gb-cr-step');tile.appendChild(el('strong','',String(i+1)+' · '+step[0]));tile.appendChild(el('p','',step[1]));grid.appendChild(tile)});
    card.appendChild(grid);
    var action=item.href?el('a','gb-cr-action',item.action):el('button','gb-cr-action',item.action);
    if(item.href){action.href=item.href;action.target='_top'}
    else{action.type='button';action.onclick=function(){if(typeof window.openCard==='function')window.openCard(item.target,item.target==='opps'?'Fırsatlar':'Global Pazarlar')}}
    card.appendChild(action);
    var note=el('p','gb-cr-note','Bilgilendirme: Bu rehber gerçek fırsat, müşteri, teklif veya gerçekleşmiş işlem kaydı oluşturmaz.');
    card.appendChild(note);host.appendChild(card);
  }
  var style=el('style');style.textContent='.gb-customer-readiness{margin:14px 0 20px;padding:17px;border:1px solid #35566a;border-radius:16px;background:#0b2536;color:#edf3f7}.gb-cr-kicker{font-size:10px;font-weight:800;letter-spacing:.09em;color:#f2b86b}.gb-customer-readiness h3{font-size:19px;margin:8px 0}.gb-cr-intro,.gb-cr-step p{font-size:13px;line-height:1.5;color:#b9cbd7}.gb-cr-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px;margin:14px 0}.gb-cr-step{padding:12px;border:1px solid #29485b;border-radius:12px;background:#102c40}.gb-cr-step strong{font-size:13px}.gb-cr-step p{margin:7px 0 0}.gb-cr-action{display:inline-block;padding:11px 15px;border:0;border-radius:10px;background:#f2a34a;color:#091b29;font-size:13px;font-weight:800;text-decoration:none;cursor:pointer}.gb-cr-note{font-size:11px;color:#8fa9ba;margin:13px 0 0}@media(max-width:650px){.gb-cr-grid{grid-template-columns:1fr}}';document.head.appendChild(style);
  function wrap(){
    var original=window.openCard;if(typeof original!=='function'||original.__gbReadiness)return;
    var wrapped=function(key){var out=original.apply(this,arguments);render(key);return out};
    wrapped.__gbReadiness=true;window.openCard=wrapped;
  }
  wrap();setTimeout(wrap,100);
})();