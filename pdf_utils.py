"""
PDF generation helpers for NEXOMART.

Two kinds of PDFs:
  1. Customer order invoice  -> build_invoice_pdf(order)
  2. Admin sales report      -> build_sales_report_pdf(...)

Both return a BytesIO buffer ready to be sent with Flask's send_file().
"""
from io import BytesIO
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_RIGHT, TA_CENTER
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)

BRAND_BLUE = colors.HexColor('#2874f0')
BRAND_DARK = colors.HexColor('#212121')
BRAND_GRAY = colors.HexColor('#878787')
BRAND_GREEN = colors.HexColor('#388e3c')

styles = getSampleStyleSheet()
styles.add(ParagraphStyle('BrandTitle', parent=styles['Title'], textColor=BRAND_BLUE, fontSize=20))
styles.add(ParagraphStyle('SmallGray', parent=styles['Normal'], textColor=BRAND_GRAY, fontSize=9))
styles.add(ParagraphStyle('SectionHead', parent=styles['Heading2'], textColor=BRAND_DARK, fontSize=13,
                           spaceBefore=14, spaceAfter=6))
styles.add(ParagraphStyle('RightNormal', parent=styles['Normal'], alignment=TA_RIGHT))
styles.add(ParagraphStyle('CenterSmall', parent=styles['Normal'], alignment=TA_CENTER, fontSize=9,
                           textColor=BRAND_GRAY))


def _rupee(amount):
    return f"Rs. {amount:,.2f}"


def _header(elements, subtitle):
    elements.append(Paragraph("NEXOMART", styles['BrandTitle']))
    elements.append(Paragraph(subtitle, styles['SmallGray']))
    elements.append(Spacer(1, 6))
    elements.append(HRFlowable(width="100%", color=BRAND_BLUE, thickness=1.2))
    elements.append(Spacer(1, 12))


