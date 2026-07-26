from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, BackgroundTasks
from sqlalchemy.orm import Session
from datetime import date
from fastapi.responses import HTMLResponse, RedirectResponse
from urllib.parse import quote
from app.database import get_db
from ..schema import (
    DarshanBookingCreate,
    CompleteBookingDetails,
    DarshanBookingResponse,
    DarshanSessionResponse,
    DarshanReviewCreate,
    DarshanReviewResponse,
    QRVerifyRequest,
    SessionStartRequest,
    SessionEndRequest,
    SessionExtensionCheckRequest,
    SessionExtensionCheckResponse,
    SessionExtensionCreateRequest,
    SessionExtensionResponse,

)
from ..models import Executive
from ..services import service

router = APIRouter(
    prefix="/divya-drishti",
    tags=["Divya Drishti"]
)

# ---------------------------------------------------------------------------
# Shared brand chrome for all HTML admin pages (matches the Resend email theme)
# ---------------------------------------------------------------------------
def _page_shell(title: str, eyebrow: str, badge: str, badge_bg: str, badge_color: str, body_html: str) -> str:
    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
        <title>{title} · TirthGhumo</title>
    </head>
    <body style="margin:0;padding:0;background:#F5F3FF;font-family:'Segoe UI',Arial,sans-serif;">
        <table width="100%" cellpadding="0" cellspacing="0" style="background:#F5F3FF;padding:40px 16px;">
            <tr>
                <td align="center">
                    <table width="560" cellpadding="0" cellspacing="0" style="max-width:560px;width:100%;">

                        <!-- Header -->
                        <tr>
                            <td style="background:linear-gradient(135deg,#4C1D95 0%,#7C3AED 100%);border-radius:14px 14px 0 0;padding:32px 36px;">
                                <table width="100%" cellpadding="0" cellspacing="0">
                                    <tr>
                                        <td>
                                            <p style="margin:0 0 4px 0;font-size:11px;font-weight:700;letter-spacing:2px;color:#C4B5FD;text-transform:uppercase;">
                                                Tirth Ghumo · VR Darshan
                                            </p>
                                            <h1 style="margin:0;font-size:22px;font-weight:700;color:#FFFFFF;line-height:1.3;">
                                                {eyebrow}
                                            </h1>
                                        </td>
                                        <td align="right" valign="top">
                                            <span style="display:inline-block;background:{badge_bg};color:{badge_color};font-size:11px;font-weight:700;letter-spacing:1px;text-transform:uppercase;padding:5px 12px;border-radius:20px;white-space:nowrap;">
                                                {badge}
                                            </span>
                                        </td>
                                    </tr>
                                </table>
                            </td>
                        </tr>

                        <!-- Body -->
                        <tr>
                            <td style="background:#FFFFFF;padding:32px 36px;border-left:1px solid #EDE9FE;border-right:1px solid #EDE9FE;">
                                {body_html}
                            </td>
                        </tr>

                        <!-- Footer -->
                        <tr>
                            <td style="background:#F5F3FF;border:1px solid #EDE9FE;border-top:none;border-radius:0 0 14px 14px;padding:20px 36px;text-align:center;">
                                <p style="margin:0;font-size:11px;color:#9CA3AF;">TirthGhumo · Divya Drishti VR Darshan System</p>
                                <p style="margin:4px 0 0 0;font-size:11px;color:#9CA3AF;">Support: 6260499299 · enquiry.tirthghumo@gmail.com</p>
                            </td>
                        </tr>

                    </table>
                </td>
            </tr>
        </table>
    </body>
    </html>
    """


def _info_row(label: str, value, zebra: bool = False) -> str:
    bg = "#F5F3FF" if zebra else "#FFFFFF"
    return f"""
    <tr style="background:{bg};">
        <td style="padding:10px 16px;font-size:12px;font-weight:600;color:#6B7280;width:40%;border-bottom:1px solid #EDE9FE;">{label}</td>
        <td style="padding:10px 16px;font-size:13px;font-weight:600;color:#1F2937;border-bottom:1px solid #EDE9FE;">{value}</td>
    </tr>
    """


@router.get("/booking/{booking_id}")
def get_booking_details(
    booking_id: int,
    db: Session = Depends(get_db)
):
    return service.get_booking_details(
        db,
        booking_id
    )


@router.post(
    "/book",
    response_model=DarshanBookingResponse,
    status_code=status.HTTP_201_CREATED
)
async def book_session(
    background_tasks: BackgroundTasks,
    full_name: str = Form(...),
    contact_number: str = Form(...),
    whatsapp_number: str = Form(...),
    address: str = Form(...),
    persons: int = Form(...),
    slot_time: str = Form(...),
    slot_date: date = Form(...),
    payment_status: str = Form(...),
    payment_screenshot: UploadFile = File(...),
    db: Session = Depends(get_db)
):

    booking_in = DarshanBookingCreate(
        full_name=full_name,
        contact_number=contact_number,
        whatsapp_number=whatsapp_number,
        address=address,
        persons=persons,
        slot_time=slot_time,
        slot_date=slot_date,
        payment_status=payment_status
    )

    return service.book_session(
        db,
        booking_in,
        payment_screenshot,
        background_tasks
    )


@router.post("/executive/login")
def executive_login(
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    executive = db.query(Executive).filter(
        Executive.username == username,
        Executive.password == password
    ).first()

    if not executive:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    return {
        "success": True,
        "executive_id": executive.id,
        "full_name": executive.full_name
    }


@router.put("/update/{booking_id}", response_model=DarshanBookingResponse)
async def update_booking(
    booking_id: int,
    booking_in: CompleteBookingDetails,
    db: Session = Depends(get_db),
):
    return service.complete_booking_details(
        db,
        booking_id,
        booking_in
    )


# ---------------------------------------------------------------------------
# FIX #1: this used to call an undefined `get_booking(...)` (NameError on
# every click). It now correctly goes through the service layer.
# ---------------------------------------------------------------------------
@router.get("/qr/{booking_id}")
def get_qr(booking_id: int, db: Session = Depends(get_db)):
    booking = service.get_booking(db, booking_id)
    return RedirectResponse(url=booking.qr_code)


@router.get("/approve-booking/{booking_id}")
def approve_booking_email(
    booking_id: int,
    db: Session = Depends(get_db)
):
    booking = service.get_booking(db, booking_id)
    executives = db.query(Executive).all()

    if executives:
        exec_buttons = ""
        for executive in executives:
            exec_buttons += f"""
            <form method="POST" action="/divya-drishti/approve-booking/{booking.id}" style="margin-bottom:14px;border:2px solid #DDD6FE;border-radius:8px;padding:14px 16px;">
                <input type="hidden" name="executive_id" value="{executive.id}" />

                <p style="margin:0 0 10px 0;font-size:14px;font-weight:700;color:#4C1D95;">
                    👤 &nbsp;{executive.full_name}
                </p>

                <label style="display:block;font-size:11px;font-weight:600;color:#6B7280;margin-bottom:4px;">
                    Distance (km)
                </label>
                <input type="number" name="distance_km" step="0.1" min="0.1" required
                       placeholder="e.g. 12.5"
                       style="width:100%;box-sizing:border-box;padding:10px 12px;font-size:13px;
                              border:1px solid #DDD6FE;border-radius:6px;margin-bottom:10px;
                              color:#1F2937;" />

                <button type="submit" style="display:block;width:100%;background:#7C3AED;color:#FFFFFF;
                    border:none;text-decoration:none;font-size:13px;font-weight:700;
                    text-align:center;padding:12px 20px;border-radius:6px;cursor:pointer;">
                    Assign to {executive.full_name}
                </button>
            </form>
            """
    else:
        exec_buttons = """
        <p style="margin:0;font-size:13px;color:#9CA3AF;font-style:italic;">
            No Saarthi executives are currently available to assign.
        </p>
        """

    body = f"""
    <p style="margin:0 0 12px 0;font-size:10px;font-weight:700;letter-spacing:2px;color:#7C3AED;text-transform:uppercase;">
        Booking Summary
    </p>
    <table width="100%" cellpadding="0" cellspacing="0" style="border:1px solid #EDE9FE;border-radius:8px;overflow:hidden;margin-bottom:28px;">
        {_info_row("Booking ID", f"#{booking.id}")}
        {_info_row("Customer", booking.full_name, zebra=True)}
        {_info_row("Customer Address", booking.address)}
        {_info_row("Date", booking.slot_date, zebra=True)}
        {_info_row("Time Slot", booking.slot_time)}
        {_info_row("Persons", booking.persons, zebra=True)}
    </table>

    <p style="margin:0 0 14px 0;font-size:10px;font-weight:700;letter-spacing:2px;color:#7C3AED;text-transform:uppercase;">
        Assign a Saarthi Executive
    </p>
    {exec_buttons}

    <hr style="border:none;border-top:1px solid #EDE9FE;margin:24px 0;" />

    <a href="/divya-drishti/reject-booking/{booking.id}"
       style="display:block;text-align:center;background:#FFFFFF;color:#DC2626;text-decoration:none;
              font-size:13px;font-weight:700;padding:12px 20px;border-radius:8px;border:2px solid #FCA5A5;">
        ❌ &nbsp; Reject This Booking
    </a>
    """

    return HTMLResponse(_page_shell(
        title="Approve Booking",
        eyebrow="Assign a Saarthi",
        badge="Pending",
        badge_bg="#FEF3C7",
        badge_color="#92400E",
        body_html=body
    ))

@router.post("/approve-booking/{booking_id}")
def approve_booking_submit(
    background_tasks: BackgroundTasks,
    booking_id: int,
    executive_id: int = Form(...),
    distance_km: float = Form(..., gt=0),
    db: Session = Depends(get_db),
):

    booking = service.approve_booking(
        db,
        booking_id,
        executive_id,
        background_tasks,
        distance_km=distance_km,
    )
    

@router.get("/reject-booking/{booking_id}")
def reject_booking_email(
    booking_id: int,
    db: Session = Depends(get_db)
):
    booking = service.reject_booking(db, booking_id)

    decline_message = f"""🙏 *Divya Drishti VR Darshan Booking Update*

