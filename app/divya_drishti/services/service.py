from sqlalchemy.orm import Session
from datetime import datetime, timezone , date , time , timedelta
import qrcode
import asyncio
import requests
import os
from zoneinfo import ZoneInfo
from fastapi import HTTPException, status , BackgroundTasks, UploadFile 
from typing import List
from app.utils.supabase_uploads import upload_to_supabase
from ..models import DarshanBooking, DarshanSession, DarshanReview  , SessionExtension , DarshanParticipant , SaarthiSessionAssignment
from ..schema import DarshanBookingCreate, DarshanReviewCreate , CompleteBookingDetails , SessionExtensionCreateRequest
from app.utils.mail.vr_admin_mail import send_admin_vr_darshan_email
from app.utils.mail.vr_user_mail import send_user_approval_mail  , send_user_decline_mail
import qrcode
import io
from app.utils.supabase_uploads import upload_to_supabase_bytes
from app.utils.whatsapp.divya_drishti import send_whatsapp_message
from math import ceil
from ..slots import WEEKDAY_SLOTS , WEEKEND_SLOTS , get_day_level_slots


# def get_available_slots(
#     db: Session,
#     selected_date: date
# ):

#     slots = (
#         WEEKEND_SLOTS
#         if selected_date.weekday() >= 5
#         else WEEKDAY_SLOTS
#     )

#     bookings = db.query(
#         DarshanBooking
#     ).filter(
#         DarshanBooking.slot_date == selected_date,
#         DarshanBooking.status != "rejected"
#     ).all()

#     result = []

#     for slot in slots:

#         slot_start = datetime.combine(
#             selected_date,
#             datetime.strptime(
#                 slot,
#                 "%H:%M"
#             ).time()
#         )

#         slot_end = slot_start + timedelta(
#             minutes=30
#         )

#         available = True

#         for booking in bookings:

#             if (
#                 booking.start_datetime is None
#                 or
#                 booking.end_datetime is None
#             ):
#                 continue

#             overlap = (
#                 slot_start < booking.end_datetime
#                 and
#                 slot_end > booking.start_datetime
#             )

#             if overlap:
#                 available = False
#                 break

#         result.append({
#             "slot_time": slot,
#             "available": available
#         })

#     return result




def get_available_slots(
    db: Session,
    selected_date: date
):

    base_slots = (
        WEEKEND_SLOTS
        if selected_date.weekday() >= 5
        else WEEKDAY_SLOTS
    )

    # NEW: narrow down to slots at least one executive can actually cover
    slots = get_day_level_slots(selected_date)

    if not slots:
        return []

    bookings = db.query(
        DarshanBooking
    ).filter(
        DarshanBooking.slot_date == selected_date,
        DarshanBooking.status != "rejected"
    ).all()

    result = []

    for slot in slots:

        slot_start = datetime.combine(
            selected_date,
            datetime.strptime(
                slot,
                "%H:%M"
            ).time()
        )

        slot_end = slot_start + timedelta(
            minutes=30
        )

        available = True

        for booking in bookings:

            if (
                booking.start_datetime is None
                or
                booking.end_datetime is None
            ):
                continue

            overlap = (
                slot_start < booking.end_datetime
                and
                slot_end > booking.start_datetime
            )

            if overlap:
                available = False
                break

        result.append({
            "slot_time": slot,
            "available": available
        })

    return result

