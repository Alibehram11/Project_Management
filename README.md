# Proje Yönetimi

Mail ve şifre ile giriş yapılan, proje seçimi olan, adminlerin ekip kurup görev
atayabildiği yerel web prototipi.

## Açma

Tam özellikli kullanım için:

```powershell
python server.py
```

Sonra tarayıcıda `http://127.0.0.1:8765` adresini aç.

Sadece arayüzü görmek için `index.html` dosyası doğrudan açılabilir; bu modda
SQLite kayıt, log ve Word indirme çalışmaz.

Demo mail kartları giriş ekranında bulunur; güvenlik nedeniyle şifreler README
ve arayüz içinde açık metin olarak yayınlanmaz.

## Bu sürümde olanlar

- Düzenlenmiş ana giriş ekranı
- Girişten sonra önce proje seçme ekranı
- Panel içinden proje değiştirme akışı
- Admin panelinde proje listesi
- Kayıt olmuş kişiyi projeye doğrudan ekleme
- Eklenen kişiye hemen görev atayabilme
- Ana admin, admin, ekip kaptanı ve üye rolleri
- Ekip kaptanının kendi ekibindeki kişilere görev verebilmesi
- Görev tesliminde not ve dosya yükleme
- Adminin teslimi onaylaması veya düzeltme istemesi
- Proje takvimi girişi
- CRM fırsatları ekranı
- Takım akışı ekranı
- Yönetim raporları ekranı
- Benim işlerim ekranı
- Gelen kutusu ekranı
- Görev önceliği, etiketi ve tahmini süre alanları
- Görev checklist'i
- Görev yorumları
- `proje_yonetimi_ogrenci_belgeleri_word` klasöründeki 10 Word belgesinin site
  içinde doldurulabilir form şablonu olarak eklenmesi
- Ana adminin belge sorularını düzenleyebilmesi
- Web formunda doldurulan belgeyi `.docx` olarak indirebilme
- Verilen Word şablonlarının arka planda kontrol edilmesi
- Admin panelinde kullanıcı ekleme, projeden çıkarma ve sistemden silme
- SQLite veritabanına state, snapshot ve log kaydı
- Admin için sistem logları ve müdahale araçları
- JSON yedek indirme, veritabanından geri yükleme ve veri onarma
- Siyah-beyaz, hareketli ve tıklanabilir yeni verimlilik paneli
- Proje içinde Atölye sekmesi
- `Alibehram11/Atolye` kaynaklarının `integrations/atolye` altında saklanması
- PBKDF2 tabanlı şifre hashleme ve eski açık şifreleri otomatik migrate etme
- Same-origin CORS, CSRF token kontrolü ve backend state sanitizasyonu

Not: Bitrix24 gibi kapsamlı iş yönetimi araçlarından esinlenen CRM, akış ve
raporlama modülleri eklendi; marka, arayüz ve ürün birebir kopyalanmaz.

Veriler tarayıcı `localStorage` alanında tutulmaya devam eder; backend ile
açıldığında aynı veri `app_data.sqlite3` dosyasına da kaydedilir. Word indirme
akışı verilen şablon dosyasını doğrular ve cevapları yeni bir `.docx` dosyasına
yazar.

## İncelenen benzer uygulamalar

- Asana: görev sahipliği, son tarih, proje görünümleri, özel alanlar, zaman
  takibi, benim görevlerim ve raporlama yaklaşımından esinlenildi.
- Trello: kart/pano mantığı, etiketler ve checklist yaklaşımından esinlenildi.
- ClickUp: görev, doküman, dashboard, yorum/chat, otomasyon ve zaman takibi
  yaklaşımından esinlenildi.

## Atölye entegrasyonu

`integrations/atolye` klasörü `Alibehram11/Atolye` reposundan alınan Flask tabanlı
robotik atölye envanter uygulamasını içerir. Ana uygulamada bunun hafif,
kullanıcı hesabıyla girilen ve proje paneliyle uyumlu bir ekranı vardır:

- Proje içindeki `Atölye` sekmesi
- Envanter stokları
- Parça talep formu
- Adminler için talep onaylama/reddetme

## Test

Backend kontrolü:

```powershell
python server.py --check
```

Atölye kaynak kontrolü:

```powershell
python -m py_compile integrations/atolye/app.py integrations/atolye/models.py integrations/atolye/create_sample_excel.py
```

Tarayıcıda `index.html?selftest=1` açılırsa gizli self-test çalışır. Bu test
admin görev atama, her üyeye görev atama, üye ekleme, kaptan yetkisi, normal üye
paneli, takvim, belge cevap kaydı, belge soru düzenleme, checklist, yorum,
benim işlerim, gelen kutusu, metrik tutarlılığı ve hatalı/boş veri akışlarını
kontrol eder. Son doğrulamada 83 tutarlılık kontrolü geçti.
