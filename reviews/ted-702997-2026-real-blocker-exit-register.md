# TED 702997-2026 — gerçek engeller / kapanış koşulları (14 Kasım 2026)

**Kapsam:** Yalnızca Global Broker taslak PR #222 teknik incelemesi. Bu kayıt bir tedarik teklifi, ticari yetki veya gönderilmiş açıklama talebi değildir.

## Güncel kaynak delili

- Resmi E-ZAK ihale kaydı: `https://zakazky.krajbezkorupce.cz/contract_display_47078.html`.
- Düzeltilmiş teknik DOCX E-ZAK belgesi: `document_254114`, 27.10.2026; SHA-256 `ec1501d66872990cb18d0e27be2f492d8911b09d28665955ec28f757434a161e`. Bu *belirli belgenin kaynak kimliği* teyitli; **son/tek bağlayıcı revizyonun bu olduğu teyitli değil**.
- TED orijinal `702997-2026`, düzeltme `746528-2026`, değişiklik ilanının yayını 28.10.2026. Düzeltme açıklamasında *Vysvětlení ZD č.1* sonucu teknik şartnamenin değiştiği ve sürenin uzatıldığı belirtilir.
- Düzeltilmiş ilan bakımından görülen teklif son günü **27.11.2026 09:00 Çekya saati**; eski ihale sayfası/önbellek 11.11 tarihini gösterebilir. Son geçerli resmi son gün ve açıklama başvuru penceresi ayrıca yetkili makam kayıtlarıyla kontrol edilmeli.
- 14.11.2026 web araştırmasında hacim çelişkilerini gideren daha geç tarihli, bağlayıcı açıklama **bulunamadı**. Bu, yeni açıklama kesinlikle yoktur anlamına gelmez. Arama sonuçları resmi açıklamaların tam envanteri değildir.

## Kapatılabilecek ve kapatılamayan işler

| Engel | Durum | Somut kapatma koşulu | Kanıt sahibi / gerekli taraf |
| --- | --- | --- | --- |
| 27.10 tarihli teknik DOCX'in kaynak kimliği ve SHA-256 değeri | **KAPALI: bu tek dosya için** | Resmi E-ZAK kaydı ve dosya hash eşleşmesi | Resmi kaynak ve hash denetimi |
| Slavkov u Brna 3 × 15.000 L ve max Ø2.450 / H3.000 mm | **CRITICAL / OPEN** | İdarenin resmi yazılı hacim/ölçü açıklaması veya geçerli düzeltmesi; ardından hacim/dış geometri bağımsız mühendis teyidi | İhale idaresi + bağımsız teknik uzman |
| Veselí nad Moravou 2 × 15.000 L, çizim Ø2.400 / H3.000; şartname H4.400 | **HIGH / OPEN** | Revize bağlayıcı çizim veya çizimin konumuna ilişkin resmi açıklama; ardından gerçek kullanılabilir hacim/yerleşim doğrulaması | İhale idaresi + teknik uzman |
| Son geçerli revizyon, açıklamalar ve 10 ekin tamlığı | **HIGH / OPEN** | Resmi ilan + düzeltmeler + Annex 8 sürümü için benzersiz sürüm zinciri, sayfa/dosya tarihleri, hash ve eksiksizlik incelemesi | Resmi E-ZAK/TED + yetkili inceleyen |
| 27 tankın kullanılabilir hacmi | **HIGH / OPEN** | Her model ve saha için üretici sertifikalı kapasite/eğim/dolum seviyesi, model/seri bağlantısı | Üretici + bağımsız mühendis |
| 9 saha pompa, filtre, vanalar, 2 karıştırıcı ve tesis bağlantıları | **HIGH / OPEN** | Madde bazlı ekipman datasheet'leri, tesis/site fit onayı, bağlantı ve tesisat incelemesi | Üretici/kurulum yüklenicisi + teknik inceleme |
| XLSX 13 formül / PDF 12 sayfa / 27 tank çizim kapsaması | **KISMİ: inceleme/test kanıtı** | Formül denetimi ve çizim indekslemesi mevcut; bunlar gerçek yüklenici uygunluğu veya nihai teknik kabul değildir | Bağımsız kanıt incelemesi |
| exact-head + Vercel + müşteri/ödeme/tedarikçi yetkileri | **OPEN / AYRI** | Aynı commit'te yetkili CI/live ölçüm, güvenlik ve müşteri kabul kanıtları; bağımsız ticari/yayın onayı | Ürün sahibi / ilgili canlı sistemler |

## En küçük gerçek sonraki işlem

1. `reviews/ted-702997-2026-clarification-draft-not-sent.md` içindeki Çekçe taslak ihale sürecinde yetkili Çekçe teknik/hukuki kişi tarafından kontrol edilir.
2. İhale idaresine açıklama talebi ancak **yetkili kişi** ve usule uygun E-ZAK kanalı üzerinden, süresi teyit edilerek iletilebilir. **Buradan mesaj gönderilmedi**.
3. Gelen resmi yanıtın tarih, sürüm, dosya, SHA-256 ve kapsam eşleşmesi bağımsız doğrulanır; ardından 12-saha 27-tank denetimi yeniden çalıştırılır.
4. Bu kapanış yapılmadan `ted_702997_2026_unresolved_technical_capacity_conflict` engeli kaldırılamaz.

## Sabit güvenlik sınırları

`technical_approval=false`, `commercial_approval=false`, `quarantine_release_authorized=false`, `deployment_approval=false`, `supplier_outreach=false`. PR #222 taslak, main ve production değişmeden kalır. Liste bir tamamlanma yüzdesi değildir.
