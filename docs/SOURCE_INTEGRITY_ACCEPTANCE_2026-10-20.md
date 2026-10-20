# Kaynak dosyası bütünlüğü ve ilan türü — 20 Ekim 2026

## Tamamlanan düzeltmeler

- PR #114: Kabul edilmiş kaynak bütçesinin ham tekrarlı değerlerce bozulması önlendi. Para birimi dosya kartında korunuyor. Çok-kalem miktar/bütçe düzleştirmesi kaldırıldı. Kaynak bağlantısı dil varyantlarından önce okunuyor. Çelişkili bütçe çekirdek dosyayı tamamlamıyor.
- PR #115: TED form-type alanı istendi ve yalnız toplu tür sayılarıyla ölçüldü.
- PR #116: Competition ile result/planning/değişiklik gibi bağlamlar ayrıldı. Kayıtlar saklandı; etiket, araştırma için kapalı müşteri tanıştırma düğmesi, ortak yönetici hazırlığı ve sunucu iç teklif kapısı aynı bağlamı kullanıyor.

## Canlı kanıt

- 455 Python ve 16 JavaScript testi geçti.
- 390px/1280px müşteri etiket/düğme, yönetici hazırlığı ve ekosistem kontrolleri geçti: https://github.com/mehmetozan-5858/global-broker-ai/actions/runs/39382134125 .
- Kaynak örneğinde 7/7 bütçe dosyadan ve kamuya izinli alandan aynı tutar/para birimiyle geçti.
- b46b8b5 önceki anlık görüntüsünde bütçeli 11 dosyanın 11'inde kart para birimi eksikti; son görüntüde 0. Çok-kalemleri düzleştiren dosyalar 8→0.
- Son tam tarama 70 kayıt, 5 tam temel dosya, 11 kamuya izinli ilan bütçesi: https://github.com/mehmetozan-5858/global-broker-ai/actions/runs/39382134054 .
- TED dağılımı: 17 competition, 21 result, 1 planning; 22 araştırma kaydı. Diğer kaynaklar bu dağılıma dahil değil. Kaynak kümesi her taramada değişebilir; tür ayrımı hiçbir kaydı silmez.
- Kaynak fiyat/navlun, gerçek müşteri kabulü, ödeme, hukuk veya telefon kurtarma doğrulaması uydurulmadı. Sabit yol haritası hâlâ web %77 / uygulama %72; P2 bütün kabulü tamamlanmadı.

Yayımlanan maskeli veri: 6dfe198272d30c0772f9c930c0eb4def95a492b7. Alıcı adları yayımlanmadı; yeni dış mesaj veya ödeme gönderilmedi.
