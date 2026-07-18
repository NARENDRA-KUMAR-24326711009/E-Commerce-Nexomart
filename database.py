from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    # Basic Info
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(15))

    # Authentication
    password_hash = db.Column(db.String(255), nullable=False)

    # Authorization
    role = db.Column(
        db.String(20),
        nullable=False,
        default='customer'
    )  # customer, admin

    is_active = db.Column(
        db.Boolean,
        default=True
    )

    # Existing
    wishlist = db.Column(db.Text, default='')
    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    # Relationships
    orders = db.relationship('Order', backref='user', lazy=True)
    cart_items = db.relationship('CartItem', backref='user', lazy=True)
    reviews = db.relationship('Review', backref='user', lazy=True)
    addresses = db.relationship('Address', backref='user', lazy=True)

    # Password Helpers
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(
            self.password_hash,
            password
        )

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    slug = db.Column(db.String(100), unique=True)
    icon = db.Column(db.String(50), default='🛍️')
    products = db.relationship('Product', backref='category', lazy=True)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Float, nullable=False)
    discount = db.Column(db.Float, default=0)  # percentage
    stock = db.Column(db.Integer, default=100)
    image = db.Column(db.String(300), default='')
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'))
    brand = db.Column(db.String(100))
    rating = db.Column(db.Float, default=4.0)
    review_count = db.Column(db.Integer, default=0)
    is_featured = db.Column(db.Boolean, default=False)
    specifications = db.Column(db.Text, default='')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def discounted_price(self):
        return round(self.price * (1 - self.discount / 100), 2)

    @property
    def savings(self):
        return round(self.price - self.discounted_price, 2)

class CartItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'))
    quantity = db.Column(db.Integer, default=1)
    product = db.relationship('Product')

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.String(20), unique=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    total_amount = db.Column(db.Float)
    status = db.Column(db.String(50), default='Confirmed')
    address = db.Column(db.Text)
    payment_method = db.Column(db.String(50))
    # Pending / Paid / COD / Failed — separate from the delivery `status` above
    payment_status = db.Column(db.String(20), default='Pending')
    estimated_delivery = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    items = db.relationship('OrderItem', backref='order', lazy=True)
    transactions = db.relationship('Transaction', backref='order', lazy=True)

class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'))
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'))
    quantity = db.Column(db.Integer)
    price = db.Column(db.Float)
    product = db.relationship('Product')

class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    rating = db.Column(db.Integer)
    comment = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    product = db.relationship('Product')

class Address(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    name = db.Column(db.String(100))
    phone = db.Column(db.String(15))
    address_line = db.Column(db.Text)
    city = db.Column(db.String(100))
    state = db.Column(db.String(100))
    pincode = db.Column(db.String(10))
    address_type = db.Column(db.String(20), default='Home')


class Transaction(db.Model):
    """Every payment attempt — Razorpay (UPI/Card/NetBanking) or COD."""
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

    razorpay_order_id = db.Column(db.String(100))
    razorpay_payment_id = db.Column(db.String(100))
    razorpay_signature = db.Column(db.String(300))

    amount = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(10), default='INR')
    method = db.Column(db.String(30))  # UPI, Card, NetBanking, COD
    status = db.Column(db.String(20), default='created')  # created, success, failed, cod
    failure_reason = db.Column(db.Text)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User')


class Settings(db.Model):
    """Singleton key/value-ish row holding the admin's own Razorpay test keys."""
    id = db.Column(db.Integer, primary_key=True)
    razorpay_key_id = db.Column(db.String(200), default='')
    razorpay_key_secret = db.Column(db.String(200), default='')
    razorpay_enabled = db.Column(db.Boolean, default=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)

    @staticmethod
    def get():
        settings = Settings.query.first()
        if not settings:
            settings = Settings()
            db.session.add(settings)
            db.session.commit()
        return settings
