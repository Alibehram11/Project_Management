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

Demo hesapları `123456` parolasını kullanır ancak parola değeri kaynakta veya
SQLite state içinde tutulmaz; PBKDF2-HMAC-SHA256 hash ve kullanıcıya özel salt
kullanılır. Üretimde demo parolalarını değiştirin. Ayrıca:

- Kalıcı ve iptal edilebilir session deposu
- Güçlü, ortam değişkeni tabanlı secret yönetimi
- TLS terminasyonu ve güvenilir reverse proxy yapılandırması
- Yedekleme, geri yükleme ve güvenlik logu saklama politikası

## English

# Security Policy

## Supported Versions

Only the latest version on the default branch is actively supported. Security
updates are not guaranteed for old commits or modified distributions.

## Reporting a Vulnerability

Do not disclose vulnerability details in a public issue. Use **Security > Report
a vulnerability** in the GitHub repository. If that channel is unavailable,
send the owner a short impact summary and wait for a secure channel before
sharing technical details.

Include the following where possible:

- The affected endpoint or workflow
- Reproducible steps
- Expected and actual behavior
- Required permission level and possible data impact
- A harmless proof of concept, if available

## Response Process

Reports are reproduced and assessed first. Confirmed vulnerabilities receive a
fix, regression test and controlled release. Public disclosure timing is
coordinated with the reporter.

## Production Notes

Demo accounts use `123456`, but the password value is not stored in plaintext in
source code or SQLite state. PBKDF2-HMAC-SHA256 with a per-user salt is used.
Change demo passwords before deploying to PythonAnywhere or any public environment.
Production deployments should also use persistent revocable sessions, environment-
based secrets, trusted TLS termination, backups and a security-log retention policy.
