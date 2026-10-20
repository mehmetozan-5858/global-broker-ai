# TED Search kaynak alanları

TED Search isteğine resmî arama alanı listesindeki identifier-lot, estimated-value-lot ve estimated-value-cur-lot eklendi. Kaynak: https://docs.ted.europa.eu/ODS/latest/reuse/field-list.html (20 Ekim 2026).

Yalnız tek ve açık LOT kimliği ile tek pozitif tutar/para birimi kaynak ilan bütçesi olarak taşınır. Birden çok kalem, tutar veya para birimi toplanmaz, sıraları eşleştirilmez. Eksik/bozuk kalem kimliği XML veya insan incelemesiyle çözülene kadar kalem kapısı kapalıdır. Resmî ilan bağlantısı doğrulanmış biçimdeki yayın numarasından kurulur. Tekrarlanan aynı ISO tarih değerleri birleştirilmez; tek bir doğrulanabilir gün olarak normalleştirilir.

Bu değer tedarikçi teklifi, alış fiyatı, satış fiyatı, navlun veya kâr değildir. Alıcı doğrulaması ve dış işlem yetkisi doğurmaz. Kamuya yalnız tutar/para birimi gösterilir; kaynak bağlantısı ve alıcı kimliği özel dosyada kalır.

Yeni unittest vakaları; tek/çok kalem, eksik kimlik, negatif/geçersiz tutar, para birimi çelişkisi, tekrarlı tarih ve kamuya veri sınırını kapsar. Ayrı salt okunur TED Search Source Probe iş akışı gerçek resmî API sözleşmesini 25 ilanla sınar; günlük veya zamanlanmış görev eklemez ve ham kayıtları günlüğe yazmaz.
