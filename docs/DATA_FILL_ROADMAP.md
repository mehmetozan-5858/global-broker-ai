# Global Broker veri doldurma yol haritası

Amaç: yeni ekran eklemek yerine mevcut fırsat havuzunu gerçek ticari verilerle doldurmak ve her kaydı iş yapılabilir seviyeye taşımak.

## Öncelik sırası

1. Çekirdek fırsat alanlarını tamamla
   - alıcı kimliği
   - ürün / teknik tanım
   - miktar veya bütçe
   - son tarih
   - ülke / şehir
   - resmî kaynak / belge

2. Alıcı doğrulama
   - kurum / şirket adı
   - resmî web veya ihale kaydı
   - iletişim kanalının kaynağı
   - doğrulama durumu

3. Tedarikçi eşleştirme
   - en az 1 doğrulanmış aday
   - ürün uygunluğu
   - ülke / ihracat kabiliyeti
   - kanıt bağlantısı

4. Gerçek fiyat / marj girdileri
   - tedarikçi teklifi
   - para birimi
   - birim fiyat
   - geçerlilik tarihi
   - tahmini satış fiyatı / komisyon modeli

5. Lojistik
   - çıkış ülkesi
   - varış noktası
   - Incoterm
   - navlun / landed cost

6. Risk
   - alıcı riski
   - tedarikçi riski
   - ülke / yaptırım / ödeme riski
   - belge ve teslimat riski

7. Teklif / müzakere / sözleşme
   - yalnız önceki kapılar gerçek verilerle tamamlandıktan sonra

8. Yönetici görünürlüğü
   - kaç kayıt tamamlandı
   - kaç kayıt hangi alan nedeniyle bekliyor
   - sıradaki ajan / görev
   - ticarete uygun aday sayısı

## Çalışma kuralı

- Kaynakta olmayan veri üretilmez.
- Eksik alanlar fırsat gibi gösterilmez; araştırma kuyruğunda tutulur.
- En hızlı kapanabilir kayıtlar önce tamamlanır.
- Resmî kaynaklı ve kritik alanlarının çoğu dolu kayıtlar öncelik kazanır.
- Tedarikçi, fiyat, lojistik ve risk verisi gerçek kanıt olmadan hazır sayılmaz.
- Dış mesaj, teklif, sözleşme veya para hareketi insan onayı olmadan yapılmaz.

## İlk uygulama

İlk teknik adım: ham fırsatların eksik çekirdek alanlarını sayan, kayıtları önceliklendiren ve her kaydı doğru araştırma ajanına yönlendiren `data_completion_queue` katmanını ana pipeline'a eklemek.
