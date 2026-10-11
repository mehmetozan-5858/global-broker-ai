(function(){
  'use strict';
  var guides={
    ceo:['Genel Bakış','Platformdaki fırsat, doğrulama ve işlem akışının üst düzey özetini gösterir.','Burada sadece özet durumu izleyin; işlem yapmak için ilgili fırsat veya tanıştırma ekranına geçin.'],
    markets:['Global Pazarlar','Fırsatları ülke ve bölge bazında incelemenizi sağlar.','Önce hedef pazarı seçin, sonra size açık sektörlerdeki fiziksel ürün taleplerini filtreleyin.'],
    opps:['Fırsatlar','Resmî ve doğrulanabilir kaynaklardan toplanan fiziksel ürün alım taleplerini gösterir.','Ürün, ülke, miktar ve son tarihi kontrol edin; uygun fırsatta Tanıştırma Talebi başlatın.'],
    buyers:['Alıcılar','Alıcı tarafındaki talepleri ve doğrulama durumunu takip eder.','Ham iletişim bilgisi gösterilmez; kimlik ve erişim kontrollü tanıştırma süreci tamamlandığında yönetilir.'],
    suppliers:['Tedarikçiler','Uygun üretici ve ihracatçı adaylarının araştırma ve doğrulama durumunu gösterir.','Doğrulanmış tedarikçi kanıtı olmayan kayıtları teklif için hazır kabul etmeyin.'],
    pricing:['Fiyat / Marj','Doğrulanmış birim fiyat, maliyet ve marj hesaplarının toplandığı bölümdür.','Kaynaklı fiyat kanıtı yoksa sistem hesaplama yapmaz; eksik alanlar araştırma kuyruğunda kalır.'],
    logistics:['Lojistik','Teslim yeri, Incoterm ve navlun kanıtlarını takip eder.','FOB, CIF veya CFR gibi şartları ve varış noktasını doğrulamadan toplam maliyeti kesin kabul etmeyin.'],
    trade:['Trade Agent','Ticari şartlar, ödeme koşulları ve ihale gerekliliklerini düzenler.','Eksik şartları kontrol edin; yalnız kaynakla doğrulanmış verileri işlem kararında kullanın.'],
    risk:['Risk Agent','Alıcı, tedarikçi, teslimat ve ticari şartlardaki riskleri işaretler.','Kırmızı veya eksik risk maddeleri kapanmadan teklif ya da işlem onayı vermeyin.'],
    communication:['Communication Agent','Onaylanmış süreçlerde kullanılacak teklif ve yazışma taslaklarını hazırlar.','Metinleri inceleyin; sistem insan onayı olmadan dışarıya mesaj göndermez.'],
    negotiation:['Negotiation Agent','Fiyat, teslimat ve ticari şartlardaki pazarlık maddelerini takip eder.','Karşı tarafın teyit ettiği şartları kayıt altına alın; varsayımları anlaşma saymayın.'],
    contract:['Contract Agent','Sözleşme ve komisyon koruma şartlarının taslak durumunu izler.','İmzalı ve hukuken gözden geçirilmiş metin olmadan sözleşmeyi aktif kabul etmeyin.'],
    commission:['Commission Agent','Başarılı işlem sonrası komisyon hakkı ve tahsilat kanıtlarını izler.','Komisyon yalnız sözleşme ve ödeme kanıtı oluştuğunda hak edilmiş sayılır.'],
    audit:['Audit Agent','Kaynak, doğrulama, onay ve işlem kayıtlarının kontrol katmanıdır.','Bir uyuşmazlıkta önce burada kayıt zincirini kontrol edin.'],
    secure:['Güvenli İşlem','Tanıştırma, onay ve özel görüşme erişimini kontrollü şekilde yönetir.','Doğrudan ham kontak satışı yapılmaz; taraflar uygunluk ve izin adımlarından geçer.'],
    protection:['12 Aylık Komisyon Koruması','Tanıştırma sonrası tekrar işlemlerde sözleşme kapsamındaki ilişki korumasını izler.','Koruma süresi ve kapsamı yalnız imzalı sözleşmede belirtilen şartlara göre uygulanır.'],
    payments:['Ödemeler','Platform ücretleri ve komisyon tahsilat durumlarını izler.','Ödeme sağlayıcısı doğrulaması olmadan ödeme tamamlandı kabul edilmez.'],
    report:['Raporlar','Fırsat, ajan, risk ve işlem durumlarını tek özet halinde sunar.','Gün sonunda önce bu ekranı kontrol ederek aksiyon gerektiren maddeleri görün.'],
    agents:['Ajanlar','Fırsat araştırma, fiyat, lojistik, risk ve doğrulama görevlerinin çalışma merkezidir.','Müşteri olarak ajanların durumunu izleyebilirsiniz; dış işlem yetkisi insan onayına bağlıdır.'],
    settings:['Ayarlar','Sektör, ülke ve hesap kapsamınızı yönettiğiniz bölümdür.','Fırsat akışınızın doğru çalışması için sektör ve ülke tercihlerinizi güncel tutun.']
  };
  var neutralBuyer='🔒 Alıcı kimliği kontrollü tanıştırma ile paylaşılır';
  function ensureStyle(){
    if(document.getElementById('gbCustomerGuideStyle'))return;
    var s=document.createElement('style');s.id='gbCustomerGuideStyle';s.textContent='.gb-guide{margin:12px 0 16px;padding:14px 15px;border:1px solid #31536a;border-radius:13px;background:linear-gradient(145deg,#0b2b40,#0a2132)}.gb-guide small{display:block;color:#f3bd67;font-weight:800;letter-spacing:.08em;margin-bottom:4px}.gb-guide h3{margin:0 0 6px;font-size:17px}.gb-guide p{margin:4px 0;color:#c7d5de;line-height:1.5;font-size:13px}.gb-guide b{color:#fff}';document.head.appendChild(s);
  }
  function inject(key){
    ensureStyle();
    var pc=document.getElementById('pc');if(!pc)return;
    var old=pc.querySelector('.gb-guide');if(old)old.remove();
    var g=guides[key]||['Bu bölüm','Bu ekran Global Broker iş akışının bir parçasıdır.','Ekrandaki doğrulama ve durum etiketlerini kontrol ederek ilerleyin.'];
    var box=document.createElement('div');box.className='gb-guide';
    box.innerHTML='<small>BU BÖLÜM NE İŞE YARAR?</small><h3>'+g[0]+'</h3><p>'+g[1]+'</p><p><b>Ne yapmalısınız?</b> '+g[2]+'</p>';
    pc.insertBefore(box,pc.firstChild);
  }
  function neutralizeBuyerLabels(root){
    var scope=root&&root.querySelectorAll?root:document;
    var nodes=scope.querySelectorAll?scope.querySelectorAll('.cp-fact strong,[data-buyer-display],.buyer-display'):[];
    for(var i=0;i<nodes.length;i++){
      var t=String(nodes[i].textContent||'');
      if(t.indexOf('Doğrulanmış alıcı')>=0||t.indexOf('kontrollü tanıştırma ile erişilir')>=0)nodes[i].textContent=neutralBuyer;
    }
  }
  function wrap(){
    var original=window.openCard;if(typeof original!=='function'||original.__gbGuided)return;
    var wrapped=function(key,title){var out=original.apply(this,arguments);setTimeout(function(){inject(key);neutralizeBuyerLabels(document)},0);return out};
    wrapped.__gbGuided=true;window.openCard=wrapped;
  }
  wrap();setTimeout(wrap,50);
  neutralizeBuyerLabels(document);
  if(window.MutationObserver){new MutationObserver(function(mutations){for(var i=0;i<mutations.length;i++){neutralizeBuyerLabels(mutations[i].target)}}).observe(document.body,{childList:true,subtree:true});}
})();
