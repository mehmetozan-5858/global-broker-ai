# Global Broker — Alan Adı ve Güvenli Yayına Alma

## Üretim yaklaşımı
Ücretsiz geliştirme sürecinde GitHub Pages önizleme ve kamuya açık veri ekranı olarak kullanılabilir. Gerçek müşteri hesabı, API ve özel erişim gerektiren üretim akışı için tercih edilen hedef **Vercel + Supabase** yapısıdır.

- Vercel proje alanı: `global-broker-ai.vercel.app` (ücretsiz geliştirme adresi)
- Supabase proje alanı: `global-broker-ai` (Auth + RLS veri katmanı)
- Özel `.com`: **henüz satın alınmadı**; kullanıcı açıkça alan adı seçip ücretli işlemi onaylamadan satın alma yapılmaz.

## Özel .com bağlama — satın alma sonrasında
1. Alan adı işletme sahibinin hesabında tescil edilir ve otomatik yenileme / MFA açılır.
2. Alan adı Vercel `global-broker-ai` projesine eklenir.
3. Vercel'in verdiği DNS kayıtları kayıt kuruluşunda uygulanır.
4. DNS ve TLS sertifikası doğrulanır; hem kök alan adı hem `www` yönlendirmesi test edilir.
5. Uygulamadaki canonical/OG adresleri, auth redirect URL'leri ve e-posta linkleri yeni alan adına alınır.
6. Alan adı doğrulanmadan `GB_CUSTOM_DOMAIN_VERIFIED=true` üretim kapısı açılmaz.

## Mevcut teknik hazırlıklar
- Vercel temiz rotaları: `/`, `/customer`, `/account`, `/pricing`, `/privacy`, `/terms`
- Temel güvenlik başlıkları Vercel yapılandırmasına eklendi.
- Supabase Auth gerçek e-posta giriş/kayıt/şifre yenileme ekranı `web/account.html` ile bağlandı.
- `customer_profiles`, korumalı `user_roles` ve `private_opportunity_access` tablolarında RLS aktif.
- Yönetici rolü istemci tarafından atanamaz.
- Shadow Mode dış eylemleri kapalı tutar.

## Yayına alma kapıları
- [x] Kaynaklı fiziksel ürün filtresi ve canlı veri doğrulaması
- [x] E-posta tabanlı gerçek Auth altyapısı ve RLS temel veri modeli
- [x] Vercel rota/güvenlik başlığı hazırlığı
- [x] Gizlilik/kullanım koşulları için açıkça **taslak** sayfalar
- [ ] Yönetici için bağımsız e-posta + telefon çift kurtarma doğrulaması (SMS sağlayıcısı gerekir)
- [ ] Gerçek ticari unvan, doğrulanmış destek/iletişim bilgisi
- [ ] KVKK/gizlilik ve kullanım koşullarının hukuk incelemesi
- [ ] Canlı ödeme sağlayıcısı, fatura ve iade akışının gerçek testleri
- [ ] Seçilen `.com` alan adının satın alınması ve DNS/TLS doğrulaması
- [ ] Körfez resmi kaynaklarından gerçek ilan + belge canlı ingest doğrulaması
- [ ] Gerçek müşteri kabul testi ve son güvenlik/performance kontrolü

## Güvenlik sınırı
`noindex` güvenlik değildir. GitHub Pages üzerindeki `dashboard.html` ve `admin.html` kamuya açık kabul edilmelidir; gizli müşteri verileri veya anahtarlar burada tutulmaz. Özel veri erişimi Supabase RLS ve sunucu tarafı API üzerinden yapılır.

`src/launch_gate.py` yukarıdaki üretim kapıları açıkça doğrulanana kadar `launch_ready=false` ve `mode=shadow` üretir. Bu nedenle kodun tamamlanması, ödeme/domain/hukuk gibi dış doğrulamalar tamamlanmadan "canlı ticarete hazır" anlamına gelmez.
