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
from app.utils.odt_pricing import get_price_per_person_budhni, get_price_per_person_halali , get_price_per_person_ujjain
from fastapi.responses import HTMLResponse

from urllib.parse import quote

router = APIRouter()

UPLOAD_DIR = "uploads/"
os.makedirs(UPLOAD_DIR, exist_ok=True)

BUDHNI_CONFIG = {
    "name": "Budhni Trek",
    "booking_model": models.ODT1,
    "traveller_model": models.ODTTraveller,
    "pricing_function": get_price_per_person_budhni,
    "base_price": 1351,
    "approve_route": "/odt/budhni/approve",
    "decline_route": "/odt/budhni/decline",
}
HALALI_CONFIG = {
    "name": "Halali Trek",
    "booking_model": models.ChotaPachmarhi,
    "traveller_model": models.ChotaPachmarhiTraveller,
    "pricing_function": get_price_per_person_halali,
    "base_price": 1199,
    "approve_route": "/odt/halali/approve",
    "decline_route": "/odt/halali/decline",
}
UJJAIN_CONFIG = {
    "name": "Ujjain Omkareshwar Trip",
    "booking_model": models.UjjainOmkareshwarTrip,
    "traveller_model": models.UjjainOmkareshwarTraveller,
    "pricing_function": get_price_per_person_ujjain,  # Assuming same pricing function for Ujjain
    "base_price": 999,
    "approve_route": "/odt/ujjain/approve",
    "decline_route": "/odt/ujjain/decline",
}

