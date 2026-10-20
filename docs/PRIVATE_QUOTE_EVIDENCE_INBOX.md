# Özel teklif kayıt ekranı

/quote-evidence, yönetici oturumu ve AAL2 doğrulamasıyla erişilir; /app üst menüsünden açılır. Alış veya satış teklifi, fırsat kimliği, karşı taraf, teklif referansı, tarih, geçerlilik, birim fiyat, para birimi, miktar, fiyat birimi ve HTTPS kaynak bağlantısı kaydedilir. Kaydetmek doğrulama veya ticari onay değildir; tüm kayıtlar pending_review kalır. Kaynak URL açılmaz, dış mesaj/teklif/ödeme yapılmaz.

Kayıtlar private.quote_evidence_inbox içinde kaynak taramalarından ayrı, yalnız eklemeli tutulur. Kamuya açık veri akışına ve Git kaynak dosyalarına teklif değerleri yazılmaz. Son 50 kayıt özel ekranda görünür. Güncel fırsat seçimi gerekir; arşivlenmiş fırsatın eski kaydı ve aynı istekle tekrar gönderimi korunur.

Yalnız yönetici+AAL2, özel şemadaki kısıtlı yardımcılar üzerinden listeleme ve ekleme yapabilir. Public RPC sarmalayıcıları security invoker; asıl private tablo için API rollerinin okuma/yazma yetkisi yok. RLS açık, varsayılan işlev izinleri iptal edilmiştir. Doğrulama işlevi auth.users ve sunucu role tablosunu denetler. İstemci approved/verified alanları gönderemez. Eksik/negatif fiyat, hatalı alan, kimlik bilgili kaynak URL ve bilinmeyen fırsat reddedilir. Teklifin girilmiş olması kaynağın veya tedarikçinin doğrulandığı anlamına gelmez.

SQL yetki ve tekrar deneme testleri tests/quote_evidence_authorization.sql içinde transaction/rollback ile yapılır: anonim, AAL1 ve yönetici olmayan kullanıcı reddi; doğru yönetici kaydı; aynı istek tekrarının tek kayıt olması; farklı içerikle tekrarın reddi; geçersiz alanlar ve tabloya doğrudan erişim reddi. Test sonunda kalıcı sentetik teklif sayısı 0. Güvenlik danışmanında yeni bulgu yok.

Tarayıcı regresyonu tüm RPC isteklerini yakalar; gerçek teklif göndermez. Mobil/masaüstü, 503 sonrası aynı UUID ile tekrar, pending_review durumu, güvenli metin gösterimi ve yetkisiz oturumları kontrol eder. P4 gerçek teklif, tam şartname ve ticari inceleme kanıtları gelene kadar açık kalır.
