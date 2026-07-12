# Katkı Rehberi

## Geliştirme Ortamı

Python 3.10 veya üzeri gereklidir. Ana uygulama yalnızca standart kütüphaneyi
kullanır.

```powershell
python server.py --check
python server.py
```

## Değişiklik İlkeleri

- Mevcut veri modeli ve rol sınırlarıyla uyumlu küçük değişiklikler yapın.
- API yetkisini yalnızca arayüz görünürlüğüne bırakmayın.
- Kullanıcı girdisini HTML olarak basmayın; `textContent` benzeri güvenli yolları
  kullanın.
- Yeni state alanlarına boyut sınırı ve geriye uyumlu varsayılan ekleyin.
- DOCX ve dosya iş akışlarında uzantı kontrolünü tek başına yeterli saymayın.
- Demo şifre davranışını değiştiren PR'larda README ve güvenlik testlerini de
  güncelleyin.

## Zorunlu Kontroller

PR açmadan önce:

```powershell
python security_tests.py
python advanced_tests.py
python server.py --check
python -m py_compile server.py advanced_rules.py security_tests.py advanced_tests.py wsgi.py
```

Yeni hata düzeltmeleri uygun bir regresyon testi içermelidir. Testler birbirinin
veritabanı durumuna bağımlı olmamalıdır.

## Commit ve PR

Commit mesajını kısa ve emir kipinde yazın. PR açıklamasında değişikliğin nedeni,
kullanıcı etkisi, güvenlik etkisi ve çalıştırılan testleri belirtin. İlgisiz
refactor'ları aynı PR'a eklemeyin.
