# Özel teklif incelemesi ve analiz önizlemesi

Yönetici+AAL2 oturumu, kayıtlı teklif için gerekçeli `accepted_for_analysis`, `needs_information` veya `rejected` kararı ekler. Analize kabulde belge, taraf/kapsam ve tutar/miktar/para birimi kontrolleri açıkça işaretlenmelidir. Süresi geçmiş veya güncel fırsatı bulunmayan kanıt kabul edilmez. Ek bilgi kararı yalnız iç kayıt oluşturur; e-posta/mesaj göndermez.

Kararlar özel tabloda eklemeli saklanır. Özgün teklif değiştirilmez. İstemci son gördüğü karar sürümünü gönderir; eski sürüm yeni kararı ezemez. Aynı istek kimliğiyle tekrar tek olay oluşturur. Tabloya API rollerinin doğrudan erişimi yoktur. Public RPC sarmalayıcıları SECURITY INVOKER; özel helperlar rol+auth.uid+AAL2 kapısını uygular.

`/api/quote_analysis` yalnız kullanıcının bearer oturumuyla SQL bağlamını okur. Son kararı analize kabul olan kanıtlar için mevcut commercial_evidence_acceptance ve price_margin_gate motorlarını geçici kopyada çalıştırır. Önceki fiyat alanları yeniden kullanılmaz. Aynı taraf için birden fazla güncel kabul edilmiş teklif varsa ilk kayıt seçilmez; belirsizlik bildirilir. Alıcı veya tedarikçi teklifi süresi dolmuşsa dışlanır. Şartnameye uygun tedarikçi, fiyat metadatası, miktar/birim ve para birimi kapıları korunur.

Önizleme kaynak taramasını veya özel fırsat kaydını güncellemez, ticari onay vermez, net kâr/ödeme/komisyon hakkı oluşturmaz. Navlun, risk ve ticari kabul ayrıdır. Gerçek kanıt olmadan P4 tamamlanmaz.

İlerleme ekranı sabit paket yüzdesini korur; kalan yol haritasındaki yazılım adımlarını ve gerçek veri/kullanım kabulünü ayrı sayar. Bu alt adım sayımı tüm uygulama için yeni bir yüzde değildir. Tamamlanan alt adımlar test, üretim dağıtımı ve canlı doğrulama kanıtı gerektirir; özel kanıt metinleri public özete aktarılmaz.

Doğrulama: geri alınan SQL yetki/tekrar/sürüm/iptal/son-karar testleri; Python analizi ve auth aktarımı; yakalanmış RPC/API kullanan mobil/masaüstü/WebKit arayüz testleri. Gerçek teklif veya inceleme kararı test amacıyla kalıcı bırakılmaz.

## Freight evidence

The same private MFA-protected inbox also accepts `party=freight`. Its amount is
always `amount_basis=shipment_total`, the entire shipment cost rather than a unit
price. The additional required fields are origin, destination, Incoterm and
transport mode. Quantity and price unit describe the cargo covered by the quote.
Supplier and buyer payloads retain their original ten-field contract.

Freight records use the same immutable intake, idempotent request IDs, append-only
review decisions and revision conflict checks. Only one current accepted freight
quote may enter an analysis. Quantity must cover the requested cargo, its unit
must match the supplier quote, and currency must match without an assumed FX
conversion. Missing, expired, revoked or ambiguous evidence blocks the calculation.

The analysis can show a goods-plus-freight subtotal. This excludes duty, tax,
insurance, fees, financing and FX; it never establishes landed cost, net profit,
commercial approval or authority to contact a carrier. No payment or shipment is
initiated. SQL authorization fixtures are rolled back; browser fixtures intercept
all quotation writes.
