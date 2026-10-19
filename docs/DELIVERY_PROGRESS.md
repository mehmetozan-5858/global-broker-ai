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