def book_session(
    db: Session,
    booking_in: DarshanBookingCreate,
    payment_screenshot: UploadFile,
    background_tasks: BackgroundTasks,
) -> DarshanBooking:

    

    payment_screenshot_url = None

    if payment_screenshot:
        try:
            payment_screenshot_url = upload_to_supabase(
                payment_screenshot,
                folder="vr_darshan_payments"
            )
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Payment upload failed: {str(e)}"
            )

    

    slots = (
        WEEKEND_SLOTS
        if booking_in.slot_date.weekday() >= 5
        else WEEKDAY_SLOTS
    )

    selected_slot = booking_in.slot_time.strip()

    if selected_slot not in slots:
        raise HTTPException(
            status_code=400,
            detail="Invalid slot selected"
        )

    

    occupied_units = ceil(
        booking_in.persons / 2
    )

    booking_minutes = occupied_units * 30

    buffer_minutes = 60

    total_minutes = booking_minutes + buffer_minutes

    

    start_dt = datetime.combine(
        booking_in.slot_date,
        datetime.strptime(
            selected_slot,
            "%H:%M"
        ).time()
    )

    end_dt = start_dt + timedelta(
        minutes=total_minutes
    )

    # -------------------------
    # Check overlap
    # -------------------------

    existing_bookings = db.query(
        DarshanBooking
    ).filter(
        DarshanBooking.slot_date == booking_in.slot_date,
        DarshanBooking.status != "rejected"
    ).all()

    for booking in existing_bookings:
        if(
        booking.start_datetime is None
        or
        booking.end_datetime is None
        ):
            continue

        overlap = (
            start_dt < booking.end_datetime
            and
            end_dt > booking.start_datetime
        )

        if overlap:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Selected slot unavailable. "
                    "Required booking duration or "
                    "buffer overlaps another booking."
                )
            )
    # -------------------------
    # Create booking
    # -------------------------

    new_booking = DarshanBooking(
        full_name=booking_in.full_name,
        contact_number=booking_in.contact_number,
        whatsapp_number=booking_in.whatsapp_number,
        address=booking_in.address,
        persons=booking_in.persons,
        slot_date=booking_in.slot_date,
        slot_time=selected_slot,
        occupied_units=occupied_units,
        start_datetime=start_dt,
        end_datetime=end_dt,
        status="pending",
        payment_status=booking_in.payment_status,
        payment_screenshot=payment_screenshot_url,
    )

    db.add(new_booking)

    try:
        db.commit()
        db.refresh(new_booking)

        background_tasks.add_task(
            send_admin_vr_darshan_email,
            new_booking
        )

    except Exception as e:
        db.rollback()

        raise HTTPException(
            status_code=500,
            detail=f"Booking creation failed: {str(e)}"
        )

    return new_booking


def complete_booking_details(
    db: Session,
    booking_id: int,
    details: CompleteBookingDetails,
    
   
):
    booking = db.query(DarshanBooking).filter(
        DarshanBooking.id == booking_id
    ).first()

    if not booking:
        raise HTTPException(
            status_code=404,
            detail="Booking not found"
        )

    if (booking.persons % 2 == 0)and len(details.participants) > booking.persons :
        raise HTTPException(
            status_code=400,
            detail=f"Expected {booking.persons}  participants"
        )
    for p in details.participants:
        participant = DarshanParticipant(
            booking_id=booking.id,
            full_name=p.full_name,
            age=p.age,
            darshan_name=p.darshan_name,
            is_extension=False
        )
        db.add(participant)
    
    


    db.commit()
    db.refresh(booking)

    return booking
def get_booking(db: Session, booking_id: int): ## for mail (admin gets this detail)
    booking = (
        db.query(DarshanBooking)
        .filter(DarshanBooking.id == booking_id)
        .first()
    )

    if not booking:
        raise HTTPException(404, "Booking not found")

    return booking

def get_booking_details(
    db: Session,
    booking_id: int
):

    booking = db.query(
        DarshanBooking
    ).filter(
        DarshanBooking.id == booking_id
    ).first()

    if not booking:
        raise HTTPException(
            status_code=404,
            detail="Booking not found"
        )

    participants = db.query(
        DarshanParticipant
    ).filter(
        DarshanParticipant.booking_id == booking_id
    ).all()

    sessions = db.query(
        DarshanSession
    ).filter(
        DarshanSession.booking_id == booking_id
    ).all()

    reviews = db.query(
        DarshanReview
    ).filter(
        DarshanReview.booking_id == booking_id
    ).all()

    return {
    "booking_id": booking.id,
    "full_name": booking.full_name,
    "contact_number": booking.contact_number,
    "whatsapp_number": booking.whatsapp_number,
    "address": booking.address,
    "persons": booking.persons,
    "slot_date": booking.slot_date,
    "slot_time": booking.slot_time,
    "status": booking.status,
    "payment_status": booking.payment_status,
    "qr_code": booking.qr_code,
 
    "participants": [
        {
            "id": p.id,
            "full_name": p.full_name,
            "age": p.age,
            "darshan_name": p.darshan_name,
            "is_extension": p.is_extension
        }
        for p in participants
    ],

    "sessions": [
        {
            "id": s.id,
            "start_time": s.start_time,
            "end_time": s.end_time,
            "status": s.status
        }
        for s in sessions
    ]
}

