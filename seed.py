from database import db, Category, Product, User, Order, OrderItem, Transaction
from werkzeug.security import generate_password_hash
from datetime import datetime, timedelta
import random
import string

def seed_data():
    if Category.query.first():
        return  # Already seeded

    # Categories
    cats = [
        Category(name='Electronics', slug='electronics', icon='📱'),
        Category(name='Fashion', slug='fashion', icon='👗'),
        Category(name='Home & Kitchen', slug='home-kitchen', icon='🏠'),
        Category(name='Books', slug='books', icon='📚'),
        Category(name='Sports', slug='sports', icon='⚽'),
        Category(name='Beauty', slug='beauty', icon='💄'),
        Category(name='Toys', slug='toys', icon='🎮'),
        Category(name='Grocery', slug='grocery', icon='🛒'),
    ]
    db.session.add_all(cats)
    db.session.flush()

    e, f, h, b, s, bty, t, g = cats

    products = [
        # Electronics
        Product(name='Samsung Galaxy S24 Ultra 5G', price=124999, discount=15, brand='Samsung',
                category_id=e.id, rating=4.6, review_count=2341, is_featured=True, stock=50,
                image='https://images.unsplash.com/photo-1610945415295-d9bbf067e59c?w=400',
                description='Latest Samsung flagship with 200MP camera, S Pen, 12GB RAM, 256GB storage.',
                specifications='Display: 6.8" Dynamic AMOLED | Battery: 5000mAh | OS: Android 14'),
        Product(name='Apple iPhone 15 Pro Max', price=159900, discount=5, brand='Apple',
                category_id=e.id, rating=4.8, review_count=5432, is_featured=True, stock=30,
                image='https://images.unsplash.com/photo-1696446702183-cbd38f7ada06?w=400',
                description='Titanium design, A17 Pro chip, 48MP camera system, USB-C.',
                specifications='Display: 6.7" Super Retina XDR | Battery: 4422mAh | Chip: A17 Pro'),
        Product(name='Sony WH-1000XM5 Headphones', price=29990, discount=25, brand='Sony',
                category_id=e.id, rating=4.7, review_count=1876, is_featured=True, stock=80,
                image='https://images.unsplash.com/photo-1618366712010-f4ae9c647dcb?w=400',
                description='Industry-leading noise cancellation, 30hr battery, multipoint connection.',
                specifications='Type: Over-ear | Connectivity: Bluetooth 5.2 | Battery: 30hrs'),
        Product(name='Dell XPS 15 Laptop', price=149990, discount=10, brand='Dell',
                category_id=e.id, rating=4.5, review_count=987, is_featured=True, stock=20,
                image='https://images.unsplash.com/photo-1593642632559-0c6d3fc62b89?w=400',
                description='Intel Core i7, 16GB RAM, 512GB SSD, OLED 4K display.',
                specifications='Processor: Intel Core i7-13700H | RAM: 16GB | Storage: 512GB SSD'),
        Product(name='iPad Air 5th Gen', price=59900, discount=8, brand='Apple',
                category_id=e.id, rating=4.6, review_count=2109, stock=45,
                image='https://images.unsplash.com/photo-1544244015-0df4b3ffc6b0?w=400',
                description='M1 chip, 10.9-inch Liquid Retina display, USB-C, Touch ID.',
                specifications='Display: 10.9" Liquid Retina | Chip: M1 | Storage: 64GB'),
        Product(name='OnePlus 12 5G', price=64999, discount=20, brand='OnePlus',
                category_id=e.id, rating=4.4, review_count=1543, stock=60,
                image='https://images.unsplash.com/photo-1511707171634-5f897ff02aa9?w=400',
                description='Snapdragon 8 Gen 3, 50W wireless charging, Hasselblad cameras.',
                specifications='Display: 6.82" LTPO AMOLED | Battery: 5400mAh | RAM: 12GB'),

        # Fashion
        Product(name="Levi's 501 Original Jeans", price=3999, discount=30, brand="Levi's",
                category_id=f.id, rating=4.3, review_count=892, stock=200,
                image='https://images.unsplash.com/photo-1542272604-787c3835535d?w=400',
                description='Classic straight-fit jeans, 100% cotton denim, timeless style.',
                specifications='Material: 100% Cotton | Fit: Straight | Rise: Mid-rise'),
        Product(name='Nike Air Max 270', price=11995, discount=15, brand='Nike',
                category_id=f.id, rating=4.5, review_count=2341, is_featured=True, stock=150,
                image='https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=400',
                description='Largest Air unit yet for all-day comfort and style.',
                specifications='Material: Mesh Upper | Sole: Rubber | Closure: Lace-up'),
        Product(name='Zara Floral Midi Dress', price=5990, discount=40, brand='Zara',
                category_id=f.id, rating=4.2, review_count=567, stock=80,
                image='https://images.unsplash.com/photo-1515372039744-b8f02a3ae446?w=400',
                description='Elegant floral print midi dress, perfect for any occasion.',
                specifications='Material: Polyester | Length: Midi | Care: Machine Washable'),

        # Home & Kitchen
        Product(name='Instant Pot Duo 7-in-1', price=8999, discount=35, brand='Instant Pot',
                category_id=h.id, rating=4.7, review_count=3421, is_featured=True, stock=120,
                image='https://images.unsplash.com/photo-1585515320310-259814833e62?w=400',
                description='Pressure Cooker, Slow Cooker, Rice Cooker, Steamer, 7 functions.',
                specifications='Capacity: 6 Quart | Functions: 7-in-1 | Material: Stainless Steel'),
        Product(name='Dyson V15 Vacuum Cleaner', price=52900, discount=12, brand='Dyson',
                category_id=h.id, rating=4.6, review_count=1234, is_featured=True, stock=35,
                image='https://images.unsplash.com/photo-1558618666-fcd25c85cd64?w=400',
                description='Laser Detect technology, 60-min runtime, HEPA filtration.',
                specifications='Type: Cordless | Battery: 60 mins | Filtration: HEPA'),

        # Books
        Product(name='Atomic Habits by James Clear', price=499, discount=20, brand='Penguin',
                category_id=b.id, rating=4.8, review_count=12340, stock=500,
                image='https://images.unsplash.com/photo-1544947950-fa07a98d237f?w=400',
                description='The proven system for building good habits and breaking bad ones.',
                specifications='Pages: 320 | Language: English | Publisher: Penguin'),
        Product(name='Rich Dad Poor Dad', price=299, discount=15, brand='Plata Publishing',
                category_id=b.id, rating=4.6, review_count=8765, stock=400,
                image='https://images.unsplash.com/photo-1589998059171-988d887df646?w=400',
                description="What the rich teach their kids about money that the poor don't.",
                specifications='Pages: 336 | Language: English | Genre: Finance'),

        # Sports
        Product(name='Yonex Arcsaber 11 Badminton Racket', price=14999, discount=18, brand='Yonex',
                category_id=s.id, rating=4.7, review_count=876, stock=60,
                image='https://images.unsplash.com/photo-1626224583764-f87db24ac4ea?w=400',
                description='Professional-grade carbon fiber racket for advanced players.',
                specifications='Weight: 83g | String Tension: 19-27 lbs | Material: HM Graphite'),
        Product(name='Decathlon Fitness Cycle', price=24999, discount=22, brand='Decathlon',
                category_id=s.id, rating=4.4, review_count=543, is_featured=True, stock=25,
                image='https://images.unsplash.com/photo-1534438327276-14e5300c3a48?w=400',
                description='Exercise bike with 8 resistance levels, LCD display, foldable.',
                specifications='Resistance: 8 levels | Display: LCD | Max Weight: 120kg'),

        # Beauty
        Product(name='Lakme 9to5 Foundation', price=449, discount=25, brand='Lakme',
                category_id=bty.id, rating=4.3, review_count=2341, stock=300,
                image='https://images.unsplash.com/photo-1522335789203-aabd1fc54bc9?w=400',
                description='Full coverage, long-lasting foundation for all skin types.',
                specifications='Type: Foundation | Coverage: Full | Finish: Matte'),
        Product(name='The Ordinary Niacinamide Serum', price=699, discount=10, brand='The Ordinary',
                category_id=bty.id, rating=4.6, review_count=4532, stock=200,
                image='https://images.unsplash.com/photo-1620916566398-39f1143ab7be?w=400',
                description='10% Niacinamide + 1% Zinc for pore minimising and blemish reduction.',
                specifications='Type: Serum | Volume: 30ml | Skin Type: All'),
    ]

    db.session.add_all(products)
    db.session.flush()

    # Demo customer
    demo = User(name='Rahul Sharma', email='demo@nexomart.com',
                phone='9876543210', password_hash=generate_password_hash('demo123'),
                role='customer')
    db.session.add(demo)

    # Demo admin
    admin = User(name='Admin', email='admin@nexomart.com',
                 phone='9999999999', password_hash=generate_password_hash('admin123'),
                 role='admin')
    db.session.add(admin)

    # A couple more customers so "Customers" stats look real
    extra_customers = [
        User(name='Priya Verma', email='priya@example.com', phone='9123456780',
             password_hash=generate_password_hash('password123'), role='customer'),
        User(name='Amit Singh', email='amit@example.com', phone='9123456781',
             password_hash=generate_password_hash('password123'), role='customer'),
        User(name='Sneha Iyer', email='sneha@example.com', phone='9123456782',
             password_hash=generate_password_hash('password123'), role='customer'),
    ]
    db.session.add_all(extra_customers)
    db.session.flush()

    all_customers = [demo] + extra_customers
    all_products = products

    # ── Historical orders + transactions, spread across the last 90 days,
    #    so the admin analytics dashboard has real category-wise data to show
    #    on first run instead of being empty. ──────────────────────────────
    statuses_pool = ['Confirmed', 'Shipped', 'Out for Delivery', 'Delivered', 'Delivered',
                      'Delivered', 'Cancelled']
    methods_pool = ['UPI', 'Card', 'NetBanking', 'COD']

    def gen_order_id():
        return 'NXM' + ''.join(random.choices(string.digits, k=10))

    used_order_ids = set()
    for day_offset in range(90, 0, -1):
        # Not every day has orders — keep it realistic
        if random.random() > 0.55:
            continue
        num_orders_today = random.randint(1, 4)
        order_date = datetime.utcnow() - timedelta(days=day_offset,
                                                     hours=random.randint(0, 23))
        for _ in range(num_orders_today):
            customer = random.choice(all_customers)
            num_items = random.randint(1, 3)
            chosen_products = random.sample(all_products, k=min(num_items, len(all_products)))

            order_id = gen_order_id()
            while order_id in used_order_ids:
                order_id = gen_order_id()
            used_order_ids.add(order_id)

            status = random.choice(statuses_pool)
            method = random.choice(methods_pool)

            order_total = 0
            line_items = []
            for p in chosen_products:
                qty = random.randint(1, 2)
                price = p.discounted_price
                order_total += price * qty
                line_items.append((p, qty, price))

            order = Order(
                order_id=order_id,
                user_id=customer.id,
                total_amount=round(order_total, 2),
                status=status,
                address=f"{customer.name}'s Address, Mumbai, Maharashtra - 400001",
                payment_method=method,
                payment_status='Cancelled' if status == 'Cancelled' else (
                    'COD' if method == 'COD' else 'Paid'),
                estimated_delivery=order_date + timedelta(days=random.randint(3, 7)),
                created_at=order_date
            )
            db.session.add(order)
            db.session.flush()

            for p, qty, price in line_items:
                db.session.add(OrderItem(order_id=order.id, product_id=p.id,
                                          quantity=qty, price=price))

            # Matching transaction record. In the real flow an Order only ever
            # gets created *after* a successful payment (or for COD), so the
            # transaction tied to an existing order is always cod/success.
            # Standalone "failed" attempts (abandoned checkouts) are added
            # separately below for the success-vs-failed analytics chart.
            txn_status = 'cod' if method == 'COD' else 'success'

            db.session.add(Transaction(
                order_id=order.id,
                user_id=customer.id,
                razorpay_order_id=f'order_DEMO{order.id:06d}' if method != 'COD' else None,
                razorpay_payment_id=f'pay_DEMO{order.id:06d}' if txn_status == 'success' else None,
                amount=round(order_total, 2),
                method=method,
                status=txn_status,
                failure_reason='Payment declined by bank' if txn_status == 'failed' else None,
                created_at=order_date
            ))

    # A few extra *failed* online-payment attempts that never became orders
    # (abandoned checkouts) — useful for the success-vs-failed analytics chart
    for _ in range(8):
        customer = random.choice(all_customers)
        fail_date = datetime.utcnow() - timedelta(days=random.randint(0, 90),
                                                    hours=random.randint(0, 23))
        amount = round(random.choice(all_products).discounted_price * random.randint(1, 2), 2)
        db.session.add(Transaction(
            order_id=None,
            user_id=customer.id,
            razorpay_order_id=f'order_DEMOFAIL{random.randint(1000,9999)}',
            amount=amount,
            method=random.choice(['UPI', 'Card', 'NetBanking']),
            status='failed',
            failure_reason='Payment declined by bank',
            created_at=fail_date
        ))

    db.session.commit()
    print("✅ Database seeded successfully! (admin@nexomart.com / admin123)")
