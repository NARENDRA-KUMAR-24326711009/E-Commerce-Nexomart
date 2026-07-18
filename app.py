from flask import (Flask, render_template, request, redirect, url_for,
                    session, flash, jsonify, send_file)
from database import (db, User, Product, Order, OrderItem, CartItem, Category,
                       Review, Address, Transaction, Settings)
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import func
from datetime import datetime, timedelta
from functools import wraps
import random
import string
import os
import razorpay

from pdf_utils import build_invoice_pdf, build_sales_report_pdf

app = Flask(__name__)
app.secret_key = 'nexomart_secret_key_2024'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///nexomart.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

def generate_order_id():
    return 'NXM' + ''.join(random.choices(string.digits, k=10))

# ─── ADMIN ACCESS CONTROL ────────────────────────────────────────────────────
def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('user_id'):
            return redirect(url_for('login'))
        user = User.query.get(session['user_id'])
        if not user or user.role != 'admin':
            flash('Access denied — admins only.', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated

# ─── ANALYTICS HELPERS ───────────────────────────────────────────────────────
def parse_date_range(req, default_days=30):
    """Reads ?start=YYYY-MM-DD&end=YYYY-MM-DD from the request, defaulting to
    the last `default_days` days (inclusive of the whole end day)."""
    end_str = req.args.get('end')
    start_str = req.args.get('start')
    if end_str:
        end = datetime.strptime(end_str, '%Y-%m-%d') + timedelta(days=1) - timedelta(seconds=1)
    else:
        end = datetime.utcnow()
    if start_str:
        start = datetime.strptime(start_str, '%Y-%m-%d')
    else:
        start = (end - timedelta(days=default_days)).replace(hour=0, minute=0, second=0, microsecond=0)
    return start, end

def get_category_sales(start, end):
    """[(category_name, revenue, distinct_order_count), ...] sorted by revenue desc."""
    rows = (db.session.query(
                Category.name,
                func.sum(OrderItem.price * OrderItem.quantity),
                func.count(func.distinct(Order.id)))
            .select_from(Category)
            .join(Product, Product.category_id == Category.id)
            .join(OrderItem, OrderItem.product_id == Product.id)
            .join(Order, Order.id == OrderItem.order_id)
            .filter(Order.status != 'Cancelled')
            .filter(Order.created_at >= start, Order.created_at <= end)
            .group_by(Category.id, Category.name)
            .order_by(func.sum(OrderItem.price * OrderItem.quantity).desc())
            .all())
    return [(name, round(rev or 0, 2), cnt) for name, rev, cnt in rows]

def get_sales_over_time(start, end):
    rows = (db.session.query(
                func.strftime('%Y-%m-%d', Order.created_at),
                func.sum(Order.total_amount))
            .filter(Order.status != 'Cancelled')
            .filter(Order.created_at >= start, Order.created_at <= end)
            .group_by(func.strftime('%Y-%m-%d', Order.created_at))
            .order_by(func.strftime('%Y-%m-%d', Order.created_at))
            .all())
    return [(d, round(v or 0, 2)) for d, v in rows]

def get_order_status_distribution(start, end):
    return (db.session.query(Order.status, func.count(Order.id))
            .filter(Order.created_at >= start, Order.created_at <= end)
            .group_by(Order.status).all())

def get_transaction_status_distribution(start, end):
    return (db.session.query(Transaction.status, func.count(Transaction.id))
            .filter(Transaction.created_at >= start, Transaction.created_at <= end)
            .group_by(Transaction.status).all())

def get_top_products(start, end, limit=5):
    return (db.session.query(
                Product.name, func.sum(OrderItem.quantity),
                func.sum(OrderItem.price * OrderItem.quantity))
            .join(OrderItem, OrderItem.product_id == Product.id)
            .join(Order, Order.id == OrderItem.order_id)
            .filter(Order.status != 'Cancelled')
            .filter(Order.created_at >= start, Order.created_at <= end)
            .group_by(Product.id, Product.name)
            .order_by(func.sum(OrderItem.quantity).desc())
            .limit(limit).all())

# ─── AUTH ───────────────────────────────────────────────────────────────────
@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        phone = request.form['phone']
        password = request.form['password']
        if User.query.filter_by(email=email).first():
            flash('Email already registered!', 'danger')
            return redirect(url_for('register'))
        
        hashed_password = generate_password_hash(password)
        user = User(name=name, email=email, phone=phone,
                    password_hash=hashed_password)
        

        db.session.add(user)
        db.session.commit()
        flash('Account created! Please login.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()

        # if user and check_password_hash(user.password, password):
        if user and check_password_hash(user.password_hash, password):
            session['user_id'] = user.id
            session['user_name'] = user.name
            session['user_role'] = user.role
            flash(f'Welcome back, {user.name}!', 'success')
            return redirect(url_for('admin_dashboard') if user.role == 'admin' else url_for('index'))
        flash('Invalid credentials!', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

# ─── HOME ────────────────────────────────────────────────────────────────────
@app.route('/')
def index():
    categories = Category.query.all()
    featured = Product.query.filter_by(is_featured=True).limit(8).all()
    deals = Product.query.filter(Product.discount > 20).limit(8).all()
    new_arrivals = Product.query.order_by(Product.id.desc()).limit(8).all()
    return render_template('index.html', categories=categories,
                           featured=featured, deals=deals, new_arrivals=new_arrivals)

# ─── PRODUCTS ────────────────────────────────────────────────────────────────
@app.route('/products')
def products():
    q = request.args.get('q', '')
    cat = request.args.get('category', '')
    sort = request.args.get('sort', 'popular')
    min_price = request.args.get('min_price', 0, type=float)
    max_price = request.args.get('max_price', 999999, type=float)

    query = Product.query
    if q:
        query = query.filter(Product.name.ilike(f'%{q}%'))
    if cat:
        category = Category.query.filter_by(slug=cat).first()
        if category:
            query = query.filter_by(category_id=category.id)
    query = query.filter(Product.price >= min_price, Product.price <= max_price)
    if sort == 'price_asc':
        query = query.order_by(Product.price.asc())
    elif sort == 'price_desc':
        query = query.order_by(Product.price.desc())
    elif sort == 'newest':
        query = query.order_by(Product.id.desc())
    else:
        query = query.order_by(Product.rating.desc())

    products = query.all()
    categories = Category.query.all()
    return render_template('products.html', products=products, categories=categories,
                           q=q, selected_cat=cat, sort=sort)

@app.route('/product/<int:pid>')
def product_detail(pid):
    product = Product.query.get_or_404(pid)
    reviews = Review.query.filter_by(product_id=pid).all()
    related = Product.query.filter_by(category_id=product.category_id).filter(Product.id != pid).limit(4).all()
    in_wishlist = False
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        in_wishlist = str(pid) in (user.wishlist or '').split(',')
    return render_template('product_detail.html', product=product,
                           reviews=reviews, related=related, in_wishlist=in_wishlist)

# ─── CART ─────────────────────────────────────────────────────────────────────
@app.route('/cart')
def cart():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    items = CartItem.query.filter_by(user_id=session['user_id']).all()
    total = sum(i.product.price * (1 - i.product.discount/100) * i.quantity for i in items)
    return render_template('cart.html', items=items, total=total)

@app.route('/cart/add/<int:pid>', methods=['POST'])
def add_to_cart(pid):
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Login required'})
    qty = int(request.form.get('quantity', 1))
    item = CartItem.query.filter_by(user_id=session['user_id'], product_id=pid).first()
    if item:
        item.quantity += qty
    else:
        item = CartItem(user_id=session['user_id'], product_id=pid, quantity=qty)
        db.session.add(item)
    db.session.commit()
    cart_count = CartItem.query.filter_by(user_id=session['user_id']).count()
    return jsonify({'success': True, 'cart_count': cart_count})

@app.route('/cart/remove/<int:item_id>')
def remove_from_cart(item_id):
    item = CartItem.query.get_or_404(item_id)
    if item.user_id == session.get('user_id'):
        db.session.delete(item)
        db.session.commit()
    return redirect(url_for('cart'))

@app.route('/cart/update/<int:item_id>', methods=['POST'])
def update_cart(item_id):
    item = CartItem.query.get_or_404(item_id)
    if item.user_id == session.get('user_id'):
        qty = int(request.form.get('quantity', 1))
        if qty <= 0:
            db.session.delete(item)
        else:
            item.quantity = qty
        db.session.commit()
    return redirect(url_for('cart'))

# ─── WISHLIST ─────────────────────────────────────────────────────────────────
@app.route('/wishlist/toggle/<int:pid>')
def toggle_wishlist(pid):
    if 'user_id' not in session:
        return jsonify({'success': False})
    user = User.query.get(session['user_id'])
    wishlist = set(filter(None, (user.wishlist or '').split(',')))
    if str(pid) in wishlist:
        wishlist.discard(str(pid))
        added = False
    else:
        wishlist.add(str(pid))
        added = True
    user.wishlist = ','.join(wishlist)
    db.session.commit()
    return jsonify({'success': True, 'added': added})

@app.route('/wishlist')
def wishlist():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user = User.query.get(session['user_id'])
    ids = list(filter(None, (user.wishlist or '').split(',')))
    products = Product.query.filter(Product.id.in_(ids)).all() if ids else []
    return render_template('wishlist.html', products=products)

# ─── CHECKOUT ────────────────────────────────────────────────────────────────
@app.route('/checkout', methods=['GET','POST'])
def checkout():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    items = CartItem.query.filter_by(user_id=session['user_id']).all()
    if not items:
        flash('Cart is empty!', 'warning')
        return redirect(url_for('cart'))

    if request.method == 'POST':
        payment = request.form['payment']
        if payment != 'COD':
            # Online methods are handled via the Razorpay popup (AJAX) —
            # this branch should only ever receive COD form submissions.
            flash('Please complete the payment in the popup, or choose Cash on Delivery.', 'warning')
            return redirect(url_for('checkout'))

        address_line = request.form['address']
        city = request.form['city']
        state = request.form['state']
        pincode = request.form['pincode']

        order_id = generate_order_id()
        total = sum(i.product.price * (1 - i.product.discount/100) * i.quantity for i in items)
        est_delivery = datetime.now() + timedelta(days=random.randint(3, 7))

        order = Order(
            order_id=order_id, user_id=session['user_id'],
            total_amount=round(total, 2), status='Confirmed',
            address=f"{address_line}, {city}, {state} - {pincode}",
            payment_method=payment, payment_status='COD',
            estimated_delivery=est_delivery
        )
        db.session.add(order)
        db.session.flush()

        for item in items:
            oi = OrderItem(order_id=order.id, product_id=item.product_id,
                           quantity=item.quantity,
                           price=round(item.product.price * (1 - item.product.discount/100), 2))
            db.session.add(oi)
            db.session.delete(item)

        db.session.add(Transaction(
            order_id=order.id, user_id=session['user_id'],
            amount=round(total, 2), method='COD', status='cod'
        ))

        db.session.commit()
        flash(f'Order {order_id} placed successfully!', 'success')
        return redirect(url_for('order_detail', order_id=order_id))

    total = sum(i.product.price * (1 - i.product.discount/100) * i.quantity for i in items)
    addresses = Address.query.filter_by(user_id=session['user_id']).all()
    settings = Settings.get()
    return render_template('checkout.html', items=items, total=total,
                           addresses=addresses, settings=settings)

# ─── RAZORPAY PAYMENT FLOW (test mode) ──────────────────────────────────────
@app.route('/payment/create_order', methods=['POST'])
def payment_create_order():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Login required'}), 401

    items = CartItem.query.filter_by(user_id=session['user_id']).all()
    if not items:
        return jsonify({'success': False, 'message': 'Your cart is empty'}), 400

    settings = Settings.get()
    if not settings.razorpay_key_id or not settings.razorpay_key_secret:
        return jsonify({'success': False,
                         'message': 'Online payments are not configured yet. Please choose Cash '
                                    'on Delivery, or ask the admin to add Razorpay keys under '
                                    'Admin → Settings.'}), 400

    data = request.get_json(silent=True) or {}
    for field in ['name', 'phone', 'address', 'city', 'state', 'pincode', 'payment']:
        if not data.get(field):
            return jsonify({'success': False, 'message': f'"{field}" is required'}), 400

    total = sum(i.product.discounted_price * i.quantity for i in items)
    amount_paise = int(round(total * 100))

    try:
        client = razorpay.Client(auth=(settings.razorpay_key_id, settings.razorpay_key_secret))
        rp_order = client.order.create({
            'amount': amount_paise, 'currency': 'INR', 'payment_capture': 1
        })
    except Exception as e:
        return jsonify({'success': False, 'message': f'Could not reach Razorpay: {e}'}), 502

    items_snapshot = [{'product_id': i.product_id, 'quantity': i.quantity,
                        'price': i.product.discounted_price} for i in items]

    session['pending_checkout'] = {
        'razorpay_order_id': rp_order['id'],
        'amount': round(total, 2),
        'items': items_snapshot,
        'address': data['address'], 'city': data['city'], 'state': data['state'],
        'pincode': data['pincode'], 'name': data['name'], 'phone': data['phone'],
        'payment_method': data['payment'],
    }

    user = User.query.get(session['user_id'])
    return jsonify({
        'success': True,
        'key_id': settings.razorpay_key_id,
        'amount': amount_paise,
        'currency': 'INR',
        'razorpay_order_id': rp_order['id'],
        'name': user.name, 'email': user.email, 'contact': user.phone or ''
    })

@app.route('/payment/verify', methods=['POST'])
def payment_verify():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Login required'}), 401

    pending = session.get('pending_checkout')
    if not pending:
        return jsonify({'success': False, 'message': 'No pending checkout found. Please try again.'}), 400

    data = request.get_json(silent=True) or {}
    rp_order_id = data.get('razorpay_order_id')
    rp_payment_id = data.get('razorpay_payment_id')
    rp_signature = data.get('razorpay_signature')

    if rp_order_id != pending.get('razorpay_order_id'):
        return jsonify({'success': False, 'message': 'Order mismatch, please retry checkout.'}), 400

    settings = Settings.get()
    client = razorpay.Client(auth=(settings.razorpay_key_id, settings.razorpay_key_secret))
    try:
        client.utility.verify_payment_signature({
            'razorpay_order_id': rp_order_id,
            'razorpay_payment_id': rp_payment_id,
            'razorpay_signature': rp_signature
        })
    except razorpay.errors.SignatureVerificationError:
        db.session.add(Transaction(
            user_id=session['user_id'], razorpay_order_id=rp_order_id,
            razorpay_payment_id=rp_payment_id, amount=pending['amount'],
            method=pending['payment_method'], status='failed',
            failure_reason='Signature verification failed'
        ))
        db.session.commit()
        return jsonify({'success': False, 'message': 'Payment verification failed'}), 400

    order_id = generate_order_id()
    est_delivery = datetime.now() + timedelta(days=random.randint(3, 7))
    order = Order(
        order_id=order_id, user_id=session['user_id'],
        total_amount=round(pending['amount'], 2), status='Confirmed',
        address=f"{pending['name']}, {pending['address']}, {pending['city']}, "
                f"{pending['state']} - {pending['pincode']}",
        payment_method=pending['payment_method'], payment_status='Paid',
        estimated_delivery=est_delivery
    )
    db.session.add(order)
    db.session.flush()

    for it in pending['items']:
        db.session.add(OrderItem(order_id=order.id, product_id=it['product_id'],
                                  quantity=it['quantity'], price=it['price']))

    db.session.add(Transaction(
        order_id=order.id, user_id=session['user_id'],
        razorpay_order_id=rp_order_id, razorpay_payment_id=rp_payment_id,
        razorpay_signature=rp_signature, amount=round(pending['amount'], 2),
        method=pending['payment_method'], status='success'
    ))

    CartItem.query.filter_by(user_id=session['user_id']).delete()
    session.pop('pending_checkout', None)
    db.session.commit()

    flash(f'Payment successful! Order {order_id} placed.', 'success')
    return jsonify({'success': True, 'order_id': order_id})

@app.route('/payment/failed', methods=['POST'])
def payment_failed():
    if 'user_id' not in session:
        return jsonify({'success': False}), 401
    data = request.get_json(silent=True) or {}
    pending = session.get('pending_checkout') or {}
    db.session.add(Transaction(
        user_id=session['user_id'],
        razorpay_order_id=data.get('razorpay_order_id') or pending.get('razorpay_order_id'),
        razorpay_payment_id=data.get('razorpay_payment_id'),
        amount=pending.get('amount', 0),
        method=pending.get('payment_method', data.get('method', '')),
        status='failed',
        failure_reason=data.get('description', 'Payment failed / cancelled by user')
    ))
    db.session.commit()
    return jsonify({'success': True})

# ─── ORDERS ──────────────────────────────────────────────────────────────────
@app.route('/orders')
def orders():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user_orders = Order.query.filter_by(user_id=session['user_id']).order_by(Order.created_at.desc()).all()
    return render_template('orders.html', orders=user_orders)

@app.route('/order/<order_id>')
def order_detail(order_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    order = Order.query.filter_by(order_id=order_id, user_id=session['user_id']).first_or_404()
    # Simulate tracking steps
    steps = [
        ('Order Placed', order.created_at, True),
        ('Order Confirmed', order.created_at + timedelta(hours=1), order.status in ['Confirmed','Shipped','Out for Delivery','Delivered']),
        ('Shipped', order.created_at + timedelta(days=1), order.status in ['Shipped','Out for Delivery','Delivered']),
        ('Out for Delivery', order.estimated_delivery - timedelta(hours=4), order.status in ['Out for Delivery','Delivered']),
        ('Delivered', order.estimated_delivery, order.status == 'Delivered'),
    ]
    return render_template('order_detail.html', order=order, steps=steps)

@app.route('/order/<order_id>/invoice.pdf')
def order_invoice_pdf(order_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    order = Order.query.filter_by(order_id=order_id, user_id=session['user_id']).first_or_404()
    buf = build_invoice_pdf(order)
    return send_file(buf, mimetype='application/pdf', as_attachment=True,
                     download_name=f'{order.order_id}_invoice.pdf')

@app.route('/order/cancel/<order_id>')
def cancel_order(order_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    order = Order.query.filter_by(order_id=order_id, user_id=session['user_id']).first_or_404()
    if order.status in ['Confirmed', 'Processing']:
        order.status = 'Cancelled'
        db.session.commit()
        flash('Order cancelled successfully.', 'success')
    else:
        flash('This order cannot be cancelled.', 'danger')
    return redirect(url_for('order_detail', order_id=order_id))

# ─── REVIEWS ─────────────────────────────────────────────────────────────────
@app.route('/review/<int:pid>', methods=['POST'])
def add_review(pid):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    rating = int(request.form['rating'])
    comment = request.form['comment']
    review = Review(product_id=pid, user_id=session['user_id'],
                    rating=rating, comment=comment)
    db.session.add(review)
    # Update product avg rating
    product = Product.query.get(pid)
    reviews = Review.query.filter_by(product_id=pid).all()
    product.rating = round((sum(r.rating for r in reviews) + rating) / (len(reviews) + 1), 1)
    db.session.commit()
    flash('Review submitted!', 'success')
    return redirect(url_for('product_detail', pid=pid))

# ─── PROFILE ─────────────────────────────────────────────────────────────────
@app.route('/profile', methods=['GET','POST'])
def profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user = User.query.get(session['user_id'])
    if request.method == 'POST':
        user.name = request.form['name']
        user.phone = request.form['phone']
        db.session.commit()
        session['user_name'] = user.name
        flash('Profile updated!', 'success')
    return render_template('profile.html', user=user)

@app.route('/address/add', methods=['POST'])
def add_address():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    addr = Address(
        user_id=session['user_id'],
        name=request.form['name'],
        phone=request.form['phone'],
        address_line=request.form['address_line'],
        city=request.form['city'],
        state=request.form['state'],
        pincode=request.form['pincode'],
        address_type=request.form.get('address_type', 'Home')
    )
    db.session.add(addr)
    db.session.commit()
    flash('Address added!', 'success')
    return redirect(url_for('profile'))

# ─── API ─────────────────────────────────────────────────────────────────────
@app.route('/api/cart_count')
def cart_count():
    if 'user_id' not in session:
        return jsonify({'count': 0})
    count = CartItem.query.filter_by(user_id=session['user_id']).count()
    return jsonify({'count': count})

@app.route('/api/search_suggestions')
def search_suggestions():
    q = request.args.get('q', '')
    if len(q) < 2:
        return jsonify([])
    products = Product.query.filter(Product.name.ilike(f'%{q}%')).limit(5).all()
    return jsonify([{'id': p.id, 'name': p.name, 'price': p.price} for p in products])

# ─── CONTEXT PROCESSORS ──────────────────────────────────────────────────────
@app.context_processor
def inject_globals():
    cart_count = 0
    if 'user_id' in session:
        cart_count = CartItem.query.filter_by(user_id=session['user_id']).count()
    categories = Category.query.all()
    return dict(cart_count=cart_count, all_categories=categories,
                current_year=datetime.now().year)

@app.route('/admin')
@admin_required
def admin_dashboard():
    total_orders = Order.query.count()
    total_customers = User.query.filter_by(role='customer').count()
    total_products = Product.query.count()
    total_revenue = db.session.query(func.sum(Order.total_amount)) \
        .filter(Order.status != 'Cancelled').scalar() or 0
    pending_orders = Order.query.filter(
        Order.status.in_(['Confirmed', 'Shipped', 'Out for Delivery'])).count()

    window_start = datetime.utcnow() - timedelta(days=30)
    window_end = datetime.utcnow()
    top_products = get_top_products(window_start, window_end)

    recent_orders = Order.query.order_by(Order.created_at.desc()).limit(6).all()
    recent_users = User.query.filter_by(role='customer') \
        .order_by(User.created_at.desc()).limit(4).all()
    recent_reviews = Review.query.order_by(Review.created_at.desc()).limit(4).all()
    recent_transactions = Transaction.query.order_by(Transaction.created_at.desc()).limit(5).all()

    return render_template('admin/dashboard.html',
        total_orders=total_orders, total_customers=total_customers,
        total_products=total_products, total_revenue=round(total_revenue, 2),
        pending_orders=pending_orders, top_products=top_products,
        recent_orders=recent_orders, recent_users=recent_users,
        recent_reviews=recent_reviews, recent_transactions=recent_transactions,
        active_page='dashboard')

# ─── ADMIN ANALYTICS APIs (feed the Chart.js graphs) ────────────────────────
@app.route('/admin/api/sales_by_category')
@admin_required
def api_sales_by_category():
    start, end = parse_date_range(request)
    rows = get_category_sales(start, end)
    return jsonify({'labels': [r[0] for r in rows],
                    'revenue': [r[1] for r in rows],
                    'orders': [r[2] for r in rows]})

@app.route('/admin/api/sales_over_time')
@admin_required
def api_sales_over_time():
    start, end = parse_date_range(request)
    rows = get_sales_over_time(start, end)
    return jsonify({'labels': [r[0] for r in rows], 'revenue': [r[1] for r in rows]})

@app.route('/admin/api/order_status')
@admin_required
def api_order_status():
    start, end = parse_date_range(request)
    rows = get_order_status_distribution(start, end)
    return jsonify({'labels': [r[0] for r in rows], 'counts': [r[1] for r in rows]})

@app.route('/admin/api/transaction_status')
@admin_required
def api_transaction_status():
    start, end = parse_date_range(request)
    rows = get_transaction_status_distribution(start, end)
    label_map = {'success': 'Success', 'failed': 'Failed', 'cod': 'COD', 'created': 'Pending'}
    return jsonify({'labels': [label_map.get(r[0], r[0]) for r in rows],
                    'counts': [r[1] for r in rows]})

# ─── ADMIN SALES REPORT (date filter + PDF export) ──────────────────────────
@app.route('/admin/sales')
@admin_required
def admin_sales():
    start, end = parse_date_range(request, default_days=30)
    orders = Order.query.filter(Order.created_at >= start, Order.created_at <= end) \
        .order_by(Order.created_at.desc()).all()

    cancelled = sum(1 for o in orders if o.status == 'Cancelled')
    non_cancelled = [o for o in orders if o.status != 'Cancelled']
    total_revenue = sum(o.total_amount for o in non_cancelled)
    avg_order_value = (total_revenue / len(non_cancelled)) if non_cancelled else 0

    summary = {
        'total_orders': len(orders), 'cancelled_orders': cancelled,
        'total_revenue': round(total_revenue, 2),
        'avg_order_value': round(avg_order_value, 2),
    }
    category_rows = get_category_sales(start, end)

    return render_template('admin/sales_report.html', start=start, end=end,
                           orders=orders, summary=summary, category_rows=category_rows,
                           active_page='sales')

@app.route('/admin/sales/pdf')
@admin_required
def admin_sales_pdf():
    start, end = parse_date_range(request, default_days=30)
    orders = Order.query.filter(Order.created_at >= start, Order.created_at <= end) \
        .order_by(Order.created_at.desc()).all()

    cancelled = sum(1 for o in orders if o.status == 'Cancelled')
    non_cancelled = [o for o in orders if o.status != 'Cancelled']
    total_revenue = sum(o.total_amount for o in non_cancelled)
    avg_order_value = (total_revenue / len(non_cancelled)) if non_cancelled else 0

    summary = {
        'total_orders': len(orders), 'cancelled_orders': cancelled,
        'total_revenue': round(total_revenue, 2),
        'avg_order_value': round(avg_order_value, 2),
    }
    category_rows = get_category_sales(start, end)

    buf = build_sales_report_pdf(start, end, summary, category_rows, orders)
    fname = f"nexomart_sales_report_{start.date()}_{end.date()}.pdf"
    return send_file(buf, mimetype='application/pdf', as_attachment=True, download_name=fname)

# ─── ADMIN TRANSACTIONS ──────────────────────────────────────────────────────
@app.route('/admin/transactions')
@admin_required
def admin_transactions():
    status_filter = request.args.get('status', '')
    query = Transaction.query.order_by(Transaction.created_at.desc())
    if status_filter:
        query = query.filter_by(status=status_filter)
    transactions = query.limit(300).all()

    totals = {
        'success': Transaction.query.filter_by(status='success').count(),
        'failed': Transaction.query.filter_by(status='failed').count(),
        'cod': Transaction.query.filter_by(status='cod').count(),
    }
    return render_template('admin/transactions.html', transactions=transactions,
                           status_filter=status_filter, totals=totals,
                           active_page='transactions')

# ─── ADMIN SETTINGS (Razorpay keys) ──────────────────────────────────────────
@app.route('/admin/settings', methods=['GET', 'POST'])
@admin_required
def admin_settings():
    settings = Settings.get()
    if request.method == 'POST':
        settings.razorpay_key_id = request.form.get('razorpay_key_id', '').strip()
        settings.razorpay_key_secret = request.form.get('razorpay_key_secret', '').strip()
        settings.razorpay_enabled = bool(settings.razorpay_key_id and settings.razorpay_key_secret)
        settings.updated_at = datetime.utcnow()
        db.session.commit()
        flash('Razorpay settings updated!', 'success')
        return redirect(url_for('admin_settings'))
    return render_template('admin/settings.html', settings=settings, active_page='settings')

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        from seed import seed_data
        seed_data()
    app.run(debug=True)


