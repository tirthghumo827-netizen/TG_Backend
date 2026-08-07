from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
from fastapi import Depends 
from app.config import settings 
from sqlalchemy.orm import Session
from sqlalchemy.orm import Session
from app.database import engine , get_db
from app import models 
import requests
import resend 
import base64
import os
from datetime import datetime
conf = ConnectionConfig(
    MAIL_USERNAME= settings.mail_username,
    MAIL_PASSWORD=settings.mail_password,
    MAIL_FROM=settings.mail_from,
    MAIL_PORT=settings.mail_port,
    MAIL_SERVER=settings.mail_server,
    MAIL_STARTTLS=settings.mail_starttls,
    MAIL_SSL_TLS=settings.mail_ssl_tls,
    USE_CREDENTIALS=settings.use_credentials,
)

resend.api_key = settings.resend_api_key
base_url = settings.base_url



def send_booking_email(
    booking_id: int,
    db: Session,
    config: dict,
    image_path: str | None = None
):
    booking = db.query(config["booking_model"]).filter(
    config["booking_model"].id == booking_id
    ).first()

    travellers = db.query(config["traveller_model"]).filter(
        config["traveller_model"].booking_id == booking_id
    ).all()

    trek_name = config["name"]

    # --- Traveller rows ---
    traveller_rows = ""
    for i, t in enumerate(travellers, 1):
        gender_color = "#dbeafe" if t.gender.lower() == "male" else "#fce7f3"
        gender_text  = "#1d4ed8" if t.gender.lower() == "male" else "#be185d"
        traveller_rows += f"""
        <tr>
          <td style="padding:10px 12px; color:#9ca3af; font-size:13px;">{i}</td>
          <td style="padding:10px 12px; color:#111827; font-size:13px; font-weight:500;">{t.full_name}</td>
          <td style="padding:10px 12px; color:#374151; font-size:13px;">{t.age}</td>
          <td style="padding:10px 12px;">
            <span style="display:inline-block; font-size:11px; font-weight:500; padding:2px 8px;
                   border-radius:20px; background:{gender_color}; color:{gender_text};">
              {t.gender}
            </span>
          </td>
        </tr>
        """ 

    # --- Links --- 
    approve_link = (
    f"https://web-production-edeea.up.railway.app{config['approve_route']}?booking_id={booking_id}"
    )

    decline_link = (
        f"https://web-production-edeea.up.railway.app{config['decline_route']}?booking_id={booking_id}"
    )

    received_at = datetime.now().strftime("%d %b %Y · %I:%M %p")

    html_body = f"""
<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>New Trek Booking</title></head>
<body style="margin:0; padding:0; background:#f4f4f4;
             font-family:-apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;">

  <div style="max-width:620px; margin:24px auto; background:#ffffff;
              border-radius:8px; overflow:hidden; border:1px solid #e0e0e0;">

    <!-- Header -->
    <div style="background:#1a1a1a; padding:28px 32px;">
      <div style="font-size:20px; font-weight:600; color:#ffffff; letter-spacing:-0.3px;">
        Tirth<span style="color:#f97316;">Ghumo</span>
      </div>
      <div style="font-size:11px; color:#9ca3af; margin-top:4px;">Booking Verification Required</div>
    </div>

    <!-- Status bar -->
    <div style="background:#fff7ed; border-bottom:1px solid #fed7aa;
                padding:10px 32px; display:flex; align-items:center; gap:8px;">
      <div style="width:8px; height:8px; background:#f97316; border-radius:50%;"></div>
      <div style="font-size:12px; color:#c2410c; font-weight:500;
                  letter-spacing:0.4px; text-transform:uppercase;">
        Pending Admin Approval
      </div>
    </div>

    <!-- Body -->
    <div style="padding:28px 32px;">
      <div>
          <strong>Trek:</strong> { trek_name }
      </div>
      <!-- Booking reference -->
      <p style="font-size:11px; font-weight:600; color:#9ca3af; text-transform:uppercase;
                letter-spacing:0.8px; margin:0 0 12px;">Booking Reference</p>
      <div style="background:#f9fafb; border:1px solid #e5e7eb; border-radius:8px;
                  padding:16px 20px; margin-bottom:24px;">
        <div style="font-size:12px; color:#6b7280; margin-bottom:4px;">Booking ID</div>
        <div style="font-size:24px; font-weight:700; color:#111827; letter-spacing:-0.5px;">
          #TG-{booking_id}
        </div>
        <div style="font-size:11px; color:#9ca3af; margin-top:6px;">
          Received: {received_at}
        </div>
      </div>

      <!-- Booking details grid -->
      <p style="font-size:11px; font-weight:600; color:#9ca3af; text-transform:uppercase;
                letter-spacing:0.8px; margin:0 0 12px;">Booking Details</p>
      <table width="100%" cellpadding="0" cellspacing="0"
             style="border-collapse:separate; border-spacing:12px 0; margin-bottom:24px;">
        <tr>
          <td width="50%">
            <div style="background:#f9fafb; border:1px solid #e5e7eb; border-radius:8px; padding:14px 16px;">
              <div style="font-size:11px; color:#9ca3af; text-transform:uppercase;
                          letter-spacing:0.5px; margin-bottom:4px;">Primary Email</div>
              <div style="font-size:13px; font-weight:600; color:#111827;
                          overflow-wrap:break-word;">{booking.primary_email}</div>
            </div>
          </td>
          <td width="50%">
            <div style="background:#f9fafb; border:1px solid #e5e7eb; border-radius:8px; padding:14px 16px;">
              <div style="font-size:11px; color:#9ca3af; text-transform:uppercase;
                          letter-spacing:0.5px; margin-bottom:4px;">Meal Preference</div>
              <div style="font-size:15px; font-weight:600; color:#111827;">{booking.meal_preference}</div>
            </div>
          </td>
        </tr>
        <tr><td colspan="2" style="padding-top:12px;"></td></tr>
        <tr>
          <td width="50%">
            <div style="background:#f9fafb; border:1px solid #e5e7eb; border-radius:8px; padding:14px 16px;">
              <div style="font-size:11px; color:#9ca3af; text-transform:uppercase;
                          letter-spacing:0.5px; margin-bottom:4px;">Total Travellers</div>
              <div style="font-size:15px; font-weight:600; color:#111827;">{booking.total_people} People</div>
            </div>
          </td>
          <td width="50%">
            <div style="background:#f9fafb; border:1px solid #e5e7eb; border-radius:8px; padding:14px 16px;">
              <div style="font-size:11px; color:#9ca3af; text-transform:uppercase;
                          letter-spacing:0.5px; margin-bottom:4px;">Trek Date</div>
              <div style="font-size:15px; font-weight:600; color:#111827;">{booking.trek_date}</div>
            </div>
          </td>
        </tr>
        <tr><td colspan="2" style="padding-top:12px;"></td></tr>
        <tr>
          <td colspan="2">
            <div style="background:#1a1a1a; border-radius:8px; padding:14px 16px;">
              <div style="font-size:11px; color:#9ca3af; text-transform:uppercase;
                          letter-spacing:0.5px; margin-bottom:4px;">Total Amount</div>
              <div style="font-size:18px; font-weight:600; color:#ffffff;">₹ {booking.total_price:,}</div>
            </div>
          </td>
        </tr>
      </table>

      <!-- Travellers table -->
      <p style="font-size:11px; font-weight:600; color:#9ca3af; text-transform:uppercase;
                letter-spacing:0.8px; margin:0 0 12px;">Travellers</p>
      <table width="100%" cellpadding="0" cellspacing="0"
             style="border-collapse:collapse; margin-bottom:24px;">
        <thead>
          <tr style="background:#f3f4f6;">
            <th style="font-size:11px; color:#6b7280; text-transform:uppercase; letter-spacing:0.5px;
                       text-align:left; padding:10px 12px; font-weight:600;">#</th>
            <th style="font-size:11px; color:#6b7280; text-transform:uppercase; letter-spacing:0.5px;
                       text-align:left; padding:10px 12px; font-weight:600;">Full Name</th>
            <th style="font-size:11px; color:#6b7280; text-transform:uppercase; letter-spacing:0.5px;
                       text-align:left; padding:10px 12px; font-weight:600;">Age</th>
            <th style="font-size:11px; color:#6b7280; text-transform:uppercase; letter-spacing:0.5px;
                       text-align:left; padding:10px 12px; font-weight:600;">Gender</th>
          </tr>
        </thead>
        <tbody>
          {traveller_rows}
        </tbody>
      </table>

      <hr style="border:none; border-top:1px solid #e5e7eb; margin:0 0 24px;">

      <!-- Action buttons -->
      <div style="background:#f9fafb; border:1px solid #e5e7eb; border-radius:8px; padding:20px 24px;">
        <p style="font-size:13px; color:#374151; margin:0 0 16px; line-height:1.6;">
          Review the payment screenshot attached and take action on this booking.
          This action is <strong>irreversible</strong> — the customer will be notified immediately.
        </p>
        <table width="100%" cellpadding="0" cellspacing="0">
          <tr>
            <td width="48%">
              <a href="{approve_link}"
                 style="display:block; padding:12px 24px; background:#16a34a; color:#ffffff;
                        font-size:14px; font-weight:600; text-decoration:none;
                        border-radius:6px; text-align:center;">
                ✓ Approve Booking
              </a>
            </td>
            <td width="4%"></td>
            <td width="48%">
              <a href="{decline_link}"
                 style="display:block; padding:12px 24px; background:#ffffff; color:#dc2626;
                        font-size:14px; font-weight:600; text-decoration:none;
                        border-radius:6px; text-align:center;
                        border:1.5px solid #dc2626;">
                ✕ Decline
              </a>
            </td>
          </tr>
        </table>
      </div>

    </div><!-- /body -->

    <!-- Footer -->
    <div style="background:#f9fafb; border-top:1px solid #e5e7eb;
                padding:16px 32px; display:flex; justify-content:space-between; align-items:center;">
      <div style="font-size:12px; color:#6b7280;">
        <strong style="color:#374151;">TirthGhumo</strong> · Admin Notification
      </div>
      <div style="font-size:11px; color:#9ca3af;">Do not reply to this email</div>
    </div>

  </div>
</body>
</html>
"""

    # --- Attachments ---
    attachments = []
    if image_path and os.path.exists(image_path):
        with open(image_path, "rb") as f:
            file_data = base64.b64encode(f.read()).decode("utf-8")
            file_name = os.path.basename(image_path)
            mime = "image/jpeg" if image_path.lower().endswith((".jpg", ".jpeg")) else "image/png"
            attachments.append({
                "content": file_data,
                "filename": file_name,
                "type": mime
            })

    email_payload = {
        "from": "Tirth Ghumo <no-reply@tirthghumo.in>",
        "to": "booking.tirthghumo@gmail.com",
        "subject":f"[{trek_name}] Booking #{booking_id} - Approval Required",
        "html": html_body
    }
    if attachments:
        email_payload["attachments"] = attachments

    response = resend.Emails.send(email_payload)
    print("EMAIL SENT SUCCESSFULLY:", response)
