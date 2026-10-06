from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
import uuid
import os


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_PATH = os.path.abspath(
    os.path.join(BASE_DIR, "../public/invoice_template.jpg")
)


def _safe_number(value, default=0):
    """Convert a DB numeric/None value into a float safely."""
    if value is None:
        return default

    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _get_invoice_values(data, config):
    """
    Get invoice amounts from the booking created by odt.py.

    odt.py now stores:
        original_price  -> price before coupon
        discount_amount -> coupon discount, capped at ₹100
        total_price     -> final payable amount

    We intentionally use the stored booking values instead of recalculating
    the amount from the pricing function. This prevents the invoice from
    disagreeing with the actual amount paid when coupons are applied.
    """

    # New odt.py fields
    stored_original_price = getattr(data, "original_price", None)
    stored_discount = getattr(data, "discount_amount", None)
    stored_total_price = getattr(data, "total_price", None)

    if (
        stored_original_price is not None
        and stored_total_price is not None
    ):
        original_price = _safe_number(stored_original_price)
        discount = _safe_number(stored_discount)
        total_price = _safe_number(stored_total_price)

        return original_price, discount, total_price

    # ------------------------------------------------------------
    # Backward compatibility for old bookings
    # ------------------------------------------------------------
    pricing_function = config["pricing_function"]
    base_price = _safe_number(config["base_price"])
    meal_preference = getattr(data, "meal_preference", None)
    quantity = int(getattr(data, "total_people", 0) or 0)

    price_per_person = _safe_number(
        pricing_function(quantity, meal_preference)
    )

    calculated_total = quantity * price_per_person

    # Old invoice logic used base_price * quantity as the original amount.
    original_price = base_price * quantity
    discount = max(0, original_price - calculated_total)
    total_price = calculated_total

    return original_price, discount, total_price


def _create_invoice_canvas(file_path):
    """Create the invoice canvas and place the invoice background template."""
    c = canvas.Canvas(file_path, pagesize=A4)
    width, height = A4

    if os.path.exists(TEMPLATE_PATH):
        c.drawImage(
            TEMPLATE_PATH,
            0,
            0,
            width=width,
            height=height,
        )

    return c


def generate_invoice(
    data,
    config,
):
    """
    Generate invoice for Budhni / Halali / Heritage bookings.

    Updated according to odt.py:
      - Uses booking.original_price
      - Uses booking.discount_amount
      - Uses booking.total_price
      - Does not recalculate coupon-discounted totals
      - Works for Budhni, Halali and Heritage through config
    """

    quantity = int(getattr(data, "total_people", 0) or 0)

    original_price, discount, amount = _get_invoice_values(
        data,
        config,
    )

    file_name = f"invoice_{uuid.uuid4().hex[:8]}.pdf"

    invoices_folder = os.path.abspath(
        os.path.join(BASE_DIR, "../invoices")
    )
    os.makedirs(invoices_folder, exist_ok=True)

    file_path = os.path.join(invoices_folder, file_name)

    c = _create_invoice_canvas(file_path)

    # ------------------------------------------------------------
    # INVOICE NUMBER / DATE
    # ------------------------------------------------------------
    invoice_no = f"INV-{data.id}"

    submitted_date = getattr(data, "submitted_at", None)
    date_text = (
        str(submitted_date.date())
        if submitted_date
        else "N/A"
    )

    c.drawString(
        149 * mm,
        198 * mm,
        invoice_no,
    )

    c.drawString(
        137 * mm,
        187 * mm,
        date_text,
    )

    # ------------------------------------------------------------
    # BILL TO
    # ------------------------------------------------------------
    primary_name = getattr(
        data,
        "primary_traveller_name",
        "",
    ) or ""

    c.drawString(
        52 * mm,
        198 * mm,
        str(primary_name),
    )

    # ------------------------------------------------------------
    # PACKAGE DETAILS
    # ------------------------------------------------------------
    c.drawString(
        124 * mm,
        142 * mm,
        str(quantity),
    )

    # Show original/base amount per person.
    price_per_person_display = (
        original_price / quantity
        if quantity > 0
        else original_price
    )

    c.drawString(
        145 * mm,
        142 * mm,
        f"{price_per_person_display:.0f}",
    )

    # Original package amount before coupon.
    c.drawString(
        173 * mm,
        142 * mm,
        f"{original_price:.0f}",
    )

    # ------------------------------------------------------------
    # SUMMARY
    # ------------------------------------------------------------
    c.drawString(
        170 * mm,
        104 * mm,
        f"{original_price:.0f}",
    )

    c.drawString(
        170 * mm,
        89 * mm,
        f"{discount:.0f}",
    )

    c.drawString(
        170 * mm,
        71 * mm,
        f"{amount:.0f}",
    )

    # ------------------------------------------------------------
    # PAYMENT DETAILS
    # ------------------------------------------------------------
    c.drawString(
        75 * mm,
        76 * mm,
        "UPI",
    )

    c.drawString(
        75 * mm,
        66 * mm,
        f"{amount:.0f}",
    )

    c.drawString(
        75 * mm,
        54 * mm,
        "0",
    )

    print(
        "Invoice:",
        {
            "booking_id": data.id,
            "original_price": original_price,
            "discount": discount,
            "total_price": amount,
        },
    )

    c.save()

    return file_path


