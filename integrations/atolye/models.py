from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    quantity = db.Column(db.Integer, nullable=False)
    category = db.Column(db.String(50))

class Request(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_name = db.Column(db.String(100), nullable=False)
    student_id = db.Column(db.String(20), nullable=False)
    project_purpose = db.Column(db.Text, nullable=False)
    usage_reason = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default='Beklemede')  # Beklemede, Onaylandı, Reddedildi
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    items = db.relationship('RequestItem', backref='request', lazy=True)

class RequestItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    request_id = db.Column(db.Integer, db.ForeignKey('request.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    product = db.relationship('Product')