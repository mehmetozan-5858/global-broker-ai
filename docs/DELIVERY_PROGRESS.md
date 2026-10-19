# Global Broker — web ve uygulama ilerleme sırası

Başlangıç: 19 Ekim 2026. Web **%70**, uygulama **%65**.
Bu oranlar sabit kapsamlı teslimat tahminidir; ticari açılış, veri doluluğu veya gelir yüzdesi değildir.
Önceki genel %65–70 tahmini bu takibin başlangıcıdır. Mevcut uygulama bir web/PWA uygulamasıdır; ayrı bir native iOS/Android uygulaması bu kapsamda sayılmaz.

| Sıra | Paket | Web puanı | Uygulama puanı | Tamamlandığında web / uygulama |
|---|---|---:|---:|---|
| P1 | Ortak ekosistem girişleri | +2 | +2 | %72 / %67 |
| P2 | Kaynaklı fırsat dosyası | +5 | +8 | %77 / %75 |
| P3 | Tedarikçi ve ürün uygunluğu | +4 | +6 | %81 / %81 |
| P4 | Gerçek fiyat, lojistik ve risk | +5 | +6 | %86 / %87 |
| P5 | AI Visibility firma aktarımı | +5 | +5 | %91 / %92 |
| P6 | Hesap ve güvenli erişim | +4 | +3 | %95 / %95 |
| P7 | Ticari açılış koşulları | +3 | +3 | %98 / %98 |
| P8 | Gerçek kullanıcı kabulü | +2 | +2 | %100 / %100 |

## Takip kuralı

- Makine tarafından okunan kayıt: `docs/delivery-progress.json`.
- Güncel oran: `python -m src.delivery_progress`.
- Paket ancak test, üretim dağıtımı ve canlı davranış kanıtıyla `complete` olur. Kodun yazılması veya PR açılması tek başına puan kazandırmaz.
- Eksik/engelli iş `in_progress` veya `blocked` kalır. Tekrar açılan paketin puanı geri alınır.
- Her güncelleme: önceki oran → değişiklik → test sonucu → dağıtım/canlı kontrol → yeni oran.
- Paket kapsamı büyürse başlangıcı veya ağırlıkları sessizce değiştirme; yeni kapsamı ayrı sürüm olarak açıkla.
- %100 bu yol haritasının kabulünü anlatır. Güncel launch gate, özel veri yetkileri ve dış işlem onayları bağımsız kalır.

## P1 kapsamı

Türkçe ve İngilizce kurumsal sayfadan, müşteri portalından ve yönetici arayüzünden ortak ekosistem ekranına erişim. AI Visibility ön değerlendirme ve plan sayfalarına sabit güvenli bağlantılar. Mobil/masaüstü, klavye erişimi ve mevcut hesap kapısının korunması doğrulanır.

Bu paket otomatik firma aktarımı veya ortak giriş sağlamaz; bunlar P5/P6 kapsamındadır. Ekosistem ekranı gizli alıcı verisini okumaz, hesap token'ını taşımaz ve form göndermez.


## Son doğrulanmış durum — 19 Ekim 2026

**Web: %70 → %77. Uygulama: %65 → %72.** P1 ve P5 kapandı; puanlar canlı kanıtla kazanıldı. P5 bağımsız teknik iş olduğu için P2–P4'ün dış veri bekleyişi sırasında tamamlandı.

- [Canlı iki yönlü ekosistem testi](https://github.com/mehmetozan-5858/global-broker-ai/actions/runs/39319153315): 390px ve 1280px; dört alan korunuyor, inceleme öncesi forma uygulanmıyor, başvuru/ödeme gönderilmiyor; portal ve yönetici arayüzü girişleri çalışıyor.
- Üretim: Global Broker `e30732f`, AI Visibility `4572551`, ikisi de READY. Doğrulanmış Broker adresi: https://global-broker-opal.vercel.app/.
- Önemli üretim düzeltmesi: Python giriş noktası özel oda API'sinden mevcut uygulama yönlendiricisine alındı. Genel HTML/asset istekleri 200; kimliksiz özel oda/yönetici API istekleri 401 kalıyor. 395 Python testi geçti.
- Yeni kaynak taramasında 80 kayıt, görünen 100 araştırma görevinde eksik fırsat kimliği 0. Tam çekirdek dosya 1; gerçek fiyatı hazır dosya 0. Bu sayılar teslimat yüzdesi değildir.
- P2 kısmi; P3/P4 gerçek tedarikçi/teklif/navlun kanıtı bekliyor. P6 gerçek kurtarma kanalları, P7 ödeme/hukuk/iletişim/domain, P8 gerçek müşteri kabulü bekliyor. Otomatik test müşteri kabulü yerine sayılmadı; production launch gate kapalı.
