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
import html

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
    image_path: str | None = None,
):
    """
    Send the new-booking/admin approval email.

    Updated to match odt.py:
    - Supports Budhni, Halali and Heritage dynamically through config.
    - Shows original_price, discount_amount and final total_price.
    - Keeps backward compatibility for Ujjain/older bookings that may not
      have original_price or discount_amount columns populated.
    """

    booking = (
        db.query(config["booking_model"])
        .filter(config["booking_model"].id == booking_id)
        .first()
    )

    if not booking:
        raise ValueError(f"Booking #{booking_id} not found")

    travellers = (
        db.query(config["traveller_model"])
        .filter(config["traveller_model"].booking_id == booking_id)
        .all()
    )

    trek_name = config["name"]

    # ------------------------------------------------------------
    # PRICE DETAILS
    # odt.py now stores:
    # original_price -> price before coupon
    # discount_amount -> total coupon discount (max ₹100)
    # total_price -> final payable amount
    # ------------------------------------------------------------
    total_price = getattr(booking, "total_price", 0) or 0

    original_price = getattr(
        booking,
        "original_price",
        total_price,
    )
    original_price = original_price or total_price

    discount_amount = getattr(
        booking,
        "discount_amount",
        0,
    ) or 0

    # Do not show a negative/invalid discount if an old record is inconsistent.
    try:
        discount_amount = max(0, min(discount_amount, original_price))
    except TypeError:
        discount_amount = 0

    # ------------------------------------------------------------
    # TRAVELLER ROWS
    # ------------------------------------------------------------
    traveller_rows = ""

    for i, t in enumerate(travellers, 1):
        gender = str(getattr(t, "gender", "") or "").lower()

        gender_color = "#dbeafe" if gender == "male" else "#fce7f3"
        gender_text = "#1d4ed8" if gender == "male" else "#be185d"

        traveller_rows += f"""
        <tr>
          <td style="padding:10px 12px; color:#9ca3af; font-size:13px;">{i}</td>
          <td style="padding:10px 12px; color:#111827; font-size:13px; font-weight:500;">
              {html.escape(str(t.full_name))}
          </td>
          <td style="padding:10px 12px; color:#374151; font-size:13px;">
              {html.escape(str(t.age))}
          </td>
          <td style="padding:10px 12px;">
            <span style="display:inline-block; font-size:11px; font-weight:500;
                         padding:2px 8px; border-radius:20px;
                         background:{gender_color}; color:{gender_text};">
              {html.escape(str(t.gender))}
            </span>
          </td>
        </tr>
        """

    # ------------------------------------------------------------
    # ADMIN ACTION LINKS
    # ------------------------------------------------------------
    approve_link = (
        f"https://web-production-5736e.up.railway.app"
        f"{config['approve_route']}?booking_id={booking_id}"
    )

    decline_link = (
        f"https://web-production-5736e.up.railway.app"
        f"{config['decline_route']}?booking_id={booking_id}"
    )

    received_at = datetime.now().strftime("%d %b %Y · %I:%M %p")

    # ------------------------------------------------------------
    # PRICE HTML
    # ------------------------------------------------------------
    if discount_amount > 0:
        price_section = f"""
        <tr>
          <td width="50%">
            <div style="background:#f9fafb; border:1px solid #e5e7eb;
                        border-radius:8px; padding:14px 16px;">
              <div style="font-size:11px; color:#9ca3af;
                          text-transform:uppercase; letter-spacing:0.5px;
                          margin-bottom:4px;">
                Original Amount
              </div>
              <div style="font-size:15px; font-weight:600; color:#111827;">
                ₹ {original_price:,.0f}
              </div>
            </div>
          </td>

          <td width="50%">
            <div style="background:#f0fdf4; border:1px solid #bbf7d0;
                        border-radius:8px; padding:14px 16px;">
              <div style="font-size:11px; color:#15803d;
                          text-transform:uppercase; letter-spacing:0.5px;
                          margin-bottom:4px;">
                Coupon Discount
              </div>
              <div style="font-size:15px; font-weight:600; color:#15803d;">
                - ₹ {discount_amount:,.0f}
              </div>
            </div>
          </td>
        </tr>

        <tr>
          <td colspan="2" style="padding-top:12px;">
            <div style="background:#1a1a1a; border-radius:8px;
                        padding:14px 16px;">
              <div style="font-size:11px; color:#9ca3af;
                          text-transform:uppercase; letter-spacing:0.5px;
                          margin-bottom:4px;">
                Final Amount
              </div>
              <div style="font-size:18px; font-weight:600; color:#ffffff;">
                ₹ {total_price:,.0f}
              </div>
            </div>
          </td>
        </tr>
        """
    else:
        price_section = f"""
        <tr>
          <td colspan="2">
            <div style="background:#1a1a1a; border-radius:8px;
                        padding:14px 16px;">
              <div style="font-size:11px; color:#9ca3af;
                          text-transform:uppercase; letter-spacing:0.5px;
                          margin-bottom:4px;">
                Total Amount
              </div>
              <div style="font-size:18px; font-weight:600; color:#ffffff;">
                ₹ {total_price:,.0f}
              </div>
            </div>
          </td>
        </tr>
        """

    html_body = f"""
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{html.escape(trek_name)} Booking</title>
</head>

<body style="margin:0; padding:0; background:#f4f4f4;
             font-family:-apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;">

<div style="max-width:620px; margin:24px auto; background:#ffffff;
            border-radius:8px; overflow:hidden; border:1px solid #e0e0e0;">

  <!-- Header -->
  <div style="background:#1a1a1a; padding:28px 32px;">
    <div style="font-size:20px; font-weight:600; color:#ffffff;">
      Tirth<span style="color:#f97316;">Ghumo</span>
    </div>
    <div style="font-size:11px; color:#9ca3af; margin-top:4px;">
      Booking Verification Required
    </div>
  </div>

  <!-- Status -->
  <div style="background:#fff7ed; border-bottom:1px solid #fed7aa;
              padding:10px 32px;">
    <div style="font-size:12px; color:#c2410c; font-weight:500;
                letter-spacing:0.4px; text-transform:uppercase;">
      Pending Admin Approval
    </div>
  </div>

  <!-- Body -->
  <div style="padding:28px 32px;">

    <div style="font-size:14px; color:#374151; margin-bottom:20px;">
      <strong>Trip:</strong> {html.escape(trek_name)}
    </div>

    <!-- Booking reference -->
    <p style="font-size:11px; font-weight:600; color:#9ca3af;
              text-transform:uppercase; letter-spacing:0.8px; margin:0 0 12px;">
      Booking Reference
    </p>

    <div style="background:#f9fafb; border:1px solid #e5e7eb;
                border-radius:8px; padding:16px 20px; margin-bottom:24px;">
      <div style="font-size:12px; color:#6b7280; margin-bottom:4px;">
        Booking ID
      </div>
      <div style="font-size:24px; font-weight:700; color:#111827;">
        #TG-{booking_id}
      </div>
      <div style="font-size:11px; color:#9ca3af; margin-top:6px;">
        Received: {received_at}
      </div>
    </div>

    <!-- Booking details -->
    <p style="font-size:11px; font-weight:600; color:#9ca3af;
              text-transform:uppercase; letter-spacing:0.8px; margin:0 0 12px;">
      Booking Details
    </p>

    <table width="100%" cellpadding="0" cellspacing="0"
           style="border-collapse:separate; border-spacing:12px 0;
                  margin-bottom:24px;">

      <tr>
        <td width="50%">
          <div style="background:#f9fafb; border:1px solid #e5e7eb;
                      border-radius:8px; padding:14px 16px;">
            <div style="font-size:11px; color:#9ca3af;
                        text-transform:uppercase; letter-spacing:0.5px;
                        margin-bottom:4px;">
              Primary Email
            </div>
            <div style="font-size:13px; font-weight:600; color:#111827;
                        overflow-wrap:break-word;">
              {html.escape(str(booking.primary_email))}
            </div>
          </div>
        </td>

        <td width="50%">
          <div style="background:#f9fafb; border:1px solid #e5e7eb;
                      border-radius:8px; padding:14px 16px;">
            <div style="font-size:11px; color:#9ca3af;
                        text-transform:uppercase; letter-spacing:0.5px;
                        margin-bottom:4px;">
              Meal Preference
            </div>
            <div style="font-size:15px; font-weight:600; color:#111827;">
              {html.escape(str(booking.meal_preference))}
            </div>
          </div>
        </td>
      </tr>

      <tr><td colspan="2" style="padding-top:12px;"></td></tr>

      <tr>
        <td width="50%">
          <div style="background:#f9fafb; border:1px solid #e5e7eb;
                      border-radius:8px; padding:14px 16px;">
            <div style="font-size:11px; color:#9ca3af;
                        text-transform:uppercase; letter-spacing:0.5px;
                        margin-bottom:4px;">
              Total Travellers
            </div>
            <div style="font-size:15px; font-weight:600; color:#111827;">
              {booking.total_people} People
            </div>
          </div>
        </td>

        <td width="50%">
          <div style="background:#f9fafb; border:1px solid #e5e7eb;
                      border-radius:8px; padding:14px 16px;">
            <div style="font-size:11px; color:#9ca3af;
                        text-transform:uppercase; letter-spacing:0.5px;
                        margin-bottom:4px;">
              Trek Date
            </div>
            <div style="font-size:15px; font-weight:600; color:#111827;">
              {html.escape(str(booking.trek_date))}
            </div>
          </div>
        </td>
      </tr>

      <tr><td colspan="2" style="padding-top:12px;"></td></tr>

      {price_section}

    </table>

    <!-- Travellers -->
    <p style="font-size:11px; font-weight:600; color:#9ca3af;
              text-transform:uppercase; letter-spacing:0.8px; margin:0 0 12px;">
      Travellers
    </p>

    <table width="100%" cellpadding="0" cellspacing="0"
           style="border-collapse:collapse; margin-bottom:24px;">
      <thead>
        <tr style="background:#f3f4f6;">
          <th style="font-size:11px; color:#6b7280; text-align:left;
                     padding:10px 12px;">#</th>
          <th style="font-size:11px; color:#6b7280; text-align:left;
                     padding:10px 12px;">Full Name</th>
          <th style="font-size:11px; color:#6b7280; text-align:left;
                     padding:10px 12px;">Age</th>
          <th style="font-size:11px; color:#6b7280; text-align:left;
                     padding:10px 12px;">Gender</th>
        </tr>
      </thead>
      <tbody>
        {traveller_rows}
      </tbody>
    </table>

    <hr style="border:none; border-top:1px solid #e5e7eb; margin:0 0 24px;">

    <!-- Actions -->
    <div style="background:#f9fafb; border:1px solid #e5e7eb;
                border-radius:8px; padding:20px 24px;">

      <p style="font-size:13px; color:#374151; margin:0 0 16px; line-height:1.6;">
        Review the payment screenshot attached and take action on this booking.
        This action is <strong>irreversible</strong> — the customer will be
        notified immediately.
      </p>

      <table width="100%" cellpadding="0" cellspacing="0">
        <tr>
          <td width="48%">
            <a href="{approve_link}"
               style="display:block; padding:12px 24px; background:#16a34a;
                      color:#ffffff; font-size:14px; font-weight:600;
                      text-decoration:none; border-radius:6px; text-align:center;">
              ✓ Approve Booking
            </a>
          </td>

          <td width="4%"></td>

          <td width="48%">
            <a href="{decline_link}"
               style="display:block; padding:12px 24px; background:#ffffff;
                      color:#dc2626; font-size:14px; font-weight:600;
                      text-decoration:none; border-radius:6px; text-align:center;
                      border:1.5px solid #dc2626;">
              ✕ Decline
            </a>
          </td>
        </tr>
      </table>
    </div>

  </div>

  <!-- Footer -->
  <div style="background:#f9fafb; border-top:1px solid #e5e7eb;
              padding:16px 32px;">
    <div style="font-size:12px; color:#6b7280;">
      <strong style="color:#374151;">TirthGhumo</strong> · Admin Notification
    </div>
    <div style="font-size:11px; color:#9ca3af;">
      Do not reply to this email
    </div>
  </div>

</div>
</body>
</html>
"""

    # ------------------------------------------------------------
    # PAYMENT SCREENSHOT ATTACHMENT
    # ------------------------------------------------------------
    attachments = []

    if image_path and os.path.exists(image_path):
        with open(image_path, "rb") as f:
            file_data = base64.b64encode(f.read()).decode("utf-8")

        file_name = os.path.basename(image_path)
        mime = (
            "image/jpeg"
            if image_path.lower().endswith((".jpg", ".jpeg"))
            else "image/png"
        )

        attachments.append(
            {
                "content": file_data,
                "filename": file_name,
                "type": mime,
            }
        )

    email_payload = {
        "from": "Tirth Ghumo <no-reply@tirthghumo.in>",
        "to": "booking.tirthghumo@gmail.com",
        "subject": f"[{trek_name}] Booking #{booking_id} - Approval Required",
        "html": html_body,
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

Team TirthGhumo

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









async def send_email_with_invoice(email, data, invoice_path):
    """Send the approved booking invoice to the customer."""

    # odt.py uses these booking models for the different trip configs.
    model_trip_names = {
        "ODT1": "Budhni Trek",
        "ChotaPachmarhi": "Halali Trek",
        "HeritageTrip": "Heritage Trip",
        "UjjainOmkareshwarTrip": "Ujjain Omkareshwar Trip",
    }

    trip_name = model_trip_names.get(
        data.__class__.__name__,
        "TirthGhumo Trip",
    )

    # odt.py stores the discounted booking amount.
    original_price = getattr(data, "original_price", None)
    discount_amount = getattr(data, "discount_amount", 0) or 0
    total_price = getattr(data, "total_price", None)

    if original_price is not None and total_price is not None:
        amount_summary = (
            f"Original amount: ₹{original_price:,.0f}\n"
            f"Coupon discount: ₹{discount_amount:,.0f}\n"
            f"Final amount: ₹{total_price:,.0f}"
        )
    elif total_price is not None:
        amount_summary = f"Final amount: ₹{total_price:,.0f}"
    else:
        amount_summary = ""

    # ---- Attach PDF ----
    with open(invoice_path, "rb") as f:
        file_bytes = base64.b64encode(f.read()).decode("utf-8")

    # ---- Email Body ----
    email_body = f"""
Hey🌿

Great news — your booking for {trip_name} with TirthGhumo
is confirmed for {data.trek_date}!

Your payment has been approved successfully.

{amount_summary}

All essential trip details, including timings and instructions,
will be shared shortly on WhatsApp.

Please make sure you’ve requested to join the WhatsApp group,
as all updates will be shared there.

If you need any help or have questions, feel free to contact us
at 6260499299 / 6204289831.

Get ready for an exciting adventure and a day full of unforgettable memories!

Warm regards,
Team TirthGhumo

Thank you for choosing TirthGhumo — Aastha Bhi, Suvidha Bhi 🌄
"""

    email_payload = {
        "from": "Tirth Ghumo <no-reply@tirthghumo.in>",
        "to": [email],
        "subject": f"Your {trip_name} Booking Invoice",
        "text": email_body.strip(),
        "attachments": [
            {
                "filename": "invoice.pdf",
                "content": file_bytes,
                "type": "application/pdf",
            }
        ],
    }

    try:
        resend.Emails.send(email_payload)
    except Exception as e:
        raise Exception(f"Invoice email failed: {str(e)}")



def send_heritage_trek_coupon_email(

    email: str,

    coupon_code: str,

    expires_at: datetime,

):

    expiry_text = expires_at.strftime("%d %B %Y")



    html_body = f"""

    <div style="font-family:Arial,sans-serif;max-width:600px;

                margin:auto;padding:24px;color:#222;">



        <h2>Thank you for choosing TirthGhumo!</h2>



        <p>

            Thank you for registering for our

            <strong>One Day Heritage</strong> experience.

        </p>



        <p>Here's a little gift for your next adventure!</p>



        <div style="background:#fff7ed;padding:24px;

                    text-align:center;border:2px dashed #f97316;

                    border-radius:12px;">



            <p style="font-size:14px;">YOUR EXCLUSIVE COUPON</p>



            <h2 style="color:#ea580c;letter-spacing:2px;">

                {coupon_code}

            </h2>



            <h3>₹100 OFF on One Day Trek</h3>



            <p>Valid until {expiry_text}</p>

        </div>



        <p>

            Enter this coupon code while booking your next

            One Day Trek on TirthGhumo.

        </p>



        <p>Happy Travelling!<br><strong>Team TirthGhumo</strong></p>

    </div>

    """



    response = resend.Emails.send({

        "from": "TirthGhumo <no-reply@tirthghumo.in>",

        "to": [email],

        "subject": "Your ₹100 TirthGhumo Trek Coupon 🎉",

        "html": html_body,

    })



    return response


