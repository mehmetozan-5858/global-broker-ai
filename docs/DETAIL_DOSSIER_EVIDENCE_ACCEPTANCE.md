# Fırsat detayı — kanıta dayalı hazır olma

PR #125 ve #126 üretimde READY. Fırsat detayının bağımsız eski hazır olma ölçümü ortak kanıt kapılarıyla değiştirildi. Yalnız verified yazısı, aday sayısı veya dolu fiyat yeterli değildir. Kaynak türü, güncel tarih, temel dosya, şartname, tam eşleşen tedarikçi, geçerli teklif, marj, lojistik ve risk ayrı doğrulanır; yalnız iç insan incelemesine hazır olma gösterilir.

Detayda doğrulanmamış/süresi geçmiş teklifin fiyatı, türetilmiş satış fiyatı, brüt marj ve komisyonu geçerli tutar gibi görünmez. Ortak modül yoksa durum belirsiz kalır. unverified/not_verified/expired/invalid gibi olumsuz etiketler yeşil rozet üretemez.

486 Python ve 21 JavaScript testi geçti. Beş yeni JS render testi: eski durumlar, süresi geçmiş teklif, tam sentetik kanıt, eksik ortak modül ve olumsuz rozetler. Sentetik tam kanıt gerçek teklif kabulü değildir.

Canlı tarayıcı: https://github.com/mehmetozan-5858/global-broker-ai/actions/runs/39400978117

390px/1280px ekosistem, üretici kabiliyeti, iletişim, kurtarma, ilerleme ve ortak hazır olma kontrolleri geçti. Önceki tarayıcı fixture'ının atladığı TED normalizasyonu eklendi; sonuç ilanı beklentisi korunarak test geçti. Üretici kabiliyeti tam şartname onayı sayılmaz.

Web %77 / uygulama %72. Gerçek geçerli teklif ve tam şartname uygunluğu doğrulanmadığı için P3/P4 kapanmadı; dış iletişim, gerçek teklif veya işlem yapılmadı.