def approve_booking(
    db: Session,
    booking_id: int,
    executive_id: int,
    background_tasks: BackgroundTasks,
    distance_km: float,
) -> DarshanBooking:
    booking = db.query(DarshanBooking).filter(DarshanBooking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail=f"Booking {booking_id} not found")

    if booking.status == "rejected":
        raise HTTPException(
            status_code=400,
            detail="Rejected bookings cannot be assigned."
        )
    # Generate QR code in memory (no local file)
    qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=10, border=4)
    qr.add_data(f"divya_drishti_booking_{booking_id}")
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)

    try:
        qr_code_url = upload_to_supabase_bytes(
            file_bytes=buffer,
            filename=f"booking_{booking_id}.png",
            content_type="image/png",
            folder="vr_darshan_qrcodes"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"QR upload failed: {str(e)}")

    booking.qr_code = qr_code_url
    booking.status = "approved"

    # Travel amount — same slab logic used in executive.update_distance
    if distance_km <= 40:
        travel_amount = distance_km * 5
    else:
        travel_amount = distance_km * 6

    assignment = SaarthiSessionAssignment(
        booking_id=booking.id,
        executive_id=executive_id,
        status="assigned",
        distance_km=distance_km,
        travel_amount=travel_amount,
        net_amount=travel_amount,   # extension_amount/deductions are 0 at creation
    )

    db.add(assignment)

    try:
        db.commit()
        db.refresh(booking)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to approve booking: {str(e)}")

    return booking


def reject_booking(db: Session, booking_id: int) -> DarshanBooking:
    booking = db.query(DarshanBooking).filter(DarshanBooking.id == booking_id).first()
    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Booking with ID {booking_id} not found"
        )
    
    if booking.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Only pending bookings can be rejected. Current status: {booking.status}"
        )
    
    booking.status = "rejected"
    
    try:
        db.commit()
        db.refresh(booking)
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reject booking: {str(e)}"
        )
        
    return booking


def verify_qr(db: Session, qr_data: str) -> DarshanBooking:
    if not qr_data.startswith("divya_drishti_booking_"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid QR code data format"
        )
    
    try:
        booking_id = int(qr_data.split("_")[-1])
    except (ValueError, IndexError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid booking ID inside QR code"
        )
        
    booking = db.query(DarshanBooking).filter(DarshanBooking.id == booking_id).first()
    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Booking associated with the QR code (ID {booking_id}) not found"
        )
        
    if booking.status != "approved":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Booking QR verification failed. Booking status must be 'approved'. Current status: {booking.status}"
        )
        
    booking.status = "verified"
    
    try:
        db.commit()
        db.refresh(booking)
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update booking verification status: {str(e)}"
        )
        
    return booking


def start_session(db: Session, booking_id: int) -> DarshanSession:
    booking = db.query(DarshanBooking).filter(DarshanBooking.id == booking_id).first()
    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Booking with ID {booking_id} not found"
        )
        
    if booking.status != "verified":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot start session. Booking must be verified first. Current status: {booking.status}"
        )
        
    # Check if there is already an active session
    existing_session = db.query(DarshanSession).filter(
        DarshanSession.booking_id == booking_id,
        DarshanSession.status == "active"
    ).first()
    
    if existing_session:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An active session already exists for this booking."
        )
        
    new_session = DarshanSession(
        booking_id=booking_id,
        start_time= datetime.now(ZoneInfo("Asia/Kolkata")),
        status="active"
    )
    
    booking.status = "started"
    assignment = (
    db.query(SaarthiSessionAssignment)
    .filter(
        SaarthiSessionAssignment.booking_id == booking_id
    )
    .first()
    )

    if assignment:
        assignment.status = "started"
        assignment.started_at = datetime.now(ZoneInfo("Asia/Kolkata"))
    
    db.add(new_session)
    try:
        db.commit()
        db.refresh(new_session)
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start session: {str(e)}"
        )
        
    return new_session


def end_session(db: Session, booking_id: int) -> DarshanSession:
    booking = db.query(DarshanBooking).filter(DarshanBooking.id == booking_id).first()
    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Booking with ID {booking_id} not found"
        )
        
    session = db.query(DarshanSession).filter(
        DarshanSession.booking_id == booking_id,
        DarshanSession.status == "active"
    ).first()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No active session found for booking ID {booking_id}"
        )
        
    end_time =  datetime.now(ZoneInfo("Asia/Kolkata"))
    session.end_time = end_time
    session.status = "completed"

    assignment = (
    db.query(SaarthiSessionAssignment)
    .filter(
        SaarthiSessionAssignment.booking_id == booking_id
    )
    .first()
    )

    if assignment:
        assignment.status = "completed"
        assignment.completed_at = datetime.now(ZoneInfo("Asia/Kolkata"))
        assignment.base_amount = 350

        # DON'T reset travel amount
        assignment.travel_amount = assignment.travel_amount or 0

        # Keep extension amount
        assignment.extension_amount = assignment.extension_amount or 0

        assignment.deductions = assignment.deductions or 0

        assignment.net_amount = (
            float(assignment.base_amount)
            + float(assignment.travel_amount)
            + float(assignment.extension_amount)
            - float(assignment.deductions)
        )
        # config = get_rate_config(db)
        # recalculate_assignment(assignment, config)
    
    if session.start_time:
        duration_delta = end_time - session.start_time
        session.duration = int(duration_delta.total_seconds())
        
    booking.status = "completed"
    
    try:
        db.commit()
        db.refresh(session)
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to end session: {str(e)}"
        )
        
    return session


