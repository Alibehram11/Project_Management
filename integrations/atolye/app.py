from flask import Flask, render_template, request, redirect, url_for, session, flash
from models import db, Product, Request, RequestItem
import hmac
import os

from dotenv import load_dotenv


load_dotenv()


def get_required_env(name):
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"{name} ortam degiskeni ayarlanmali.")
    return value


app = Flask(__name__)
app.config['SECRET_KEY'] = get_required_env('ATOLYE_SECRET_KEY')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///inventory.db'
db.init_app(app)

ADMIN_PASSWORD = get_required_env('ATOLYE_ADMIN_PASSWORD')
MAX_TEXT_LENGTH = 500


def limited_text(value, limit=MAX_TEXT_LENGTH):
    return str(value or '').strip()[:limit]


def form_int(name, default=0):
    try:
        return int(request.form.get(name, default))
    except (TypeError, ValueError):
        return default


@app.route('/')
def index():
    products = Product.query.all()
    return render_template('index.html', products=products)


@app.route('/search', methods=['GET'])
def search():
    query = limited_text(request.args.get('q', ''), 80)
    products = Product.query.filter(Product.name.contains(query)).all()
    return render_template('index.html', products=products, query=query)


@app.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    product_id = form_int('product_id')
    quantity = form_int('quantity')
    product = db.session.get(Product, product_id)
    if not product or quantity < 1 or quantity > product.quantity:
        flash('Gecersiz urun veya adet.')
        return redirect(url_for('index'))
    if 'cart' not in session:
        session['cart'] = {}
    session['cart'][str(product_id)] = quantity
    session.modified = True
    flash('Urun sepete eklendi.')
    return redirect(url_for('index'))


@app.route('/cart')
def cart():
    cart_items = []
    if 'cart' in session:
        for pid, qty in session['cart'].items():
            try:
                product_id = int(pid)
                quantity = int(qty)
            except (TypeError, ValueError):
                continue
            product = db.session.get(Product, product_id)
            if product:
                cart_items.append({'product': product, 'quantity': quantity})
    return render_template('cart.html', cart_items=cart_items)


@app.route('/request_form', methods=['GET', 'POST'])
def request_form():
    if request.method == 'POST':
        student_name = limited_text(request.form.get('student_name'), 100)
        student_id = limited_text(request.form.get('student_id'), 20)
        project_purpose = limited_text(request.form.get('project_purpose'))
        usage_reason = limited_text(request.form.get('usage_reason'))
        if not all([student_name, student_id, project_purpose, usage_reason]):
            flash('Tum alanlari doldurun.')
            return redirect(url_for('request_form'))

        req = Request(student_name=student_name, student_id=student_id,
                      project_purpose=project_purpose, usage_reason=usage_reason)
        db.session.add(req)
        db.session.flush()

        for pid, qty in session.get('cart', {}).items():
            try:
                product_id = int(pid)
                quantity = int(qty)
            except (TypeError, ValueError):
                continue
            item = RequestItem(request_id=req.id, product_id=product_id, quantity=quantity)
            db.session.add(item)

        db.session.commit()
        session.pop('cart', None)
        flash('Talebiniz gonderildi.')
        return redirect(url_for('index'))

    return render_template('request_form.html')


@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if request.method == 'POST':
        password = request.form['password']
        if hmac.compare_digest(password, ADMIN_PASSWORD):
            session['admin'] = True
            return redirect(url_for('admin_panel'))
        flash('Yanlis sifre.')
    return render_template('admin.html')


@app.route('/admin_panel')
def admin_panel():
    if not session.get('admin'):
        return redirect(url_for('admin'))
    requests = Request.query.all()
    return render_template('admin_panel.html', requests=requests)


@app.route('/approve/<int:req_id>')
def approve(req_id):
    if not session.get('admin'):
        return redirect(url_for('admin'))
    req = db.session.get(Request, req_id)
    if req and req.status == 'Beklemede':
        req.status = 'Onaylandi'
        for item in req.items:
            product = item.product
            if product.quantity >= item.quantity:
                product.quantity -= item.quantity
            else:
                flash('Yetersiz stok.')
                return redirect(url_for('admin_panel'))
        db.session.commit()
        flash('Talep onaylandi.')
    return redirect(url_for('admin_panel'))


@app.route('/reject/<int:req_id>')
def reject(req_id):
    if not session.get('admin'):
        return redirect(url_for('admin'))
    req = db.session.get(Request, req_id)
    if req and req.status == 'Beklemede':
        req.status = 'Reddedildi'
        db.session.commit()
        flash('Talep reddedildi.')
    return redirect(url_for('admin_panel'))


@app.route('/logout')
def logout():
    session.pop('admin', None)
    return redirect(url_for('index'))


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        if not Product.query.first():
            products = [
                Product(name='Arduino Uno', description='Mikrodenetleyici karti', quantity=10, category='Elektronik'),
                Product(name='Raspberry Pi', description='Tek kartli bilgisayar', quantity=5, category='Bilgisayar'),
                Product(name='Servo Motor', description='Doner motor', quantity=20, category='Motor'),
                Product(name='LED', description='Isik yayan diyot', quantity=100, category='Isik'),
                Product(name='Breadboard', description='Devre tahtasi', quantity=15, category='Arac'),
            ]
            db.session.add_all(products)
            db.session.commit()

    debug_enabled = os.environ.get('ATOLYE_DEBUG', '').lower() == 'true'
    app.run(host='0.0.0.0', port=5000, debug=debug_enabled)