async def send_booking_declined_email(data , email):
    try:
        text_body = f"""
        Hello,

Thank you for choosing TirthGhumo for your adventure.
We wanted to let you know that we've reviewed your recent booking attempt.
Unfortunately, we couldn’t verify the payment details on our end.

This might be due to a mismatch in the transaction ID or some other discrepancy.

If you believe this is an error, please feel free to reach out to us at
6260499299 / 6204289831 — we’ll be happy to help resolve the issue.

We appreciate your understanding and hope to welcome you on another adventure soon.

Warm regards,
Team TirthGhumo
        """.strip()

        email_payload = {
            "from": "Tirth Ghumo <no-reply@tirthghumo.in>",
            "to": [email],
            "subject": "Booking Update – Action Required",
            "text": text_body,
        }

        resend.Emails.send(email_payload)

    except Exception as e:
        print("DECLINE EMAIL ERROR:", e)
        raise




async def send_email_with_invoice(email ,data, invoice_path):
    """Send invoice PDF to user using Resend"""

    # ---- Attach PDF ----
    with open(invoice_path, "rb") as f:
        file_bytes = base64.b64encode(f.read()).decode("utf-8")

    # ---- Email Body ----
    email_body = f"""
   Hey🌿

Great news — your booking for the 1Day Adventure Trek with TirthGhumo 
is confirmed for {data.trek_date}!

Your payment has been approved successfully . 

All essential trip details, including timings and instructions, 
will be shared shortly on WhatsApp.

Please make sure you’ve requested to join the WhatsApp group,
as all updates will be shared there.

If you need any help or have questions, feel free to contact us 
at 6260499299 / 6204289831.

Get ready for an exciting adventure and a day full of unforgettable memories!

Warm regards,
Team TirthGhumo

Thank you for choosing TirthGhumo — Aastha Bhi, Suvidha Bhi 🌄

    """

    # ---- Email Payload ----
    email_payload = {
        "from": "Tirth Ghumo <no-reply@tirthghumo.in>",
        "to": [email],
        "subject": "Your Trek Booking Invoice",
        "text": email_body.strip(),
        "attachments": [
            {
                "filename": "invoice.pdf",
                "content": file_bytes,
                "type": "application/pdf"
            }
        ]
    }

    # ---- Send ----
    try:
        resend.Emails.send(email_payload)
    except Exception as e:
        raise Exception(f"Invoice email failed: {str(e)}")