def create_review(db: Session, review_in: DarshanReviewCreate) -> DarshanReview:
    booking_id = review_in.booking_id
    
    booking = db.query(DarshanBooking).filter(DarshanBooking.id == booking_id).first()
    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Booking with ID {booking_id} not found"
        )
        
    if booking.status != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot submit review. Booking must be completed (session ended). Current status: {booking.status}"
        )
        
    # Check if a review already exists
    existing_review = db.query(DarshanReview).filter(DarshanReview.booking_id == booking_id).first()
    if existing_review:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A review has already been submitted for this booking."
        )
        
    new_review = DarshanReview(
        booking_id=booking_id,
        experience_rating=review_in.experience_rating,
        vr_quality_rating=review_in.vr_quality_rating,
        executive_rating=review_in.executive_rating,
        comment=review_in.comment
    )
    
    booking.status = "reviewed"
    
    db.add(new_review)
    try:
        db.commit()
        db.refresh(new_review)
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save review: {str(e)}"
        )
        
    return new_review





def extend_session(
    db: Session,
    extend_in: SessionExtensionCreateRequest
):
    booking = db.query(DarshanBooking).filter(
        DarshanBooking.id == extend_in.booking_id
    ).first()

    if not booking:
        raise HTTPException(
            status_code=404,
            detail="Booking not found"
        )

    extension_check = check_extension(
        db,
        extend_in.booking_id
    )

    if not extension_check["possible"]:
        raise HTTPException(
            status_code=400,
            detail=extension_check["message"]
        )

    # Create Extension Participant
    participant = DarshanParticipant(
        booking_id=booking.id,
        full_name=extend_in.full_name,
        age=extend_in.age,
        darshan_name=extend_in.darshan_name,
        is_extension=True
    )

    db.add(participant)

    # Store Extension History
    extension = SessionExtension(
        booking_id=booking.id,
        minutes=30,
        amount=499
    )

    db.add(extension)

    # Increase Session End Time
    booking.end_datetime += timedelta(
        minutes=30
    )

    # Update Saarthi Assignment
    assignment = db.query(SaarthiSessionAssignment).filter(
        SaarthiSessionAssignment.booking_id == booking.id
    ).first()

    if assignment:

        assignment.extension_minutes += 30

        assignment.extension_amount += 499

        assignment.net_amount = (
            float(assignment.base_amount)
            + float(assignment.travel_amount)
            + float(assignment.extension_amount)
            - float(assignment.deductions)
        )

    try:
        db.commit()

        db.refresh(participant)
        db.refresh(extension)

        if assignment:
            db.refresh(assignment)

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

    return {
        "success": True,
        "message": "Extension created successfully",
        "participant_id": participant.id,
        "booking_id": booking.id,
        "participant_name": participant.full_name,
        "extension_minutes": 30,
        "extension_amount": 350,
        "is_extension": participant.is_extension
    }
def check_extension(
    db: Session,
    booking_id: int
):
    booking = db.query(
        DarshanBooking
    ).filter(
        DarshanBooking.id == booking_id
    ).first()

    if not booking:
        raise HTTPException(
            404,
            "Booking not found"
        )

    extension_start = booking.end_datetime
    LAST_ALLOWED_END_TIME = time(22, 0)
    extension_end = (
        extension_start
        + timedelta(minutes=30)
    )
    if extension_end.hour  > 22:
        return {
            "possible": False,
            "message": "Extension unavailable. Last slot reached."
        }

    other_bookings = db.query(
        DarshanBooking
    ).filter(
        DarshanBooking.slot_date == booking.slot_date,
        DarshanBooking.id != booking.id,
        DarshanBooking.status != "rejected"
    ).all()

    for other in other_bookings:

        if (
            other.start_datetime is None
            or
            other.end_datetime is None
        ):
            continue

        overlap = (
            extension_start < other.end_datetime
            and
            extension_end > other.start_datetime
        )

        if overlap:
            return {
                "possible": False,
                "amount": 0,
                "message": "Extension not available"
            }

    return {
        "possible": True,
        "amount": 499,
        "message": "Extension available"
    }
def shorten_url(long_url: str) -> str:
    try:
        response = requests.get(
            "https://tinyurl.com/api-create.php",
            params={"url": long_url},
            timeout=5
        )
        if response.status_code == 200:
            return response.text
    except Exception:
        pass
    return long_url  