def generate_ujjain_invoice(
    data,
    config,
):
    """
    Generate Ujjain / Omkareshwar invoice.

    Ujjain has its existing partial-payment behavior, so it remains separate
    from the coupon-based invoice flow used by odt.py for Budhni/Heritage.
    """

    pricing_function = config["pricing_function"]
    base_price = _safe_number(config["base_price"])
    meal_preference = getattr(data, "meal_preference", None)

    quantity = int(getattr(data, "total_people", 0) or 0)

    total_without_discount = base_price * quantity

    price_per_person = _safe_number(
        pricing_function(quantity, meal_preference)
    )

    total_with_discount = quantity * price_per_person
    discount = total_without_discount - total_with_discount

    amount = total_with_discount

    if getattr(data, "payment_status", None) == "partial":
        amount = amount * 0.4

    file_name = f"invoice_{uuid.uuid4().hex[:8]}.pdf"

    invoices_folder = os.path.abspath(
        os.path.join(BASE_DIR, "../invoices")
    )
    os.makedirs(invoices_folder, exist_ok=True)

    file_path = os.path.join(invoices_folder, file_name)

    c = _create_invoice_canvas(file_path)

    # ------------------------------------------------------------
    # INVOICE NUMBER / DATE
    # ------------------------------------------------------------
    invoice_no = f"INV-{data.id}"

    submitted_date = getattr(data, "submitted_at", None)
    date_text = (
        str(submitted_date.date())
        if submitted_date
        else "N/A"
    )

    c.drawString(
        149 * mm,
        198 * mm,
        invoice_no,
    )

    c.drawString(
        137 * mm,
        187 * mm,
        date_text,
    )

    # ------------------------------------------------------------
    # BILL TO
    # ------------------------------------------------------------
    primary_name = getattr(
        data,
        "primary_traveller_name",
        "",
    ) or ""

    c.drawString(
        52 * mm,
        198 * mm,
        str(primary_name),
    )

    # ------------------------------------------------------------
    # PACKAGE DETAILS
    # ------------------------------------------------------------
    c.drawString(
        124 * mm,
        142 * mm,
        str(quantity),
    )

    c.drawString(
        145 * mm,
        142 * mm,
        f"{base_price:.0f}",
    )

    c.drawString(
        173 * mm,
        142 * mm,
        f"{total_without_discount:.0f}",
    )

    # ------------------------------------------------------------
    # SUMMARY
    # ------------------------------------------------------------
    c.drawString(
        170 * mm,
        104 * mm,
        f"{total_without_discount:.0f}",
    )

    c.drawString(
        170 * mm,
        89 * mm,
        f"{discount:.0f}",
    )

    c.drawString(
        170 * mm,
        71 * mm,
        f"{amount:.0f}",
    )

    # ------------------------------------------------------------
    # PAYMENT DETAILS
    # ------------------------------------------------------------
    c.drawString(
        75 * mm,
        76 * mm,
        "UPI",
    )

    c.drawString(
        75 * mm,
        66 * mm,
        f"{amount:.0f}",
    )

    # Remaining amount after partial payment.
    remaining_amount = total_with_discount - amount

    c.drawString(
        75 * mm,
        54 * mm,
        f"{remaining_amount:.0f}",
    )

    print(
        "Ujjain Invoice:",
        {
            "booking_id": data.id,
            "original_price": total_without_discount,
            "discount": discount,
            "total_price": amount,
            "remaining_amount": remaining_amount,
        },
    )

    c.save()

    return file_path
