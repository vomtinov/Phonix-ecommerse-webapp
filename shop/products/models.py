from shop import db, app  # 👈 import the app to use its context
from datetime import datetime

# 👕 Product table
class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    stock = db.Column(db.Integer, nullable=False)
    desc = db.Column(db.Text, nullable=False)
    pub_date = db.Column(db.DateTime, nullable=False, default=datetime.now())
    brand_id = db.Column(db.Integer, db.ForeignKey('brand.id'), nullable=False)
    brand = db.relationship('Brand', backref=db.backref('brand', lazy=True))
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=False)
    category = db.relationship('Category', backref=db.backref('category', lazy=True))
    image_1 = db.Column(db.String(256), nullable=False, default='image1.jpg')

    def __repr__(self):
        return f'<Product {self.name}>'

# 🧢 Brand table
class Brand(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), nullable=False, unique=True)

# 🧃 Category table
class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), nullable=False, unique=True)

# ✅ Safely creating tables inside application context
with app.app_context():
    db.create_all()
