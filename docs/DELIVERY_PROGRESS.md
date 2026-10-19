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

## Toplu tamamlama çalışması — 19 Ekim 2026

Web **%77 → %77**, uygulama **%72 → %72**. P2 üzerinde üç üretim düzeltmesi yapıldı; tüm kayıtlar için kabul tamamlanmadığından puan eklenmedi.

- PR #100: resmî TED XML/HTML belge okuma, kalem bazında miktar/bütçe/tarih, müşteriye güvenli ilan bütçesi. İlk gerçek taramada belge okunan kayıt 2→19, çekirdek dosya 1→2; 58 kalem ve 2 bütçe.
- PR #101: seçilmemiş çok kalemli ilanlarda çekirdek dosya, fiyat/marj ve ticari hazır kapıları kapatıldı.
- PR #102: kaynak kesintisinde yalnız aynı ilanın doğrulanmış temel alanlarını ilk doğrulama tarihiyle koruyan sınırlı önbellek. Yeni XML eski bilgiyi yeniler veya siler; teklifler/iletişim/raw belgeler önbelleğe girmez. İki gerçek kaynak bütçesi kesinti yeniden oynatımında korundu.
- 411 Python testi geçti. Müşteri ve yönetici ekranlarının tarih ve kalem uyarıları 390px/1280px tarayıcı kontrolünde geçti. Bu yeniden oynatım gerçek müşteri kabulü değildir.
- [Üretim ekosistem testi](https://github.com/mehmetozan-5858/global-broker-ai/actions/runs/39322312730) ve [mobil yayın kontrolü](https://github.com/mehmetozan-5858/global-broker-ai/actions/runs/39322312679) başarılı. Üretim sürümü `39fbf3a` READY.

P3/P4 gerçek tedarikçi, teklif ve navlun; P6 kurtarma kanalları; P7 ödeme/hukuk/işletme/domain; P8 gerçek müşteri kabulü kanıtı gerektiriyor. Bu dış koşullar kod yazılarak tamamlanmış sayılmaz.

[Son canlı kaynak taraması](https://github.com/mehmetozan-5858/global-broker-ai/actions/runs/39322312764) başarılı: 72 kayıt; XML/HTML erişimi sıfırken iki kaynak bütçesi önceki doğrulama tarihiyle korundu (`reused_notices=2`). Veri anlık görüntüsü `3f689f1`. Yönetici üst durum rozeti de seçilmemiş çok kalemli dosyayı hazır göstermez.

## Ürün ayrıntısı ve tedarik araştırması — ikinci toplu çalışma

Kaynak başlığındaki ayrıntılı ürün adı genel Türkçe kategori etiketinden ayrı korunur; arama ve müşteri kartı bu ayrıntıyı kullanır. 72 kayıtlık gerçek anlık görüntü üzerinde bütün mevcut fırsat kimlikleri korundu; 72 kaynak ürün başlığı kullanılabilir. Bilinen alıcı adı, URL, e-posta ve telefon ürün ayrıntısından çıkarılır.

TED `681487-2026` için iki gerçek üretici, resmî kimlik ve ürün kaynaklarıyla araştırıldı. Beş kamusal teknik gereksinim için kabiliyet eşleşmesi ve kalan boşluklar yönetici dosyasında gösterilir. Müşteri yalnız aday sayısını ve tam şartname/teklif onayının beklediğini görür. Kayıt yalnız tam TED numarası, kaynak ve ürün kapsamı eşleşirse uygulanır. Üçlü havuz, birebir şartname ve fiyat/marj onayı verilmez.

- FormFactor: https://www.formfactor.com/company/about-us/ ve https://www.formfactor.com/product/probe-systems/300-mm-systems/cm300xi-siph/
- Optik/DC/RF platform kanıtı: https://www.formfactor.com/product/probe-systems/autonomous-assistants/autonomous-silicon-photonics/
- ficonTEC: https://www.ficontec.com/imprint/ ve https://www.ficontec.com/capabilities/
- İlan referansı: https://ted.europa.eu/en/notice/-/detail/681487-2026 (kaynak akışında mevcut teknik açıklamalar; son erişimde TED robot denetimi görüldü).

417 Python testi ve 390px/1280px müşteri/yönetici tarayıcı kontrolleri geçti. P3 `blocked` durumundan `in_progress` durumuna geçti; eksiksiz şartname kabulü henüz yok. Web %77, uygulama %72; sabit puanlar değiştirilmedi.
