# İletişim formu ve özel e-posta yönlendirmesi

Kullanıcı tercihi: kişisel telefon/e-posta yalnız güvenlik için kullanılır. Müşteriler web ve uygulamadaki “Bize ulaşın” bağlantısından `/contact` formuna yazabilir. Form ad, yanıt adresi, konu ve mesaj alır; kişisel yönetici iletişim bilgilerini göstermez.

Broker sunucusu alanları doğrular, yalnız izin verilen kaynakları kabul eder ve mesajı zaman damgalı HMAC imzasıyla AI Visibility sunucusuna iletir. IP yalnız anahtarlı özet olarak aktarılır. E-posta sağlayıcı anahtarı ve hedef adres AI Visibility sunucusunda kalır. Alıcı müşteri isteğinden alınmaz.

Mesaj önce özel gelen kutusuna kaydedilir. Aynı gönderim kimliği ve içerik tekrar geldiğinde ikinci kayıt/e-posta oluşturulmaz; farklı içerik aynı kimlikle reddedilir. E-posta servisi kabul ederse form bunu açıkça söyler. Gönderim hatasında kayıt kuyrukta kalır; e-posta iletildi denmez. Kayıt da doğrulanamazsa form metni korunur. Bekleyenler mevcut günlük döngüde sınırlı olarak tekrar denenir; sağlayıcı deduplikasyon penceresi dışındaki belirsiz iletim elle incelemeye alınır.

Özel gelen kutusu: `https://www.aivisibilityworks.com/admin/broker-mesajlari` (yönetici oturumu gerekli). Müşteri mesajı yeni müşteri/lead veya ödeme kaydı oluşturmaz ve otomatik yanıt göndermez.

Doğrulama: 431 Python testi; e-posta tarafında 384 Node testi ve Next production build; 390px/1280px form kontrolleri. Üretim testinin sabit kimliği `3fb7b761-2ea9-4a10-a49e-c5f37e730d40`; yalnız mevcut yönetici e-postasına açıkça sistem testi olarak gönderilir, tekrar deneme aynı kimlikle deduplike edilir. Bu gerçek müşteri kabulü değildir. E-posta servisinin kabulü, mesajın okunduğuna veya gelen kutusuna teslim edildiğine dair kanıt değildir.
