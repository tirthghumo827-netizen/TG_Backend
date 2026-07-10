# -*- coding: utf-8 -*-
from fastapi import FastAPI ,  HTTPException , Response , status , Depends , APIRouter , Form , File , UploadFile 
import json
import uuid
from app import models , schema  
from sqlalchemy.orm import Session
from app.database import engine , get_db
from app.config import settings  
from app.utils.mail.odt_mail import send_booking_email , send_email_with_invoice , send_booking_declined_email 
import shutil, os
from fastapi import BackgroundTasks
from app.utils.invoice_generator import generate_invoice
from app.utils.supabase_uploads import upload_to_supabase
from app.utils.odt_pricing import get_price_per_person
from fastapi.responses import HTMLResponse

from urllib.parse import quote

router = APIRouter()

UPLOAD_DIR = "uploads/"
os.makedirs(UPLOAD_DIR, exist_ok=True)





@router.post("/odt_booking", status_code=status.HTTP_201_CREATED)
async def odt_booking(
    background_tasks: BackgroundTasks,
    travellers: str = Form(...),   # JSON string array
    meal_preference: str = Form(...),
    trek_date: str = Form(...) ,
    agree: bool = Form(...),
    payment_screenshot: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    # Parse travellers JSON
    
    travellers_list = json.loads(travellers)
    
    try:
        print("RAW travellers:", travellers)
        print(type(travellers))
        travellers_list = json.loads(travellers)

        if not isinstance(travellers_list, list):
            raise ValueError("Travellers must be a list")

    except Exception:
        raise HTTPException(
            status_code=400,
            detail="Invalid travellers data"
        )

    total_people = len(travellers_list)

    if total_people == 0:
        raise HTTPException(
            status_code=400,
            detail="At least one traveller required"
        )

    price_per_person = get_price_per_person(total_people , meal_preference)
    total_price = price_per_person * total_people

    if not total_price:
        raise HTTPException(
            status_code=400,
            detail="Invalid group size"
        )

    # Save screenshot
    file_location = None

    if payment_screenshot:
        unique_id = uuid.uuid4().hex
        file_name = f"booking_{unique_id}_{payment_screenshot.filename}"
        file_location = os.path.join(UPLOAD_DIR, file_name)

        with open(file_location, "wb") as buffer:
            shutil.copyfileobj(payment_screenshot.file, buffer)
    primary_email = travellers_list[0]["email_address"]
    primary_traveller_name = travellers_list[0]["full_name"]
    primary_traveller_contact = travellers_list[0]["contact_number"]
    # Create booking
    booking = models.ODT1(
        primary_email=primary_email,
        primary_traveller_name=primary_traveller_name,
        primary_traveller_contact=primary_traveller_contact,
        total_people=total_people,
        total_price=total_price,
        meal_preference=meal_preference,
        trek_date=trek_date, 
        agree=agree,
        payment_screenshot=file_location,
        status="pending"
    )

    db.add(booking)
    db.commit()
    db.refresh(booking)

    # Add travellers
    for traveller in travellers_list:
        traveller_data = models.ODTTraveller(
            booking_id=booking.id,
            full_name=traveller["full_name"],
            email_address=traveller["email_address"],
            age=traveller["age"],
            gender=traveller["gender"],
            contact_number=traveller["contact_number"],
            whatsapp_number=traveller["whatsapp_number"],
            college_name=traveller["college_name"],
            pick_up_loc=traveller["pick_up_loc"],
            drop_loc=traveller["drop_loc"],
            trip_exp_level=traveller.get("trip_exp_level"),
            medical_details=traveller.get("medical_details")
        )

        db.add(traveller_data)


    db.commit()

    background_tasks.add_task(
    send_booking_email,
    booking.id,
    db,
    file_location
    )

    return {
        "message": "Booking successful",
        "booking_id": booking.id,
        "total_people": total_people,
        "total_price": total_price
    }



def _status_page(
    title: str,
    message: str,
    color: str,
    icon: str,
    whatsapp_url: str | None = None,
    whatsapp_label: str = "Send WhatsApp Message"
) -> HTMLResponse:
    whatsapp_button = ""
    if whatsapp_url:
        whatsapp_button = f"""
    <hr class="divider">
    <a href="{whatsapp_url}" target="_blank" class="btn-whatsapp">
      <span>📱</span> {whatsapp_label}
    </a>"""

    html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}</title>
  <style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
      background: #f4f4f4;
      min-height: 100vh;
      display: flex;
      align-items: center;
      justify-content: center;
    }}
    .card {{
      background: #ffffff;
      border-radius: 12px;
      border: 1px solid #e0e0e0;
      padding: 48px 40px;
      text-align: center;
      max-width: 420px;
      width: 90%;
    }}
    .icon {{
      width: 64px;
      height: 64px;
      border-radius: 50%;
      background: {color}15;
      display: flex;
      align-items: center;
      justify-content: center;
      margin: 0 auto 24px;
      font-size: 28px;
    }}
    .brand {{
      font-size: 13px;
      font-weight: 600;
      color: #9ca3af;
      letter-spacing: 0.5px;
      text-transform: uppercase;
      margin-bottom: 20px;
    }}
    .brand span {{ color: #f97316; }}
    h1 {{
      font-size: 22px;
      font-weight: 700;
      color: #111827;
      margin-bottom: 10px;
    }}
    p {{
      font-size: 14px;
      color: #6b7280;
      line-height: 1.6;
    }}
    .divider {{
      border: none;
      border-top: 1px solid #e5e7eb;
      margin: 28px 0;
    }}
    .footer {{
      font-size: 12px;
      color: #9ca3af;
      margin-top: 24px;
    }}
    .btn-whatsapp {{
      display: inline-flex;
      align-items: center;
      gap: 8px;
      background: #25D366;
      color: white;
      padding: 12px 24px;
      border-radius: 8px;
      text-decoration: none;
      font-size: 14px;
      font-weight: 600;
      transition: background 0.2s;
    }}
    .btn-whatsapp:hover {{ background: #1ebe5d; }}
  </style>
</head>
<body>
  <div class="card">
    <div class="brand">Tirth<span>Ghumo</span></div>
    <div class="icon">{icon}</div>
    <h1>{title}</h1>
    <p>{message}</p>
    {whatsapp_button}
    <hr class="divider">
    <div class="footer">This action has been recorded. You may close this tab.</div>
  </div>
</body>
</html>
"""
    return HTMLResponse(content=html, media_type="text/html; charset=utf-8")
 

def _build_odt_whatsapp_message(booking) -> str:
    return f"""
Thank you {booking.primary_traveller_name} Ji for registering for the One Day Trek ! 

Your registration is successful.  

Please check your email for the confirmation and trek details  . 

Join the official WhatsApp group using the link below:
https://chat.whatsapp.com/JEMGyip6DoOF0PjWAxmGbF?s=sh&p=a&ilr=0

Make sure you have raised the request to join the official WhatsApp group as all updates, packing lists, and important info will be shared there before the trek .

See you on the trek ! 

Team TirthGhumo
""".strip()


@router.get("/odt/approve")
def approve_booking(
    booking_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    booking = db.query(models.ODT1).filter(
        models.ODT1.id == booking_id
    ).first()

    if not booking:
        raise HTTPException(404, "Booking not found")

    invoice_path = generate_invoice(booking)
    booking.status = "approved"
    db.commit()
    db.refresh(booking)

    background_tasks.add_task(
        send_email_with_invoice,
        booking.primary_email,
        booking,
        invoice_path
    )

    whatsapp_message = _build_odt_whatsapp_message(booking)
    whatsapp_url = f"https://wa.me/91{booking.primary_traveller_contact}?text={quote(whatsapp_message, safe='', encoding='utf-8')}"

    return _status_page(
        title="Booking Approved",
        message=f"Booking <strong>#TG-{booking_id}</strong> has been approved. "
                f"The confirmation email and invoice have been sent to the customer.",
        color="#16a34a",
        icon="✓",
        whatsapp_url=whatsapp_url,
        whatsapp_label="Send WhatsApp to Customer"
    )


@router.get("/odt/decline")
def decline_booking(
    booking_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    booking = db.query(models.ODT1).filter(
        models.ODT1.id == booking_id
    ).first()

    if not booking:
        raise HTTPException(404, "Booking not found")

    booking.status = "declined"
    db.commit()

    background_tasks.add_task(
        send_booking_declined_email,
        booking,
        booking.primary_email
    )

    # No WhatsApp button on decline — email handles it
    return _status_page(
        title="Booking Declined",
        message=f"Booking <strong>#TG-{booking_id}</strong> has been declined. "
                f"The customer has been notified via email.",
        color="#dc2626",
        icon="✕"
    )