def create_odt_booking(
    *,
    db: Session,
    travellers_list: list,
    meal_preference: str,
    trek_date: str,
    agree: bool,
    payment_screenshot: UploadFile,
    config: dict,
):
    total_people = len(travellers_list)
    model = config["booking_model"]
    pricing_function = config["pricing_function"]
    traveller_model = config["traveller_model"]
    if total_people == 0:
        raise HTTPException(
            status_code=400,
            detail="At least one traveller required"
        )

    price_per_person = pricing_function(total_people, meal_preference)
    total_price = price_per_person * total_people

    if not total_price:
        raise HTTPException(
            status_code=400,
            detail="Invalid group size"
        )

    file_location = None

    if payment_screenshot:
        unique_id = uuid.uuid4().hex
        file_name = f"booking_{unique_id}_{payment_screenshot.filename}"
        file_location = os.path.join(UPLOAD_DIR, file_name)

        with open(file_location, "wb") as buffer:
            shutil.copyfileobj(payment_screenshot.file, buffer)

    booking = model(
        primary_email=travellers_list[0]["email_address"],
        primary_traveller_name=travellers_list[0]["full_name"],
        primary_traveller_contact=travellers_list[0]["contact_number"],
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

    for traveller in travellers_list:
        db.add(
            traveller_model(
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
                medical_details=traveller.get("medical_details"),
            )
        )

    db.commit()

    return booking, file_location, total_people, total_price

def approve_booking_helper(
    booking_id: int,
    background_tasks: BackgroundTasks,
    db: Session,
    config: dict,
):
    booking = db.query(config["booking_model"]).filter(
    config["booking_model"].id == booking_id
    ).first()

    if not booking:
        raise HTTPException(404, "Booking not found")

    invoice_path = generate_invoice(
        booking,
        config
    )

    booking.status = "approved"

    db.commit()
    db.refresh(booking)

    background_tasks.add_task(
        send_email_with_invoice,
        booking.primary_email,
        booking,
        invoice_path,
    )

    whatsapp_message = _build_odt_whatsapp_message(booking)

    whatsapp_url = (
        f"https://wa.me/91{booking.primary_traveller_contact}"
        f"?text={quote(whatsapp_message, safe='', encoding='utf-8')}"
    )

    return _status_page(
        title="Booking Approved",
        message=f"Booking <strong>#TG-{booking_id}</strong> has been approved. "
                f"The confirmation email and invoice have been sent to the customer.",
        color="#16a34a",
        icon="✓",
        whatsapp_url=whatsapp_url,
        whatsapp_label="Send WhatsApp to Customer",
    )
def decline_booking_helper(
    booking_id: int,
    background_tasks: BackgroundTasks,
    db: Session,
    booking_model,
):
    booking = (
        db.query(booking_model)
        .filter(booking_model.id == booking_id)
        .first()
    )

    if not booking:
        raise HTTPException(404, "Booking not found")

    booking.status = "declined"

    db.commit()

    background_tasks.add_task(
        send_booking_declined_email,
        booking,
        booking.primary_email,
    )

    return _status_page(
        title="Booking Declined",
        message=f"Booking <strong>#TG-{booking_id}</strong> has been declined. "
                f"The customer has been notified via email.",
        color="#dc2626",
        icon="✕",
    )


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
    
    booking, file_location, total_people, total_price = create_odt_booking(
    db=db,
    travellers_list=travellers_list,
    meal_preference=meal_preference,
    trek_date=trek_date,
    agree=agree,
    payment_screenshot=payment_screenshot,
    config=BUDHNI_CONFIG
)

    background_tasks.add_task(
        send_booking_email,
        booking.id,
        db,
        BUDHNI_CONFIG,
        file_location,
    )

    return {
        "message": "Booking successful",
        "booking_id": booking.id,
        "total_people": total_people,
        "total_price": total_price,
    }

# Chota Pachmarhi Route 
@router.post("/odt/halali", status_code=status.HTTP_201_CREATED)
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
    
    booking, file_location, total_people, total_price = create_odt_booking(
    db=db,
    travellers_list=travellers_list,
    meal_preference=meal_preference,
    trek_date=trek_date,
    agree=agree,
    payment_screenshot=payment_screenshot,
    config=HALALI_CONFIG
)

    background_tasks.add_task(
        send_booking_email,
        booking.id,
        db,
        HALALI_CONFIG,
        file_location,
    )

    return {
        "message": "Booking successful",
        "booking_id": booking.id,
        "total_people": total_people,
        "total_price": total_price,
    }
@router.post("/ujjain_omkareshwar", status_code=status.HTTP_201_CREATED)
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
    
    booking, file_location, total_people, total_price = create_odt_booking(
    db=db,
    travellers_list=travellers_list,
    meal_preference=meal_preference,
    trek_date=trek_date,
    agree=agree,
    payment_screenshot=payment_screenshot,
    config=UJJAIN_CONFIG
)

    background_tasks.add_task(
        send_booking_email,
        booking.id,
        db,
        UJJAIN_CONFIG,
        file_location,
    )

    return {
        "message": "Booking successful",
        "booking_id": booking.id,
        "total_people": total_people,
        "total_price": total_price,
    }



ODT_WHATSAPP_GROUPS = {
    # "2026-07-12": "https://chat.whatsapp.com/JEMGyip6DoOF0PjWAxmGbF?s=sh&p=a&ilr=0", #B9
    # "2026-07-26": "https://chat.whatsapp.com/JkflPYXwYqzIfVEe8rmMUf?s=cl&p=i&mlu=0&ilr=0",  # B10
    # "2026-08-22": "https://chat.whatsapp.com/HIwU7EwT5iyAkQhX73ZP81?s=cl&p=i&mlu=0&ilr=0" , # Halali Trek
    "2026-09-05" : "https://chat.whatsapp.com/G9cEuK3Vb9b4KtizF2TbVu?s=sw&p=a&ilr=4", # Halali Batch 2 
    "2026-09-12" : "https://chat.whatsapp.com/FyqDe4aK99TGxhhgbd9pMX?s=sw&p=a&ilr=4", # Ujjain Batch 1 
    # add more trek dates here as needed
}

DEFAULT_ODT_WHATSAPP_GROUP = "https://chat.whatsapp.com/JkflPYXwYqzIfVEe8rmMUf?s=cl&p=i&mlu=0&ilr=0"


def _get_whatsapp_group_link(trek_date) -> str:
    if hasattr(trek_date, "isoformat"):
        trek_date = trek_date.isoformat()
    else:
        trek_date = str(trek_date).strip()[:10]
    return ODT_WHATSAPP_GROUPS.get(trek_date, DEFAULT_ODT_WHATSAPP_GROUP)

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
    print(f"DEBUG trek_date value: {repr(booking.trek_date)}")
    group_link = _get_whatsapp_group_link(booking.trek_date)
    return f"""
Thank you {booking.primary_traveller_name} Ji for registering for the One Day Trek ! 

Your registration is successful.  

Please check your email for the confirmation and trek details  . 

Join the official WhatsApp group using the link below:
{group_link}

Make sure you have raised the request to join the official WhatsApp group as all updates, packing lists, and important info will be shared there before the trek .

See you on the trek ! 

Team TirthGhumo
""".strip()


@router.get("/odt/budhni/approve")
def approve_booking(
    booking_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    return approve_booking_helper(
        booking_id,
        background_tasks,
        db,
        config=BUDHNI_CONFIG
    )
@router.get("/odt/halali/approve")
def approve_chota_booking(
    booking_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    return approve_booking_helper(
        booking_id,
        background_tasks,
        db,
        config=HALALI_CONFIG
    )
@router.get("/ujjain/approve")
def approve_chota_booking(
    booking_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    return approve_booking_helper(
        booking_id,
        background_tasks,
        db,
        config=UJJAIN_CONFIG
    )

@router.get("/odt/budhni/decline")
def decline_booking(
    booking_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    return decline_booking_helper(
        booking_id,
        background_tasks,
        db,
        models.ODT1,
    )
@router.get("/odt/halali/decline")
def decline_chota_booking(
    booking_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    return decline_booking_helper(
        booking_id,
        background_tasks,
        db,
        models.ChotaPachmarhi,
    )
@router.get("/ujjain/decline")
def decline_chota_booking(
    booking_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    return decline_booking_helper(
        booking_id,
        background_tasks,
        db,
        models.ChotaPachmarhi,
    )

