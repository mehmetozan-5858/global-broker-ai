# Teklif giriş/MFA dönüşü — üretim doğrulaması

PR #130–#133; son üretim 95925ef920042b0fbb9b477b0382e50b04c61b9f READY. CI, mobil dağıtım ve ekosistem tarayıcı iş akışı geçti. 486 Python ve 25 JavaScript testi.

Tarayıcı kanıtı: https://github.com/mehmetozan-5858/global-broker-ai/actions/runs/39420822104

390px/1280px gerçek sayfa dosyaları ve yakalanmış sentetik Auth/MFA/RPC ile teklif ekranı → giriş → hatalı TOTP kodunun reddi → doğru kod → teklif formu akışı geçti. Mevcut AAL2 oturumuyla tekrar kod istenmediği, sunucunun geçersiz saydığı oturumun ilerlemediği, dış dönüş adresinin reddedildiği ve eksik refresh bilgisiyle yeniden giriş istendiği de doğrulandı. Gerçek hesap, parola, MFA faktörü veya teklif değiştirilmedi.

Giriş düğmesi HTMLde başlangıçta devre dışı; kurtarma/oturum başlangıcı bitince açılır. Önceki testte erken tıklamanın işlenmemesi bu kontrolle düzeltildi. Gerçek inline hesap kodunu geciktirilmiş başlangıçla çalıştıran regresyon testinde de doğrulandı. İzinli üç dönüş yolu dışında otomatik gezinme yok; URLde belirteç/parola/kod taşınmaz. Güvenlik ekranı sunucu /auth/v1/user yanıtını doğrulamadan mevcut AAL2 ile dönmez. Veritabanı yönetici+AAL2 kapısı değişmedi.

Web yeniden yazımlarında hesap dosyaları /web/ altında açık adresten yüklenir; mobil statik paket hazırlığında uygun yerel dosya yollarına dönüştürülür. Gerçek paketleme bloğuyla 5 yerel hesap/güvenlik/teklif scripti doğrulandı.

Web %77 / uygulama %72. P6 bağımsız telefon/SMS ve gerçek kurtarma kabulünü bekler; bu teknik akış gerçek kullanıcı veya müşteri kabulü yerine geçmez.

## Gerçek yönetici cihazında doğrulama

20 Ekim 2026 saat 15:19 (Europe/Istanbul), kullanıcı konuşmada iPhone Safari ekran görüntüleri paylaştı. Kod girdikten sonra broker.aivisibilityworks.com üzerindeki Teklif kanıtları sayfasında “Yönetici erişimi doğrulandı” mesajı ve boş teklif formu görülüyor. Bu, gerçek yönetici MFA dönüşü ve form erişiminin görsel kabulüdür. Kaydetme işlemi görülmedi; 1250.50/USD/25 alanları örnek yer tutuculardır. Gerçek teklif, SMS/parola kurtarma veya gerçek müşteri kabulü olarak sayılmaz. P6 açık, web %77 / uygulama %72 kalır.
