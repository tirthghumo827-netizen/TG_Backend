from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
import uuid
import os
import json
from app.utils.pricing.pachmarhi import get_price_per_person


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_PATH = os.path.abspath(os.path.join(BASE_DIR, "../public/invoice_template.jpg"))

def generate_invoice(
    data,
    config,
):
    pricing_function = config["pricing_function"]
    base_price = config["base_price"]
    meal_preference = data.meal_preference
    

    quantity = data.total_people
    total = base_price * quantity
    
    price_per_person = pricing_function(quantity, meal_preference)
    amount = quantity * price_per_person
    discount = total - amount
    
    file_name = f"invoice_{uuid.uuid4().hex[:8]}.pdf"
    invoices_folder = os.path.abspath(os.path.join(BASE_DIR, "../invoices"))
    os.makedirs(invoices_folder, exist_ok=True)

    file_path = os.path.join(invoices_folder, file_name)

    c = canvas.Canvas(file_path, pagesize=A4)
    width, height = A4

    c.drawImage(TEMPLATE_PATH, 0, 0, width=width, height=height)

    # invoice_no = f"INV-{uuid.uuid4().hex[:6].upper()}"
    invoice_no = f"INV-{data.id}"
    submitted_date = getattr(data, "submitted_at", None)
    date_text = str(submitted_date.date()) if submitted_date else "N/A"

    # USER NAME UNDER LOGO
    # c.drawString(28 * mm, 257 * mm, data.full_name)

    # INVOICE NO AND DATE
    c.drawString(149 * mm, 198 * mm, invoice_no)
    c.drawString(137 * mm, 187 * mm, date_text)

    # BILL TO NAME
    c.drawString(52 * mm, 198 * mm,data.primary_traveller_name)  # Assuming the first traveller is the primary contact
    
    # PACKAGE DETAILS
    # c.drawString(25 * mm, 185 * mm, "1 Day Adventure Trek")
    c.drawString(124 * mm, 142 * mm, str(quantity))
    # if(amount == 1101 or amount == 1251): # Holi Offer Applied
    c.drawString(145 * mm, 142 * mm,str(base_price))
    c.drawString(173 * mm, 142 * mm, str(total))
    c.drawString(170 * mm, 104 * mm, str(total))   # Subtotal
    c.drawString(170 * mm, 89 * mm, str(discount))     # Discount
    c.drawString(170 * mm, 71 * mm, str(amount))   # Total

    # PAYMENT DETAILS
    c.drawString(75 * mm, 76 * mm, "UPI")
    c.drawString(75 * mm, 66 * mm, str(amount))
    c.drawString(75 * mm, 54 * mm, "0")
    # else:
    #     c.drawString(145 * mm, 142 * mm,str(amount))
    #     c.drawString(173 * mm, 142 * mm, str(amount))

    #     c.drawString(170 * mm, 104 * mm, str(amount))   # Subtotal
    #     c.drawString(170 * mm, 89 * mm, "0")     # Discount
    #     c.drawString(170 * mm, 71 * mm, str(amount))   # Total

    #     # PAYMENT DETAILS
    #     c.drawString(75 * mm, 76 * mm, "UPI")
    #     c.drawString(75 * mm, 66 * mm, str(amount))
    #     c.drawString(75 * mm, 54 * mm, "0")
    print(amount , type(amount))
    c.save()
    return file_path        

    # OTHERS (UPI)
    # c.drawString(25 * mm, 172 * mm, "UPI")
    # c.drawString(170 * mm, 172 * mm, "939")

    # SUMMARY (RIGHT SIDE)
    # c.drawString(170 * mm, 104 * mm, str(amount+201))   # Subtotal
    # c.drawString(170 * mm, 89 * mm, "Holi Offer")     # Discount
    # c.drawString(170 * mm, 71 * mm, str(amount))   # Total

    # # PAYMENT DETAILS
    # c.drawString(75 * mm, 76 * mm, "UPI")
    # c.drawString(75 * mm, 66 * mm, str(amount))
    # c.drawString(75 * mm, 54 * mm, "0")
    
## Ujjain Invoice Generation Function

def generate_ujjain_invoice(
    data,
    config,
):
    pricing_function = config["pricing_function"]
    base_price = config["base_price"]
    meal_preference = data.meal_preference
    

    quantity = data.total_people
    total_without_discount = base_price * quantity
    
    price_per_person = pricing_function(quantity, meal_preference)
    amount = quantity * price_per_person
    toatl_without_discount = amount
    if data.payment_status == "partial":
        amount = amount * 0.4
    discount = total_without_discount - amount
    
    file_name = f"invoice_{uuid.uuid4().hex[:8]}.pdf"
    invoices_folder = os.path.abspath(os.path.join(BASE_DIR, "../invoices"))
    os.makedirs(invoices_folder, exist_ok=True)

    file_path = os.path.join(invoices_folder, file_name)

    c = canvas.Canvas(file_path, pagesize=A4)
    width, height = A4

    c.drawImage(TEMPLATE_PATH, 0, 0, width=width, height=height)

    # invoice_no = f"INV-{uuid.uuid4().hex[:6].upper()}"
    invoice_no = f"INV-{data.id}"
    submitted_date = getattr(data, "submitted_at", None)
    date_text = str(submitted_date.date()) if submitted_date else "N/A"

    # USER NAME UNDER LOGO
    # c.drawString(28 * mm, 257 * mm, data.full_name)

    # INVOICE NO AND DATE
    c.drawString(149 * mm, 198 * mm, invoice_no)
    c.drawString(137 * mm, 187 * mm, date_text)

    # BILL TO NAME
    c.drawString(52 * mm, 198 * mm,data.primary_traveller_name)  # Assuming the first traveller is the primary contact
    
    # PACKAGE DETAILS
    # c.drawString(25 * mm, 185 * mm, "1 Day Adventure Trek")
    c.drawString(124 * mm, 142 * mm, str(quantity))
    # if(amount == 1101 or amount == 1251): # Holi Offer Applied
    c.drawString(145 * mm, 142 * mm,str(base_price))
    c.drawString(173 * mm, 142 * mm, str(total_without_discount))
    c.drawString(170 * mm, 104 * mm, str(total_without_discount))   # Subtotal
    c.drawString(170 * mm, 89 * mm, str(discount))     # Discount
    c.drawString(170 * mm, 71 * mm, str(amount))   # Total

    # PAYMENT DETAILS
    c.drawString(75 * mm, 76 * mm, "UPI")
    c.drawString(75 * mm, 66 * mm, str(amount))
    c.drawString(75 * mm, 54 * mm, str(toatl_without_discount - amount))
    # else:
    #     c.drawString(145 * mm, 142 * mm,str(amount))
    #     c.drawString(173 * mm, 142 * mm, str(amount))

    #     c.drawString(170 * mm, 104 * mm, str(amount))   # Subtotal
    #     c.drawString(170 * mm, 89 * mm, "0")     # Discount
    #     c.drawString(170 * mm, 71 * mm, str(amount))   # Total

    #     # PAYMENT DETAILS
    #     c.drawString(75 * mm, 76 * mm, "UPI")
    #     c.drawString(75 * mm, 66 * mm, str(amount))
    #     c.drawString(75 * mm, 54 * mm, "0")
    print(amount , type(amount))
    c.save()
    return file_path        
