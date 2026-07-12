# Güvenlik Politikası

## Desteklenen Sürüm

Aktif olarak yalnızca varsayılan dalın en güncel sürümü desteklenir. Eski
commit'ler ve kullanıcı tarafından değiştirilmiş dağıtımlar için güvenlik
güncellemesi garantisi verilmez.

## Açık Bildirme

Bir güvenlik açığı bulduysanız ayrıntıları herkese açık issue içinde paylaşmayın.
GitHub deposundaki **Security > Report a vulnerability** alanını kullanın. Bu
alan kullanılamıyorsa depo sahibine yalnızca açığın etkisini belirten kısa bir
mesaj gönderin ve teknik ayrıntıları güvenli kanal kurulana kadar paylaşmayın.

Bildirimde mümkünse şunlara yer verin:

- Etkilenen endpoint veya iş akışı
- Tekrarlanabilir adımlar
- Beklenen ve gerçekleşen davranış
- Yetki seviyesi ve olası veri etkisi
- Varsa zararsız bir proof of concept

## Yanıt Süreci

Rapor alındığında önce tekrar üretme ve etki değerlendirmesi yapılır. Doğrulanan
açık için düzeltme, regresyon testi ve güvenli yayın hazırlanır. Açık kamuya
duyurulacaksa zamanlama raporlayan kişiyle koordine edilir.

## Üretim Uyarısı

Depodaki demo hesapları açık metin `123456` şifresini kullanır. Bu tercih test
senaryoları içindir ve üretim güvenliği sağlamaz. İnternete açık gerçek kullanım
öncesinde en az aşağıdaki değişiklikler yapılmalıdır:

- Argon2id, scrypt veya bcrypt ile şifre hashing
- Kalıcı ve iptal edilebilir session deposu
- Güçlü, ortam değişkeni tabanlı secret yönetimi
- TLS terminasyonu ve güvenilir reverse proxy yapılandırması
- Yedekleme, geri yükleme ve güvenlik logu saklama politikası
