# NEXOMART — Build Progress Tracker

This file tracks exactly what has been built so the project can be picked up
again from any point. Tick marks = done in this session.

## Checkpoint 1 — Database models
- [x] `Settings` model (stores Razorpay key_id / key_secret, singleton row)
- [x] `Transaction` model (razorpay order/payment id, signature, amount, status, method)
- [x] `Order.payment_status` column (Pending / Paid / COD / Failed)
- [x] `Order.payment_method` reused (already existed)

## Checkpoint 2 — Seed data for analytics
- [x] Admin demo user (admin@nexomart.com / admin123)
- [x] Historical random orders + order items + transactions spread over past
      90 days, across categories, so dashboard graphs aren't empty on first run

## Checkpoint 3 — Razorpay integration (test mode)
- [x] `/admin/settings` page — admin pastes their own Razorpay Test Key ID +
      Key Secret, saved to `Settings` table
- [x] `/payment/create_order` — server creates a Razorpay Order via API
- [x] Checkout page loads `checkout.js`, opens Razorpay modal for
      UPI / Card / NetBanking; COD still bypasses Razorpay
- [x] `/payment/verify` — verifies signature (HMAC SHA256), creates the real
      Order + OrderItems + Transaction(status=success) and empties the cart
- [x] `/payment/failed` — logs Transaction(status=failed) if the modal
      reports a failure (so the dashboard can show failed-payment analytics)

## Checkpoint 4 — Admin dashboard (live + dynamic)
- [x] Real stats (orders, customers, products, revenue) replacing dummy numbers
- [x] Chart: Revenue by Category (bar)
- [x] Chart: Sales Trend over time (line)
- [x] Chart: Order Status breakdown (donut)
- [x] Chart: Payment Success vs Failed (donut)
- [x] Top 5 selling products table
- [x] Recent orders feed (replacing dummy "Recent Activity")

## Checkpoint 5 — Admin Sales Report (date filter + PDF)
- [x] `/admin/sales` page — start/end date filter, re-draws charts + table via AJAX
- [x] `/admin/sales/pdf` — generates a PDF (reportlab) of the filtered report:
      summary, category-wise revenue table, order list

## Checkpoint 6 — Admin Transactions list
- [x] `/admin/transactions` — table of all transactions (order id, customer,
      amount, method, status, date), status filter, link into order detail

## Checkpoint 7 — Customer-side purchase PDFs
- [x] `orders.html` — "Download Invoice" button per order
- [x] `order_detail.html` — "Download Invoice PDF" button
- [x] `/order/<order_id>/invoice.pdf` — generates a clean invoice PDF
      (items purchased, prices, totals, payment info)

## Checkpoint 8 — Wiring + polish
- [x] `admin_required` decorator, all admin routes protected
- [x] `templates/admin/_admin_base.html` shared sidebar layout
- [x] CSS for sidebar active states, chart cards, filter bar, tables, badges
- [x] checkout.html payment section cleaned up (old broken/duplicate markup
      removed) and wired to Razorpay JS
- [x] requirements.txt updated (razorpay, reportlab)
- [x] Sanity-run the app (`flask` boots, routes resolve, db creates) inside
      the sandbox before packaging

## Final — Packaging
- [x] Zip the full `nexomart/` project and hand it to the user
- [x] README.md with setup steps + where to get free Razorpay test keys
