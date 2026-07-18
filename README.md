# NEXOMART — Flask E-Commerce Project

A Flipkart-style e-commerce demo built with Flask, featuring product browsing,
cart/wishlist, checkout with Razorpay test-mode payments, order tracking,
PDF invoices, and a live, data-driven admin dashboard with sales analytics.

## Setup

```bash
pip install -r requirements.txt
python3 app.py
```

The app runs at `http://127.0.0.1:5000`. On first run it automatically
creates the SQLite database (`instance/nexomart.db`) and seeds it with demo
categories, products, users, and 90 days of historical orders/transactions
so the dashboard graphs aren't empty. Seeding only runs once — re-running
`python3 app.py` later will not duplicate data.

## Login Credentials

| Role     | Email                  | Password   |
|----------|-------------------------|------------|
| Admin    | admin@nexomart.com      | admin123   |
| Customer | demo@nexomart.com       | demo123    |
| Customer | priya@example.com       | password123|
| Customer | amit@example.com        | password123|
| Customer | sneha@example.com       | password123|

Admins are redirected straight to the Admin Dashboard on login, and also get
an "Admin Dashboard" link in the account dropdown menu.

## Setting Up Razorpay Test-Mode Payments

Online payments (UPI / Card / NetBanking) are optional — Cash on Delivery
always works without any setup. To enable online payments:

1. Create a free account at [razorpay.com](https://razorpay.com) and make
   sure **Test Mode** is switched on (toggle in the top-left of the dashboard).
2. Go to **Settings → API Keys → Generate Test Key**. Copy the Key ID
   (starts with `rzp_test_`) and the Key Secret.
3. Log into NEXOMART as admin → **Admin Dashboard → Settings**, paste both
   values, and save.
4. At checkout, choosing UPI / Card / NetBanking now opens a real Razorpay
   test-mode payment popup.

**Test payment values** (official Razorpay sandbox values — never use real
card numbers in test mode):
- Card: `4111 1111 1111 1111`, any future expiry, any CVV, any name.
- UPI: `success@razorpay` to simulate success, `failure@razorpay` to simulate
  a decline.

Every payment attempt (success or failure) is logged to the `Transaction`
table and shown in **Admin → Transactions**, including abandoned/failed
attempts that never became an order.

## What Was Built

**Customer side**
- Browsing, cart, wishlist, reviews — unchanged from the original build.
- Rewritten checkout page: saved-address autofill, COD or Razorpay test-mode
  payment, inline error handling for failed/cancelled payments.
- "Download Invoice" PDF button on the orders list and order detail pages.

**Admin side** (`/admin`, admin login required)
- **Dashboard** — live stats (orders, customers, products, revenue) and four
  Chart.js graphs: revenue by category, order status split, sales trend, and
  payment outcomes (success/failed/COD), plus a top-products table, recent
  orders, and a recent-activity feed.
- **Sales Report** (`/admin/sales`) — custom date-range filter (with quick
  7/30/90-day buttons), category-wise revenue table, full order list for the
  period, and a **PDF export** of the whole report.
- **Transactions** (`/admin/transactions`) — every payment attempt with
  status filter (success / failed / COD / pending), including abandoned
  checkouts that never produced an order.
- **Settings** (`/admin/settings`) — where the admin enters their own
  Razorpay test API keys.

## Project Structure

```
nexomart/
├── app.py              Flask routes (auth, shop, checkout, payments, admin)
├── database.py         SQLAlchemy models
├── seed.py             Demo data + 90 days of historical orders/transactions
├── pdf_utils.py         Invoice + sales report PDF generation (reportlab)
├── requirements.txt
├── static/
│   ├── css/style.css
│   └── js/main.js
├── templates/
│   ├── ... (storefront pages)
│   └── admin/           Dashboard, sales report, transactions, settings
└── instance/            SQLite DB (created automatically on first run)
```

## Notes

- This is a teaching/demo project — Razorpay keys are stored in plain text
  in the database for simplicity, which is fine for a Test Mode key but
  should never be done with Live Mode keys in a real deployment.
- The Flask dev server (`debug=True`) is for local development only; deploy
  behind a production WSGI server (gunicorn, etc.) for anything beyond a
  demo.
