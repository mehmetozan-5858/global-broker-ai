# Global Broker — Alan Adı ve Güvenli Yayına Alma

## Alan adı seçimi (henüz satın alınmadı)
Tercih: kısa, markayla uyumlu bir **.com** alan adı. Örnekler yalnızca isim fikridir; kullanılabilirlik, marka hakkı ve sahiplik doğrulanmadan satın alınmış veya uygun sayılmamalıdır.

## GitHub Pages özel alan adı
1. Seçilen alan adını bir kayıt kuruluşundan satın alın; hesap ve yenileme yönetimi işletme sahibinde olsun.
2. GitHub repository **Settings → Pages → Custom domain** alanına alan adını girip kaydedin.
3. DNS sağlayıcısında `www` için `CNAME` kaydını `mehmetozan-5858.github.io` adresine yönlendirin. Repo adı veya https:// eklemeyin.
4. Kök alan adı da kullanılacaksa GitHub Pages belgelerindeki `A`/`ALIAS` kayıtlarını ekleyin.
5. DNS yayılımı ve sertifika tamamlandıktan sonra **Enforce HTTPS** seçeneğini açın; hem www hem kök alan adı yönlendirmesini test edin.
6. GitHub Pages, GitHub Actions üzerinden yayımlandığından özel alan adı Pages ayarlarından yapılır; bu aşamada rastgele `CNAME` dosyası eklemeyin.

Kaynak: https://docs.github.com/en/pages/configuring-a-custom-domain-for-your-github-pages-site/managing-a-custom-domain-for-your-github-pages-site

## Yayına alma kapıları (henüz tamamlanmış sayılmaz)
- [ ] Gerçek alan adı tescili, marka kontrolü ve HTTPS testi
- [ ] Ticari unvan, iletişim kanalları, açık kimlik ve destek süreci
- [ ] KVKK/gizlilik, çerez ve kullanım şartları: gerçek iş modeline göre hukuk kontrolü
- [ ] Sunucu tarafında kimlik doğrulama, oturum yönetimi ve rol bazlı yetkilendirme
- [ ] Yönetici paneli ve hassas verileri herkese açık GitHub Pages statik dağıtımından çıkarma
- [ ] Gerçek belge okuma, kaynak kanıtı ve uluslararası fiziksel ürün uygunluğu
- [ ] Ödeme/komisyon sözleşmeleri, vergisel uygunluk, ödeme sağlayıcısı
- [ ] Hata izleme, yedekleme, mobil test, erişilebilirlik ve performans testleri

**Uyarı:** `noindex` yalnızca arama motorlarına bir yönergedir, güvenlik kontrolü değildir. `dashboard.html` ve `admin.html` herkese açık GitHub Pages üzerinden erişilebilir; bunlara gizli müşteri verisi veya anahtar konulmamalıdır.
