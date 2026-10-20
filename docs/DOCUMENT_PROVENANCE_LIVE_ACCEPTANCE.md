# Belge kanıtı — üretim doğrulaması

PR #121: 478 Python ve 16 JavaScript testi, 390px/1280px üretim tarayıcı kontrolleri, mobil yayın ve kaynak taraması geçti. Üretim READY: 400399039e6c0729f5d3a1603b775cf679669998.

Tarama: https://github.com/mehmetozan-5858/global-broker-ai/actions/runs/39389649771

66 kayıt, 16 resmî belge bağlantılı kayıt, 10 okunan kaynak sayfası, 2 fırsatta 4 PDF eki. 5 temel dosya, 11 ilan bütçesi, 0 gerçek fiyat hazır kayıt. Özel senkronizasyon 66 kayıt ile geçti; yayımlama gizlilik kapısı geçti. Körfez canlı kaynak kapsamı bu taramada yeniden doğrulandı; bu bir önceki taramanın kesintisini geçmişe dönük doğrulamaz.

Şartname analizinin v4 sayımı sayfa ve eki ayrı tutuyor. Toplam parsed_count tek başına PDF kabulü değildir. Uzantısız PDF, keşfedilen ek, bir iyi/bir başarısız ek, HTML döndüren PDF adresi ve uzun portalın PDF metnini bastırması testlerle kapsandı. Yönetici ekranında da sayfa/ek/bekleyen ek ayrı gösterilir; gerçekten okunan dinamik PDF bağlantısı önceliklidir. Bu görünüm bir Node render regresyonuyla doğrulandı; toplam 479 Python testi yerelde geçti.

Tam şartname uygunluğu, tam kaynak dosyası ve ticari kabul kapıları açık kalır. Sabit ilerleme web %77 / uygulama %72; ek puan yok.
