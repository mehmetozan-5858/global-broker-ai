# Teklif ekranına giriş/MFA sonrası geri dönüş

Teklif ekranı giriş ve MFA bağlantılarına /quote-evidence dönüş hedefi ekler. Hesap ekranı başarılı parola girişi veya doğrulanmış mevcut oturum sonrasında bu hedef için güvenlik ekranına ilerler. Şifre kurtarma formu tamamlanmadan otomatik geçiş yapılmaz. Normal hesap ve çıkış davranışı korunur.

Güvenlik ekranı Supabase oturumunu kurup sunucunun /auth/v1/user yanıtını doğrular. Mevcut AAL2 oturumuyla ek kod istemeden izinli hedefe döner; AAL1 oturumunda TOTP doğrulaması gerekir. Hatalı kod veya geçersiz oturum geri dönüşü açmaz. Hesabım bağlantısı da hedefi korur.

Hedefler yalnız /account, /app ve /quote-evidence. Harici adres, protokol-relative, parçacık, sorgu, yol kaçışı ve çift kodlama reddedilir. URLde belirteç, parola veya kod taşınmaz. Ortak hedef modülü yüklenmezse otomatik yönlendirme yapılmaz. Yönetici+AAL2 veritabanı kapısı değiştirilmedi.

Hesap ekranının yerel JS bağımlılıkları /web/ mutlak yolundan yüklenir; /account yeniden yazımı nedeniyle kökte kaybolmaz.

Üç Node sözleşme testi; ayrıca üretim tarayıcı regresyonu gerçek sayfa dosyalarıyla ve yakalanmış sentetik Auth/MFA/RPC istekleriyle mobil/masaüstü giriş → hatalı kod reddi → başarılı MFA → teklif ekranına dönüşü, mevcut AAL2, dış hedef reddi ve geçersiz oturum reddini kontrol eder. Gerçek parola/faktör/teklif değiştirilmez; bu gerçek yönetici kabulü veya SMS kurtarma kabulü değildir.