Namaste {booking.full_name},

Thank you for choosing Divya Drishti VR Darshan.

After reviewing your booking request, we regret to inform you that we are currently unable to approve your booking.

❌ *Booking Status: Declined*

📋 *Booking Details*
• Booking ID: #{booking.id}
• Date: {booking.slot_date}
• Time Slot: {booking.slot_time}
• Persons: {booking.persons}

This may happen due to:
• Slot availability issues
• Payment verification issues
• Incomplete booking information
• Operational limitations for the selected schedule

If you believe this was a mistake or would like to book another slot, please contact our support team.

📞 Support: 6260499299
📧 enquiry.tirthghumo@gmail.com

We sincerely apologize for any inconvenience caused and hope to serve you in the future. 🌸🙏

Warm Regards,
*Team TirthGhumo*
Divya Drishti VR Darshan"""

    whatsapp_url = (
        f"https://wa.me/91{booking.whatsapp_number}"
        f"?text={quote(decline_message)}"
    )

    body = f"""
    <p style="margin:0 0 20px 0;font-size:14px;color:#374151;line-height:1.6;">
        Booking <strong>#{booking.id}</strong> has been marked as declined. You may notify the
        customer directly over WhatsApp using the button below.
    </p>

    <table width="100%" cellpadding="0" cellspacing="0" style="border:1px solid #EDE9FE;border-radius:8px;overflow:hidden;margin-bottom:28px;">
        {_info_row("Customer", booking.full_name)}
        {_info_row("Date", booking.slot_date, zebra=True)}
        {_info_row("Time Slot", booking.slot_time)}
    </table>

    <table width="100%" cellpadding="0" cellspacing="0">
        <tr>
            <td>
                <a href="{whatsapp_url}" target="_blank"
                   style="display:block;background:#25D366;color:#FFFFFF;text-decoration:none;
                          font-size:14px;font-weight:700;text-align:center;padding:14px 24px;
                          border-radius:8px;letter-spacing:0.5px;">
                    💬 &nbsp; Send WhatsApp Message
                </a>
            </td>
        </tr>
    </table>
    """

    return HTMLResponse(_page_shell(
        title="Booking Rejected",
        eyebrow="Booking Rejected",
        badge="Declined",
        badge_bg="#FEE2E2",
        badge_color="#991B1B",
        body_html=body
    ))


@router.patch("/reject/{booking_id}", response_model=DarshanBookingResponse)
async def reject_booking(booking_id: int, db: Session = Depends(get_db)):
    return service.reject_booking(db, booking_id)


@router.post("/verify-qr", response_model=DarshanBookingResponse)
def verify_qr(verify_in: QRVerifyRequest, db: Session = Depends(get_db)):
    return service.verify_qr(db, verify_in.qr_data)


@router.post("/session/start", response_model=DarshanSessionResponse)
def start_session(start_in: SessionStartRequest, db: Session = Depends(get_db)):
    return service.start_session(db, start_in.booking_id)


@router.post("/session/end", response_model=DarshanSessionResponse)
def end_session(end_in: SessionEndRequest, db: Session = Depends(get_db)):
    return service.end_session(db, end_in.booking_id)


@router.post("/review", response_model=DarshanReviewResponse)
def create_review(review_in: DarshanReviewCreate, db: Session = Depends(get_db)):
    return service.create_review(db, review_in)


@router.post("/check-extension")
def check_extension(
    check_in: SessionExtensionCheckRequest,
    db: Session = Depends(get_db)
):
    return service.check_extension(
        db,
        check_in.booking_id
    )


@router.post("/session/extend")
def extend_session(
    extend_in: SessionExtensionCreateRequest,
    db: Session = Depends(get_db)
):
    return service.extend_session(
        db,
        extend_in
    )


@router.get("/slots")
def get_available_slots(
    selected_date: date,
    db: Session = Depends(get_db)
):
    return service.get_available_slots(
        db,
        selected_date
    )