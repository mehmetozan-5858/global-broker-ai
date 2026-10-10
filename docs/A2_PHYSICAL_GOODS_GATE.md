# A2 — Fiziksel Mal / Hizmet Ayrımı

Global Broker ana ticari fırsat akışına yalnızca fiziksel ürün alımı olduğu kanıtlanan kayıtlar girebilir.

## Kararlar
- `goods_candidate`: ana araştırma zincirine girebilir. İhracat, yabancı tedarikçi uygunluğu ve ticari şartlar yine ayrıca doğrulanır.
- `review_mixed`: ürün + kurulum, mühendislik, eğitim, bakım, destek veya başka hizmet unsuru var. İnsan incelemesi olmadan ana fırsat değildir.
- `review_unknown`: fiziksel mal alımı kanıtlanamadı. Ana fırsat değildir.
- `exclude_service`: hizmet, danışmanlık, personel veya yapım işi. Dışarıda.
- `exclude_non_physical`: yazılım, SaaS, bulut veya dijital abonelik ağırlıklı. Dışarıda.

## Kaynak önceliği
Resmî kaynak `services/works/consulting` diyorsa başlıktaki `equipment/material` kelimesi kaydı mal alımına çeviremez. Resmî kaynak `goods/supplies` diyorsa bile kurulum, mühendislik, bakım veya destek gibi karma sinyal varsa kayıt incelemeye alınır.

## Pipeline kapısı
`src.physical_goods_gate` broker ve Çin kaynakları toplandıktan sonra, enrichment/tedarikçi/şartname/fiyat/risk araştırmasından **önce** çalışır. Böylece pahalı ve zaman alan araştırma sadece fiziksel mal adaylarına harcanır.

Shadow Mode devam eder; bu sınıflandırma teklif gönderme, alıcı uygunluğu veya ihracat izni anlamına gelmez.
