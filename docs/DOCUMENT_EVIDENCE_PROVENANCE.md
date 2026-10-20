# Belge ve portal kanıtı ayrımı

Portal sayfası okuması PDF/DOCX/metin eki okumasından ayrı sayılır. Şartname analizi toplam parsed_count değerinden bir PDF okunduğu sonucunu çıkarmaz; dosya türü ve başarılı girişin URL kanıtı gerekir. Eski metadata bu kanıtı taşımıyorsa yeniden okuma gereklidir.

Sonradan bulunan ve uzantısız indirilen dosyalar özel şartname/dosya bağlantılarına ayrıştırıcı türüyle eklenir. Başarısız bir ek, başka bir PDF okundu diye tamamlanmış sayılmaz. Bir PDF adresinin HTML döndürmesi de PDF kabulü değildir.

Uzun portal sayfası kaynak metin sınırını doldursa bile sonradan bulunan teknik PDF metni önce korunur. Metin ve dosya boyutu sınırları değişmedi. Kamuya açık yayımlama ve özel depolama kuralları korunur.

478 Python testi; yeni durumlar portal/PDF ayrımı, keşfedilen ek, dinamik PDF, yönlendirme çoğaltmama, başarısız ek, eski kanıtsız metadata, PDF adresinde HTML ve uzun portal altında PDF metnini korumayı kapsar. Bu kontroller tam şartname uygunluğu, gerçek teklif veya müşteri kabulü yerine geçmez.
