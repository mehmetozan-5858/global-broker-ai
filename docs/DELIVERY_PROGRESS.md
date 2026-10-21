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

## Canlı takip ekranı

`/progress` veya `/web/progress.html` üzerinden web ve uygulama yüzdeleri, açık/tamamlanan paket filtresi ve her paketin kabul şartları okunabilir. Kaynak tek ilerleme kaydıdır; ödeme/hesap/fırsat verileri API yanıtına girmez. Mobil statik yayın da aynı kayıttan sınırlı JSON üretir. Veri erişilemez veya kayıt geçersizse eski yüzde güncelmiş gibi gösterilmez.

419 Python testi ve 390px/1280px ilerleme ekranı testi başarılı. Açılış raporundaki ödeme/hukuk/işletme grubunun gizlilik süzgecinde yanlışlıkla silinmesi, özel alanları açmadan grup anahtarı değiştirilerek düzeltildi.

[Ürün/tedarik üretim taraması](https://github.com/mehmetozan-5858/global-broker-ai/actions/runs/39323642846): 73 kayıt, 73 kaynak ürün ayrıntısı, bir gerçek fırsatta 2 üretici kabiliyeti adayı. Tam şartname, teklif ve ticari kapılar açık sayılmadı. [Ekosistem ve üretici ekran testleri](https://github.com/mehmetozan-5858/global-broker-ai/actions/runs/39323642735) ve mobil yayın başarılı.

## Hesap kurtarma ve özel yönetici dosyaları — 20 Ekim 2026

Şifre sıfırlama isteği sonrası eksik olan yeni şifre kaydetme dönüşü tamamlandı. Doğrulama bağlantısındaki erişim/yenileme belirteçleri ağ isteğinden önce URLden temizlenir. Oturum Auth sunucusunda doğrulanmadan saklanmaz; şifre tekrarı ve en az 12 karakter kontrol edilir. Geçersiz bağlantı, geçersiz oturum, MFA hatası ve ağ hatası başarıya çevrilmez. TOTP doğrulamasından sonra yalnız izin verilen `/account` veya `/app` hedefine dönülür. Gerçek e-posta gönderimi ve gerçek parola değişikliği test edilmedi; redirect allowlist ve e-posta teslim kabulü hâlâ gerekli.

Yönetici API maskelenmiş dosyayı tam dosya olarak sunuyordu. Kaynak artık özel veritabanındaki gerçek fırsat satırlarıdır. Anonim kullanıcıya kapalı public invoker RPC, ayrı özel şemadaki sınırlı helper üzerinden rol+AAL2 kontrolüyle çalışır; ham tablo erişimi verilmez, servis anahtarı tarayıcıya veya API koduna eklenmez. Özel kaynak yoksa 503 döner, maskeli dosya tam dosya yerine geçmez. Yerel dosya yalnız toplu telemetri için kullanılır.

Veritabanında gerçek özel satırların erişim kontrolü SQL rol/claim simülasyonuyla doğrulandı; bu gerçek tarayıcı giriş kabulü değildir. Doğru admin+AAL2 özel alanları okudu; AAL1, başka kullanıcı ve anonim reddedildi. 423 Python testi, 4 Node sözleşme testi ve 390px/1280px parola yenileme tarayıcı testleri geçti. Testler bütün Auth isteklerini yakalar; gerçek hesaba e-posta göndermez veya şifre değiştirmez.

Canlı ön kontrol: telefon doğrulaması ve çift kurtarma kaydı bulunmuyor; gerçek tedarikçi fiyatı/finansal uygunluk kaydı yok; Broker projesine yalnız doğrulanmış Vercel alt alan adı bağlı. P2/P6 teknik olarak ilerledi; tam kabul olmadığı için sabit %77/%72 puanları değişmedi.

## Özel alan adı tamamlandı — 20 Ekim 2026

https://broker.aivisibilityworks.com Global Broker üretim projesine eklendi ve Vercel tarafından doğrulandı. Mevcut Cloudflare DNS çözümlemesiyle HTTPS üzerinden Broker ana sayfası, ilerleme ekranı ve ilerleme API'si 200 döndü; AI Visibility ana sitesi de 200 kaldı. Alan adı satın alınmadı, DNS/nameserver veya e-posta kayıtları değiştirilmedi. Önceki teknik adres çalışmaya devam eder; mevcut hesapların origin tabanlı oturumunu korumak için yönlendirme eklenmedi.

Her kaynak taraması alan adının HTTPS ana sayfasını, sağlık uç noktasını ve kimliksiz yönetici erişiminin 401 kalmasını tekrar doğrular. Başarısız okumada domain açılış kapısı false kalır. 426 Python testi geçti. P7 içindeki özel alan adı koşulu tamamlandı; ödeme/hukuk/işletme iletişimi kanıtı olmadığı için paketin tamamına puan verilmedi.

Hesap/özel dosya düzeltmesi PR #106 üretimde: CI, mobil yayın ve şifre yenileme dahil tarayıcı kontrolleri başarılı. Gerçek parola değişikliği, SMS veya ödeme işlemi yapılmadı.

## İletişim ve tutarlı kanıt kapıları — 20 Ekim 2026

Web %77, uygulama %72. İletişim formundan mevcut özel yönetici e-postasına tek sistem testi kabul edildi; aynı kimlikle tekrar gönderim ikinci e-posta oluşturmadı. Canlı kanıt: https://github.com/mehmetozan-5858/global-broker-ai/actions/runs/39372843723 . Bu gerçek müşteri kabulü değildir.

Yönetici uygulamasındaki %70 doluluk eşiği artık ticari hazırlık yerine geçmez. Sunucunun her kayıtta yeniden hesapladığı temel kaynak kapısı, kalem seçimi, güncel son tarih, bağımsız alıcı doğrulaması, tam şartname tedarikçisi, geçerli teklif, alıcı fiyatı, landed cost ve risk kapıları ortak görünümde kullanılır. CEO sıralaması, günlük görev, fırsat kartı, hazır sayacı ve güvenli işlem kartı aynı kanıtlara bakar. Tam temel dosya yalnız “Kaynak dosyası tam” olarak adlandırılır; dış işlem yetkisi doğurmaz. Eksik veya eski biçimli kanıt hazır kabul edilmez.

Kalan paketlerin dış kanıtları değişmedi: kaynakta eksik fırsat alanları; tam şartname tedarikçi teyidi; gerçek geçerli teklif/navlun/risk; telefon/SMS kurtarma; bireysel işletme modelinin hukuki ve ödeme kabulü; gerçek müşteri testi. Bunlar otomatik testle tamamlanmış sayılamaz.

## Açık paket ile sıradaki yazılım işi — 21 Ekim 2026

Sabit paket puanları değiştirilmedi. P2'nin eksik kaynak/kabul koşulları,
P3/P4'ün gerçek teknik teyit ve ticari belge koşulları ayrı kalır.
`next_package` ilk açık paketi, `next_software_step` ise engelli veya gerçek
kabul bekleyen adımları atlayarak sıradaki açık yazılım adımını gösterir.
Bu ayrım bitmiş adımlara yeni puan vermez, kabul koşullarını kaldırmaz.
Mevcut kayıtta 13 yazılım adımının 12'si tamamlanmış; açık yazılım adımı
P7 ödeme sağlayıcısı / tahsilat / fatura entegrasyonudur. Bu sayım bütün
uygulamanın tamamlanma yüzdesi değildir. Paddle itirazı yanıt bekliyor;
bu kayıt yeni mesaj, şifre değişikliği veya gerçek ödeme başlatmaz.


## 21 October 2026 — six-heading closeout review

The six remaining acceptance headings were reviewed together against read-only
production aggregates and the latest successful source/browser runs. See
[the consolidated closure queue](LAUNCH_BLOCKERS.md#consolidated-acceptance-review--21-october-2026)
for exact evidence and responsible next actions. There are 67 active records,
zero verified suppliers, zero price-ready records, zero submitted/reviewed
quotes and zero Broker sandbox receipts. Dual recovery and real customer/legal
acceptance remain unverified. No point or gate changes: web 77%, app 72%.
No new regression run is necessary for this documentation-only review.