def build_invoice_pdf(order):
    """order: an Order model instance (with .items, .user, .transactions loaded)."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4,
                             topMargin=18 * mm, bottomMargin=18 * mm,
                             leftMargin=18 * mm, rightMargin=18 * mm)
    elements = []
    _header(elements, "Tax Invoice / Order Receipt")

    txn = order.transactions[-1] if order.transactions else None

    info_table_data = [
        [Paragraph(f"<b>Order ID:</b> {order.order_id}", styles['Normal']),
         Paragraph(f"<b>Order Date:</b> {order.created_at.strftime('%d %b %Y, %I:%M %p')}", styles['Normal'])],
        [Paragraph(f"<b>Billed To:</b> {order.user.name}", styles['Normal']),
         Paragraph(f"<b>Payment Method:</b> {order.payment_method}", styles['Normal'])],
        [Paragraph(f"<b>Email:</b> {order.user.email}", styles['Normal']),
         Paragraph(f"<b>Payment Status:</b> {order.payment_status}", styles['Normal'])],
    ]
    if txn and txn.razorpay_payment_id:
        info_table_data.append([
            Paragraph(f"<b>Payment Ref:</b> {txn.razorpay_payment_id}", styles['Normal']),
            Paragraph(f"<b>Order Status:</b> {order.status}", styles['Normal'])
        ])
    info_table = Table(info_table_data, colWidths=[None, None])
    info_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    elements.append(info_table)

    elements.append(Paragraph("Delivery Address", styles['SectionHead']))
    elements.append(Paragraph(order.address, styles['Normal']))

    elements.append(Paragraph("Items Purchased", styles['SectionHead']))
    rows = [["#", "Product", "Brand", "Qty", "Unit Price", "Subtotal"]]
    for i, item in enumerate(order.items, start=1):
        rows.append([
            str(i),
            Paragraph(item.product.name, styles['Normal']),
            item.product.brand or '-',
            str(item.quantity),
            _rupee(item.price),
            _rupee(item.price * item.quantity),
        ])
    item_table = Table(rows, colWidths=[18, 190, 70, 35, 75, 80])
    item_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), BRAND_BLUE),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('ALIGN', (3, 0), (-1, -1), 'CENTER'),
        ('ALIGN', (4, 0), (-1, -1), 'RIGHT'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e0e0e0')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f7f9fc')]),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    elements.append(item_table)

    elements.append(Spacer(1, 10))
    total_table = Table([["Total Amount Paid", _rupee(order.total_amount)]], colWidths=[400, 78])
    total_table.setStyle(TableStyle([
        ('FONTSIZE', (0, 0), (-1, -1), 12),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
        ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
        ('TEXTCOLOR', (0, 0), (-1, -1), BRAND_DARK),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('LINEABOVE', (0, 0), (-1, 0), 1, BRAND_BLUE),
    ]))
    elements.append(total_table)

    elements.append(Spacer(1, 24))
    elements.append(Paragraph(
        "This is a system-generated invoice for a demo/academic e-commerce project.",
        styles['CenterSmall']))
    elements.append(Paragraph(
        f"Generated on {datetime.now().strftime('%d %b %Y, %I:%M %p')} | NEXOMART",
        styles['CenterSmall']))

    doc.build(elements)
    buffer.seek(0)
    return buffer


def build_sales_report_pdf(start_date, end_date, summary, category_rows, orders):
    """
    summary: dict with total_orders, total_revenue, avg_order_value, cancelled_orders
    category_rows: list of (category_name, revenue, order_count) tuples
    orders: list of Order instances within the date range
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4,
                             topMargin=18 * mm, bottomMargin=18 * mm,
                             leftMargin=15 * mm, rightMargin=15 * mm)
    elements = []
    period = f"{start_date.strftime('%d %b %Y')} – {end_date.strftime('%d %b %Y')}"
    _header(elements, f"Admin Sales Report &nbsp;|&nbsp; Period: {period}")

    elements.append(Paragraph("Summary", styles['SectionHead']))
    summary_rows = [
        ["Total Orders", str(summary['total_orders'])],
        ["Cancelled Orders", str(summary['cancelled_orders'])],
        ["Total Revenue", _rupee(summary['total_revenue'])],
        ["Average Order Value", _rupee(summary['avg_order_value'])],
    ]
    summary_table = Table(summary_rows, colWidths=[200, 200])
    summary_table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e0e0e0')),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f1f3f6')),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(summary_table)

    elements.append(Paragraph("Category-wise Revenue", styles['SectionHead']))
    cat_table_data = [["Category", "Orders Containing Item", "Revenue"]]
    for name, revenue, count in category_rows:
        cat_table_data.append([name, str(count), _rupee(revenue)])
    cat_table = Table(cat_table_data, colWidths=[220, 150, 100])
    cat_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), BRAND_BLUE),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTSIZE', (0, 0), (-1, -1), 9.5),
        ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e0e0e0')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f7f9fc')]),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    elements.append(cat_table)

    elements.append(Paragraph(f"Orders in Period ({len(orders)})", styles['SectionHead']))
    order_rows = [["Order ID", "Date", "Customer", "Payment", "Status", "Amount"]]
    for o in orders:
        order_rows.append([
            o.order_id,
            o.created_at.strftime('%d %b %Y'),
            o.user.name if o.user else '-',
            o.payment_method or '-',
            o.status,
            _rupee(o.total_amount),
        ])
    order_table = Table(order_rows, colWidths=[80, 65, 100, 65, 80, 80], repeatRows=1)
    order_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), BRAND_DARK),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTSIZE', (0, 0), (-1, -1), 8.5),
        ('ALIGN', (-1, 0), (-1, -1), 'RIGHT'),
        ('GRID', (0, 0), (-1, -1), 0.4, colors.HexColor('#e0e0e0')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f7f9fc')]),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    elements.append(order_table)

    elements.append(Spacer(1, 18))
    elements.append(Paragraph(
        f"Generated on {datetime.now().strftime('%d %b %Y, %I:%M %p')} | NEXOMART Admin Panel",
        styles['CenterSmall']))

    doc.build(elements)
    buffer.seek(0)
    return buffer
