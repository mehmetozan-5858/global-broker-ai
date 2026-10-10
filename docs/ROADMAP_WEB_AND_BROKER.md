# Global Broker — İki Kollu Üretim Yol Haritası
Sürüm: 2026-10-10 · Durum: kod, otomatik test ve canlı Shadow Scan sonuçları esas alınır.

## Temel ilkeler
- Sadece uluslararası ticarete konu olabilecek **fiziksel mal alımları** ana fırsat akışına girer. Hizmet/yapım hariç, karma ve belirsiz ilanlar incelemede.
- İlanın varlığı; miktarın, teknik şartnamenin, ihracat izninin veya tedarikçi uygunluğunun teyidi değildir. Kanıt yoksa alan **bilinmiyor** olarak görünür; tahmin ayrı etiketlenir.
- İşletme modeli: **önce ücretsiz veya minimum sabit gider**. Ücretli sağlayıcıya geçmeden önce kullanım koşulları, maliyet, yenileme, kota ve alternatifleri gözden geçirilir.
- **Shadow Mode:** Doğrulanmış yetki, sözleşme ve ticari onay olmadan dışarıya teklif/e-posta/ödeme/sipariş gönderilmez.
- Her paket kapanışı: kod + otomatik test + dağıtım + canlı davranış kontrolü + maliyet kontrolü.
- Kodun hazır olması, alan adı/ödeme/hukuk/SMS gibi dış üretim kapılarının tamamlandığı anlamına gelmez.

## WEB PORTAL — W1–W5
| Paket | Çıktı | Durum |
|---|---|---|
| W1 Görsel kimlik | Fotoğraflı, renkli, mobil uyumlu kurumsal ana sayfa | **Uygulandı ve yayınlandı** |
| W2 Müşteri deneyimi | Fiziksel ürün arama, ülke/şehir/alıcı, veri doluluk filtresi ve güçlü fırsat sıralaması | **Uygulandı ve canlı veriyle çalışıyor** |
| W3 Kimlik ve kurumsal güven | Supabase Auth giriş/kayıt/şifre yenileme, RLS profiller, korumalı roller ve özel erişim tablosu | **Kod + veri katmanı uygulandı; yönetici telefon+e-posta çift kurtarma için SMS sağlayıcısı bekliyor** |
| W4 Ticari model | Fail-closed billing gate, şeffaf ticari model sayfası, ödeme/iade/fatura üretim kapıları | **Kod hazır; gerçek ödeme sağlayıcısı, hukuki taraf, fatura ve iade testi olmadan ödeme kapalı** |
| W5 Yayın | Vercel temiz rotalar, güvenlik başlıkları, TR + EN sayfalar, domain checklist | **Teknik hazırlık uygulandı; `.com` satın alma ve DNS/TLS kullanıcı onayı sonrası** |

## GLOBAL BROKER UYGULAMASI — A1–A10
| Paket | Çıktı | Durum |
|---|---|---|
| A1 Tarama sağlığı | Süre sınırlı, seri Shadow Scan, atomik yayın | **Tamamlandı ve canlı tarama geçti** |
| A2 Mal alımı filtresi | Hizmet/yapım/dijital dışarıda; karma/unknown incelemede | **Tamamlandı ve canlı kapı aktif** |
| A3 Eksik alanlar | Kaynak kanıtlı ülke/şehir/ürün/miktar/son tarih/alıcı; iki geçişli zenginleştirme | **Tamamlandı; eksik alanlar bilinmiyor olarak korunuyor** |
| A4 Körfez bağlantıları | Resmî kaynak registry + Katar Monaqasat gerçek liste adapteri | **Katar canlı adapteri uygulandı; Suudi Arabistan + BAE canlı ingest doğrulaması eksik, bu yüzden A4 üretim kapısı kapalı** |
| A5 Şartname | Belge/teknik şartname + ödeme/teminat/teslim/yeterlilik/ödül kriteri kanıt alanları | **Uygulandı; kaynağın vermediği alanlar eksik kalıyor** |
| A6 Tedarikçi | Şartnameye bağlı tedarikçi araştırma kuyruğu ve doğrulama kuralı | **Kod uygulandı; dış kaynaktan gerçek tedarikçi adayları doğrulanmadan satışa hazır sayılmaz** |
| A7 Ticari fizibilite | Miktar, para birimi, doğrulanmış fiyat/navlun/gümrük/teslim girdileri | **Fail-closed hesaplama kapısı uygulandı; veri yoksa marj üretilmiyor** |
| A8 Teklif/risk | İç taslak uygunluğu, doğrulama engelleri, dış eylem yasağı | **Uygulandı; insan onayı olmadan dış işlem yok** |
| A9 Ajan merkezi | Ajan/stage durum sayaçları, kota dostu Shadow policy | **Uygulandı; dış eylemler kapalı** |
| A10 Launch Gate | Teknik + auth + depolama + hukuk + ödeme + domain + Körfez + müşteri kabul kapıları | **Uygulandı ve fail-closed; bütün dış kapılar geçmeden `launch_ready=false`** |

## Canlı üretime geçmek için kalan DIŞ kapılar
1. Suudi Arabistan Etimad ve BAE resmî platformlarından gerçek ilan + belge canlı ingest doğrulaması.
2. Yönetici hesabı için e-posta + telefon bağımsız çift kurtarma doğrulaması için SMS sağlayıcısı.
3. Ticari unvan/işletme iletişim bilgileri ve hukuk tarafından incelenmiş KVKK/kullanım/iade metinleri.
4. Gerçek ödeme sağlayıcısı veya resmî banka/fatura akışı ve test işlemi.
5. Kullanıcının seçip açıkça onayladığı `.com` alan adının satın alınması ve DNS/TLS doğrulaması.
6. Gerçek müşteri kabul testi.

## Operasyon
Her Shadow Scan; A2–A10 veri/güvenlik aşamalarını çalıştırır. `src/launch_gate.py` bütün gerekli dış üretim doğrulamaları tamamlanmadan canlı ticaret modunu açmaz. Bu sayede yazılım geliştirmesi ilerlerken yanlışlıkla ödeme, teklif, sipariş veya müşteri verisi açılması engellenir.
