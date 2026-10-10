# Global Broker — İki Kollu Üretim Yol Haritası
Sürüm: 2026-10-10 · Durum: canlı test sonuçları esas alınır, plan tamamlanma iddiası değildir.

## Temel ilkeler
- Sadece uluslararası ticarete konu olabilecek **fiziksel mal alımları** ana fırsat akışına girer. Hizmet/yapım hariç, karma ve belirsiz ilanlar incelemede.
- İlanın varlığı; miktarın, teknik şartnamenin, ihracat izninin veya tedarikçi uygunluğunun teyidi değildir. Kanıt yoksa alan **bilinmiyor** olarak görünür; tahmin ayrı etiketlenir.
- İşletme modeli: **önce ücretsiz veya minimum sabit gider**. Ücretli sağlayıcıya geçmeden önce kullanım koşulları, maliyet, yenileme, kota ve alternatifleri gözden geçirilir.
- **Shadow Mode:** Doğrulanmış yetki, sözleşme ve ticari onay olmadan dışarıya teklif/e-posta/ödeme/sipariş gönderilmez.
- Her paket kapanışı: kod + otomatik test + dağıtım + canlı davranış kontrolü + maliyet kontrolü.

## WEB PORTAL — W1–W5
| Paket | Çıktı | Kabul ölçütü | Durum |
|---|---|---|---|
| W1 Görsel kimlik | Fotoğraflı, renkli, mobil uyumlu TR ana sayfa; güvenilir metinler | 375px ve masaüstünde taşma yok, görseller yükleniyor, erişilebilir menü, linkler çalışıyor | Geliştiriliyor |
| W2 Müşteri deneyimi | Ülke→şehir→fiziksel ürün; arama/filtre/şartname; ücretsiz tanıtım ve erişim ayrımı | Gerçek veriyle doğru filtreleme, gizli veriler sunucuda korumalı | Plan |
| W3 Kimlik ve kurumsal güven | Sunucu tarafı giriş, rol bazlı erişim, kurtarma/2FA, doğrulanmış iletişim, gizlilik/şartlar | Yetkisiz erişim testleri, oturum güvenliği, hukuk incelemesi | Plan |
| W4 Ticari model | Fiyatlandırma, sözleşme, fatura/ödeme, komisyon kaydı | Sağlayıcı ve yasal koşullar doğrulanmış, test ödeme ve iade akışı | Plan |
| W5 Yayın | Özel .com, DNS/HTTPS, SEO, izleme, yedek, performans, TR/EN | DNS sahibi doğrulanmış, mobil/SEO/güvenlik testleri geçilmiş | Plan |

## GLOBAL BROKER UYGULAMASI — A1–A10
| Paket | Çıktı | Kabul ölçütü | Durum |
|---|---|---|---|
| A1 Tarama sağlığı | GitHub Actions/entegrasyonlar çalışır, veri güncellik etiketi | Art arda başarılı tarama ve güncel veri zaman damgası | İzlemede |
| A2 Mal alımı filtresi | Hizmet ve yapım dışarıda, karma/unknown incelemede | Karışık gerçek örneklerle sınıflandırma testleri | İlk sürüm mevcut; genişletilecek |
| A3 Eksik alanlar | Ülke/şehir/ürün/miktar; bilinmeyen nedenleri ve kanıt bağlantısı | Kaynaktan izlenebilir alan; tahminler resmî veri diye sunulmaz | Kısmen mevcut |
| A4 Körfez bağlantıları | Suudi Arabistan, BAE, Katar öncelikli; ardından Kuveyt, Umman, Bahreyn, Yemen | Gerçek ilan, gerçek belge ve yenilenme testi; yalnız bağlantı yeterli değil | Kaynak dizini mevcut, canlı aktarım yok |
| A5 Şartname | Teknik özellik, evrak, teminat, ödeme, teslim | Belge metninden alan kanıtı, eksik alanlar görünür | Kısmen mevcut |
| A6 Tedarikçi | Üretici/tedarikçi araştırma ve teyit | Kaynaklı iletişim ve ürün eşleşmesi | Plan |
| A7 Ticari fizibilite | Fiyat, navlun, ithalat/menşe ve maliyet | Para birimi, miktar ve varsayımlar şeffaf | Plan |
| A8 Teklif/risk | Taslak teklif, uyum kontrolü, komisyon ve sözleşme | İnsan onayı olmadan dış eylem yok | Plan |
| A9 Ajan merkezi | Kaynak başına uzman ajan, kota bütçesi, günlük CEO raporu | Başarılı iş/sıra/başarısızlık ölçülebilir | Kısmen mevcut |
| A10 Launch Gate | Uçtan uca test, güvenlik, yasal ve müşteri kabulü | Kritik açık sorun yok; gerçek müşteri akışı doğrulandı | Plan |

## 20 günlük hedef çalışma dizisi (garanti süre değil)
- Gün 1–4: W1 + A1; fotoğraflı web yayını, tarama hataları ve son başarılı çalışma.
- Gün 5–8: W2 ilk sürüm + A2–A3; ürün sınıflandırması, miktar ve ülke kanıtı.
- Gün 9–12: A4–A5; Körfez resmî kaynak bağlantısı ve belge çözümleme.
- Gün 13–16: W3 + A6–A9 ilk akış; güvenli giriş, müşteri/tedarikçi ayrımı, insan onayı.
- Gün 17–20: W4–W5 + A10; testler, maliyet ve mevzuat kontrolü, aşamalı yayın kararı.

## Operasyon
Her paket için GitHub PR, CI sonucu, canlı kontrol kanıtı ve gider tahmini tutulur. Ücretsiz servislerin ticari kullanım şartları incelenir. Ücretli hizmet ve alan adı satın alımı kullanıcı onayı olmadan yapılmaz. Yönetici paneli ve hassas bilgiler herkese açık statik Pages üzerinde güvenli kabul edilmez.
