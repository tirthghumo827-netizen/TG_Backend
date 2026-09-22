# -*- coding: utf-8 -*-
from fastapi import FastAPI ,  HTTPException , Response , status , Depends , APIRouter , Form , File , UploadFile 
import json
import uuid
from app import models , schema  
from sqlalchemy.orm import Session
from app.database import engine , get_db
from app.config import settings  
from app.utils.mail.odt_mail import send_booking_email , send_email_with_invoice , send_booking_declined_email 
from app.utils.mail.ujjain_omkareshwar import ujjain_approval_email , ujjain_declined_email
import shutil, os
from fastapi import BackgroundTasks
from app.utils.invoice_generator import generate_invoice , generate_ujjain_invoice
from app.utils.supabase_uploads import upload_to_supabase
from app.utils.odt_pricing import get_price_per_person_budhni, get_price_per_person_halali , get_price_per_person_ujjain , get_price_per_person_heritage
from fastapi.responses import HTMLResponse
from app.services.heritage_coupon_service import (
    get_or_create_heritage_trek_coupon
)

from app.utils.mail.odt_mail import (
    send_heritage_trek_coupon_email
)
from urllib.parse import quote
import logging

logger = logging.getLogger(__name__)
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
    "approval_mail" : send_email_with_invoice,
    "decline_mail" : send_booking_declined_email
}
HALALI_CONFIG = {
    "name": "Halali Trek",
    "booking_model": models.ChotaPachmarhi,
    "traveller_model": models.ChotaPachmarhiTraveller,
    "pricing_function": get_price_per_person_halali,
    "base_price": 1199,
    "approve_route": "/odt/halali/approve",
    "decline_route": "/odt/halali/decline",
    "approval_mail" : send_email_with_invoice,
    "decline_mail" : send_booking_declined_email
}
UJJAIN_CONFIG = {
    "name": "Ujjain Omkareshwar Trip",
    "booking_model": models.UjjainOmkareshwarTrip,
    "traveller_model": models.UjjainOmkareshwarTraveller,
    "pricing_function": get_price_per_person_ujjain,  # Assuming same pricing function for Ujjain
    "base_price": 5599,
    "approve_route": "/ujjain/approve",
    "decline_route": "/ujjain/decline",
    "approval_mail" : ujjain_approval_email,
    "decline_mail" : ujjain_declined_email
}
HERITAGE_CONFIG = { # One Day Heritage Trip Configurations
    "name": "Heritage Trip",
    "booking_model": models.HeritageTrip,
    "traveller_model": models.HeritageTraveller,
    "pricing_function": get_price_per_person_heritage,  # Assuming same pricing function for Heritage
    "base_price": 999, 
    "approve_route": "/heritage/approve",
    "decline_route": "/heritage/decline",
    "approval_mail" : send_email_with_invoice,
    "decline_mail" : send_booking_declined_email
    
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

## Ujjain booking helper function 
def create_ujjain_booking(
    *,
    db: Session,
    travellers_list: list,
    meal_preference: str,
    trek_date: str,
    payment_status: str,
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

    price_per_person = pricing_function(total_people, meal_preference )
    total_price = price_per_person * total_people

    if not total_price:
        raise HTTPException(
            status_code=400,
            detail="Invalid group size"
        )
    if payment_status == "partial" :
        total_price = total_price  * 0.4 
    else :
        payment_status = "full"

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
        payment_status=payment_status,
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

    if booking.status != "pending":
        raise HTTPException(
            400,
            f"Booking status is '{booking.status}', cannot approve."
        )
    if config["name"] == "Ujjain Omkareshwar Trip":
        invoice_path = generate_ujjain_invoice(
            booking,
            config
        )
    else:
        invoice_path = generate_invoice(
            booking,
            config
        )

    booking.status = "approved"

    db.commit()
    db.refresh(booking)

    background_tasks.add_task(
        config["approval_mail"],
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

    if booking.status != "pending":
        raise HTTPException(
            400,
            f"Booking status is '{booking.status}', cannot decline."
        )
    booking.status = "declined"

    db.commit()

    background_tasks.add_task(
        config["decline_mail"],
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
    payment_status: str = Form(...),
    agree: bool = Form(...),
    payment_screenshot: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    # Parse travellers JSON
    
    travellers_list = json.loads(travellers)
    
    booking, file_location, total_people, total_price = create_ujjain_booking(
    db=db,
    travellers_list=travellers_list,
    meal_preference=meal_preference,
    trek_date=trek_date,
    agree=agree,
    payment_status=payment_status,
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

@router.post("/heritage_booking", status_code=status.HTTP_201_CREATED)
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
    config=HERITAGE_CONFIG
    )

    background_tasks.add_task(
        send_booking_email,
        booking.id,
        db,
        HERITAGE_CONFIG,
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
    "2026-09-19" : "https://chat.whatsapp.com/FyqDe4aK99TGxhhgbd9pMX?s=sw&p=a&ilr=4", # Ujjain Batch 1 
    "2026-09-26" : "https://chat.whatsapp.com/LUSThbpdQ9D5kdnchJ5gEv?s=sw&p=a&ilr=4", # Ujjain Batch 2
    "2026-10-04" : "https://chat.whatsapp.com/BMaYQX8lefZJ5EMKttOjTC?s=cl&p=i&mlu=4&ilr=4", # One day heritage trip  1
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
Thank you {booking.primary_traveller_name} Ji for registering for Trip ! 

Your registration is successful.  

Please check your email for the confirmation and trip details  . 

Join the official WhatsApp group using the link below:
{group_link}

Make sure you have raised the request to join the official WhatsApp group as all updates, packing lists, and important info will be shared there before the trip .

See you on the trip ! 

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
# @router.get("/heritage/approve")
# def approve_booking(
#     booking_id: int,
#     background_tasks: BackgroundTasks,
#     db: Session = Depends(get_db),
# ):
#     return approve_booking_helper(
#         booking_id,
#         background_tasks,
#         db,
#         config=HERITAGE_CONFIG
#     )

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
        config=BUDHNI_CONFIG,
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
        config=HALALI_CONFIG,
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
        config=UJJAIN_CONFIG,
    )
# @router.get("/heritage/decline")
# def decline_booking(
#     booking_id: int,
#     background_tasks: BackgroundTasks,
#     db: Session = Depends(get_db),
# ):
#     return decline_booking_helper(
#         booking_id,
#         background_tasks,
#         db,
#         config=HERIATGE_CONFIG,
#     )

# ================= HERITAGE APPROVAL ROUTE =================

@router.get("/heritage/approve")
def approve_heritage_booking(
    booking_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    # Fetch Heritage booking
    booking = (
        db.query(models.HeritageTrip)
        .filter(models.HeritageTrip.id == booking_id)
        .first()
    )

    if not booking:
        raise HTTPException(
            status_code=404,
            detail="Heritage booking not found",
        )

    if booking.status != "pending":
        raise HTTPException(
            status_code=400,
            detail=f"Booking status is '{booking.status}', cannot approve.",
        )

    try:
        # Generate invoice
        invoice_path = generate_invoice(booking, HERITAGE_CONFIG)

        # Approve booking
        booking.status = "approved"

        # Generate or retrieve Heritage → Trek coupon
        coupon, coupon_created = get_or_create_heritage_trek_coupon(
            db=db,
            email=booking.primary_email,
            heritage_booking_id=booking.id,
        )

        # Save approval changes
        db.commit()
        db.refresh(booking)

    except Exception:
        db.rollback()

        # Print the actual error in the FastAPI terminal
        logger.exception(
            "Heritage approval failed for booking ID %s",
            booking_id,
        )

        raise HTTPException(
            status_code=500,
            detail="Could not approve Heritage booking.",
        )

    # Existing approval email with invoice
    background_tasks.add_task(
        HERITAGE_CONFIG["approval_mail"],
        booking.primary_email,
        booking,
        invoice_path,
    )

    # Send coupon email only if a new coupon was created
    if coupon_created:
        background_tasks.add_task(
            send_heritage_trek_coupon_email,
            booking.primary_email,
            coupon.coupon_code,
            coupon.expires_at,
        )

    # WhatsApp link
    whatsapp_message = _build_odt_whatsapp_message(booking)

    whatsapp_url = (
        f"https://wa.me/91{booking.primary_traveller_contact}"
        f"?text={quote(whatsapp_message, safe='', encoding='utf-8')}"
    )

    return _status_page(
        title="Heritage Booking Approved",
        message=(
            f"Heritage booking <strong>#TG-{booking_id}</strong> "
            "has been approved. Confirmation email and invoice have been "
            "queued. Heritage → Trek coupon email has also been queued "
            "if a new coupon was generated."
        ),
        color="#16a34a",
        icon="✓",
        whatsapp_url=whatsapp_url,
        whatsapp_label="Send WhatsApp to Customer",
    )


# ================= HERITAGE DECLINE ROUTE =================

@router.get("/heritage/decline")
def decline_heritage_booking(
    booking_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    # Fetch Heritage booking
    booking = (
        db.query(models.HeritageTrip)
        .filter(models.HeritageTrip.id == booking_id)
        .first()
    )

    if not booking:
        raise HTTPException(status_code=404, detail="Heritage booking not found")

    if booking.status != "pending":
        raise HTTPException(
            status_code=400,
            detail=f"Booking status is '{booking.status}', cannot decline."
        )

    # Decline booking
    booking.status = "declined"
    db.commit()
    db.refresh(booking)

    # Send existing decline email
    background_tasks.add_task(
        HERITAGE_CONFIG["decline_mail"],
        booking,
        booking.primary_email,
    )

    return _status_page(
        title="Heritage Booking Declined",
        message=(
            f"Heritage booking <strong>#TG-{booking_id}</strong> "
            "has been declined. The customer has been notified via email."
        ),
        color="#dc2626",
        icon="✕",
    )