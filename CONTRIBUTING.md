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
python security_advanced_tests.py
python endpoint_quality_tests.py
python server.py --check
python -m py_compile server.py advanced_rules.py security_tests.py advanced_tests.py security_advanced_tests.py endpoint_quality_tests.py wsgi.py
```

Yeni hata düzeltmeleri uygun bir regresyon testi içermelidir. Testler birbirinin
veritabanı durumuna bağımlı olmamalıdır.

## Commit ve PR

Commit mesajını kısa ve emir kipinde yazın. PR açıklamasında değişikliğin nedeni,
kullanıcı etkisi, güvenlik etkisi ve çalıştırılan testleri belirtin. İlgisiz
refactor'ları aynı PR'a eklemeyin.

## English

# Contributing Guide

## Development Environment

Python 3.10 or newer is required. The main application uses only the Python
standard library.

```powershell
python server.py --check
python server.py
```

## Change Principles

- Keep changes small and compatible with the existing data model and role boundaries.
- Enforce API authorization on the server, not only by hiding UI controls.
- Never render user input as HTML; use safe APIs such as `textContent`.
- Add size limits and backward-compatible defaults to new state fields.
- Validate DOCX content instead of relying on file extensions alone.
- Update the README and security tests when demo credential behavior changes.

## Required Checks

Run these commands before opening a pull request:

```powershell
python security_tests.py
python advanced_tests.py
python security_advanced_tests.py
python endpoint_quality_tests.py
python server.py --check
python -m py_compile server.py advanced_rules.py security_tests.py advanced_tests.py security_advanced_tests.py endpoint_quality_tests.py wsgi.py
```

Every bug fix should include an appropriate regression test. Tests must not
depend on database state left by another test.

## Commits and Pull Requests

Use short, imperative commit messages. Explain the reason, user impact,
security impact and validation commands in the pull request. Keep unrelated
refactors out of the same pull request.
