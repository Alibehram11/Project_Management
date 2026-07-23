# PythonAnywhere Kurulum Notu

Onerilen Python surumu: **Python 3.12**.

PythonAnywhere dokumaninda mevcut sistem imajina gore Python 3.9-3.13 arasi
secenekler gorunuyor. Bu proje harici paket kullanmadigi ve Python 3.10+
soz dizimine dayandigi icin 3.12 en rahat secimdir. Hesabinda sadece daha yeni
imaj varsa 3.13 de calisir; 3.10 altini secme.

## 1. Dosyalari yukle

Repo klasorunu PythonAnywhere'de su yola koy:

```bash
/home/KULLANICI_ADIN/Project_Management
```

Git ile almak icin:

```bash
cd /home/KULLANICI_ADIN
git clone https://github.com/Alibehram11/Project_Management.git
cd Project_Management
```

## 2. Virtualenv olustur

```bash
mkvirtualenv --python=/usr/bin/python3.12 proje-yonetimi
pip install -r requirements.txt
```

`requirements.txt` bilincli olarak bos sayilir; ana uygulama Flask istemez,
standart kutuphane ile WSGI uzerinden calisir.

## 3. Web app ayari

PythonAnywhere Web sekmesinde:

- Add a new web app
- Manual configuration
- Python 3.12
- Virtualenv: `/home/KULLANICI_ADIN/.virtualenvs/proje-yonetimi`

## 4. WSGI dosyasi

Web sekmesindeki WSGI configuration file icine sunu yaz:

```python
import sys

path = "/home/KULLANICI_ADIN/Project_Management"
if path not in sys.path:
    sys.path.insert(0, path)

from server import application
```

Alternatif olarak repo icindeki `wsgi.py` dosyasini da kullanabilirsin; aktif
uygulama nesnesi `application` adindadir.

## 5. Static files

Bu projede `index.html`, `styles.css` ve `app.js` dosyalari WSGI uygulamasi
tarafindan servis edilir. PythonAnywhere Static files bolumune ekstra esleme
eklemek zorunda degilsin. Ileride dosyalar `static/` gibi ayri bir klasore
tasindiginda bu bolumden klasor eslemesi yapilabilir.

## 6. Kontrol

Bash console'da:

```bash
cd /home/KULLANICI_ADIN/Project_Management
python server.py --check
```

Web sekmesinden Reload yaptiktan sonra:

```text
https://KULLANICI_ADIN.pythonanywhere.com/api/health
```

`ok: true` goruyorsan backend calisiyor demektir.

## Notlar

- `python server.py` PythonAnywhere web yayini icin kullanilmaz; sadece yerelde
  test etmek icindir.
- Veritabani dosyasi `app_data.sqlite3` proje klasorunde olusur.
- Yuklenen Word sablonlari `uploaded_templates/` klasorune yazilir.
- Demo hesaplari PBKDF2-HMAC-SHA256 hash ve kullaniciya ozel salt ile saklanir;
  yine de PythonAnywhere'de yayina almadan once demo parolalarini degistirin.
