# Proje Yönetimi

[![CI](https://github.com/Alibehram11/Project_Management/actions/workflows/ci.yml/badge.svg)](https://github.com/Alibehram11/Project_Management/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-black.svg)](LICENSE)

Ekiplerin projeleri, görevleri, teslimleri, takvimi ve öğrenci belgelerini tek
ekrandan yönetebilmesi için geliştirilmiş, SQLite destekli bir web uygulaması.
Uygulama standart Python WSGI arayüzüyle çalışır ve PythonAnywhere üzerinde
harici backend paketi olmadan yayımlanabilir.

> [!WARNING]
> Bu depo eğitim ve test amacıyla sekiz açık metin demo şifresi içerir. Demo
> hesaplarını gerçek kullanıcı verileriyle veya internete açık üretim ortamında
> kullanmayın. Üretim kullanımı öncesinde şifre hashing ve kalıcı session
> altyapısına geçilmelidir.

## Öne Çıkanlar

- E-posta ve şifre ile giriş, kayıt ve giriş sonrası proje seçimi
- Ana admin, proje admini, ekip kaptanı ve üye yetkileri
- Projeye kullanıcı ekleme, görev atama, checklist, yorum ve dosya teslimi
- Görev onayı, düzeltme talebi, takvim, CRM, ekip akışı ve rapor ekranları
- Web üzerinden doldurulup `.docx` olarak indirilebilen 10 Word şablonu
- Proje içinden erişilen Atölye envanteri ve kullanıcıya özel talepler
- SQLite state, revision, snapshot, audit log ve kalıcı bildirim outbox kaydı
- Proje kapsamlı API yetkilendirmesi, CSRF, origin/host ve rate-limit kontrolleri
- Optimistic concurrency, soft delete, çöp kutusu ve veri bütünlüğü kuralları
- Görevlerin CSV ve PDF olarak dışa aktarılması

## Mimari

```text
Project_Management/
├── server.py                 # HTTP + WSGI API, SQLite ve güvenlik katmanı
├── advanced_rules.py         # Yetki, bütünlük, pagination ve export kuralları
├── app.js                    # Tarayıcı uygulaması ve kullanıcı iş akışları
├── index.html
├── styles.css
├── security_tests.py         # 53 güvenlik/regresyon senaryosu
├── advanced_tests.py         # 30 ileri seviye iş kuralı ve yük senaryosu
├── wsgi.py                   # PythonAnywhere WSGI giriş noktası
├── integrations/atolye/      # Atölye kaynak entegrasyonu
└── proje_yonetimi_ogrenci_belgeleri_word/  # 10 DOCX şablonu
```

Frontend, kullanıcı deneyimi için tarayıcı depolamasını kullanır. Backend açıkken
durum SQLite'a revision numarasıyla atomik olarak yazılır. Sunucu, gönderilen
state verisini kullanıcıya ait proje kapsamıyla birleştirir; arayüzde saklanan
bir düğmeye veya istemcinin bildirdiği role güvenmez.

## Hızlı Başlangıç

Gereksinim: Python 3.10 veya üzeri. Önerilen sürüm Python 3.12'dir.

```powershell
git clone https://github.com/Alibehram11/Project_Management.git
cd Project_Management
python server.py --check
python server.py
```

Ardından `http://127.0.0.1:8765` adresini açın.

Ana uygulama yalnızca Python standart kütüphanesini kullanır. Bu nedenle
`requirements.txt` bilerek boş tutulmuştur. Atölye kaynak uygulamasını bağımsız
çalıştırmak isterseniz kendi `integrations/atolye/requirements.txt` dosyasını
kullanın.

## Demo Hesapları

Tüm demo hesaplarının şifresi `123456` değeridir.

| Rol | E-posta |
| --- | --- |
| Ana admin | `admin@proje.local` |
| Yazılım kaptanı | `yazilim@proje.local` |
| Yazılım üyesi | `yazilim2@proje.local` |
| Tasarım üyesi | `tasarim@proje.local` |
| Mekanik kaptanı | `mekanik@proje.local` |
| Elektronik üyesi | `elektronik@proje.local` |
| Mentor admin | `mentor@proje.local` |
| Atölye admin | `atolye@proje.local` |

## Testler

Tam doğrulama:

```powershell
python security_tests.py
python advanced_tests.py
python server.py --check
python -m py_compile server.py advanced_rules.py security_tests.py advanced_tests.py wsgi.py
```

Beklenen sonuç:

- Güvenlik/regresyon testleri: `53/53 PASS`
- İleri seviye senaryolar: `30/30 PASS`
- Word şablon kontrolü: `10/10`

Tarayıcı iş akışlarını kontrol etmek için uygulamayı
`http://127.0.0.1:8765/?selftest=1` adresinde açabilirsiniz.

## Güvenlik Modeli

- Bearer session ve session başına CSRF token
- Her istekte güncel kullanıcı ve proje üyeliği doğrulaması
- Sistem admini ve proje admini işlemlerinin ayrılması
- IDOR'a karşı kullanıcıya özel state filtreleme
- Revision tabanlı eşzamanlı güncelleme kontrolü
- JSON boyut, derinlik, anahtar ve kontrol karakteri sınırları
- DOCX makro, dış ilişki, XML/DTD, traversal ve ZIP bombası kontrolleri
- SQL sorgularında parametre kullanımı ve güvenli hata yanıtları
- Thread-safe rate limiter ve tekrar denenebilir SQLite outbox

Güvenlik açığı bildirimleri için [SECURITY.md](SECURITY.md) dosyasını inceleyin.

## PythonAnywhere

Elle yükleme ve WSGI kurulumu için [PYTHONANYWHERE.md](PYTHONANYWHERE.md)
rehberini kullanın. Temel WSGI yapılandırması:

```python
import sys

path = "/home/KULLANICI_ADIN/Project_Management"
if path not in sys.path:
    sys.path.insert(0, path)

from server import application
```

Özel alan adı kullanıyorsanız `PROJECT_ALLOWED_HOSTS` ortam değişkenine alan
adınızı ekleyin.

## Katkı

Katkı adımları ve zorunlu kontroller için [CONTRIBUTING.md](CONTRIBUTING.md)
dosyasına bakın. Atölye entegrasyonu ayrı kaynak yapısını korur; ana uygulama
değişiklikleri entegrasyon koduyla gereksiz yere birleştirilmemelidir.

## Lisans

Bu proje [MIT Lisansı](LICENSE) ile yayımlanır.
