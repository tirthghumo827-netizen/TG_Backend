# utils/mail/admin_vr_darshan_mail.py
import resend
from app.config import settings

resend.api_key = settings.resend_api_key

def send_admin_vr_darshan_email(booking):

    approve_url = f"https://web-production-60ea6.up.railway.app/divya-drishti/approve-booking/{booking.id}"

    decline_url = f"https://web-production-60ea6.up.railway.app/divya-drishti/reject-booking/{booking.id}"
    # decline_other_url = f"https://web-production-60ea6.up.railway.app/admin/vr-darshan/action?booking_id={booking.id}&action=decline_other"

    payment_screenshot_html = (
        f'<a href="{booking.payment_screenshot}" target="_blank" style="color:#7C3AED;font-weight:600;text-decoration:none;">View Screenshot ↗</a>'
        if booking.payment_screenshot
        else '<span style="color:#9CA3AF;font-style:italic;">Not uploaded</span>'
    )

    html_body = f"""
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>VR Darshan Booking – Action Required</title>
</head>
<body style="margin:0;padding:0;background:#F5F3FF;font-family:'Segoe UI',Arial,sans-serif;">

  <table width="100%" cellpadding="0" cellspacing="0" style="background:#F5F3FF;padding:32px 0;">
    <tr>
      <td align="center">
        <table width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%;">

          <!-- Header -->
          <tr>
            <td style="background:linear-gradient(135deg,#4C1D95 0%,#7C3AED 100%);border-radius:12px 12px 0 0;padding:32px 36px;">
              <table width="100%" cellpadding="0" cellspacing="0">
                <tr>
                  <td>
                    <p style="margin:0 0 4px 0;font-size:11px;font-weight:700;letter-spacing:2px;color:#C4B5FD;text-transform:uppercase;">Tirth Ghumo · VR Darshan</p>
                    <h1 style="margin:0;font-size:24px;font-weight:700;color:#FFFFFF;line-height:1.3;">New Booking Request</h1>
                    <p style="margin:8px 0 0 0;font-size:13px;color:#DDD6FE;">Action required · Booking <span style="font-weight:700;color:#FFFFFF;">#{booking.id}</span></p>
                  </td>
                  <td align="right" valign="top">
                    <span style="display:inline-block;background:#FEF3C7;color:#92400E;font-size:11px;font-weight:700;letter-spacing:1px;text-transform:uppercase;padding:5px 12px;border-radius:20px;">Pending</span>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- Body Card -->
          <tr>
            <td style="background:#FFFFFF;padding:32px 36px;border-left:1px solid #EDE9FE;border-right:1px solid #EDE9FE;">

              <!-- Contact Details -->
              <p style="margin:0 0 12px 0;font-size:10px;font-weight:700;letter-spacing:2px;color:#7C3AED;text-transform:uppercase;">Contact Details</p>
              <table width="100%" cellpadding="0" cellspacing="0" style="border:1px solid #EDE9FE;border-radius:8px;overflow:hidden;margin-bottom:24px;">
                <tr style="background:#F5F3FF;">
                  <td style="padding:10px 16px;font-size:12px;font-weight:600;color:#6B7280;width:40%;border-bottom:1px solid #EDE9FE;">Name</td>
                  <td style="padding:10px 16px;font-size:13px;font-weight:600;color:#1F2937;border-bottom:1px solid #EDE9FE;">{booking.full_name}</td>
                </tr>
                <tr>
                  <td style="padding:10px 16px;font-size:12px;font-weight:600;color:#6B7280;border-bottom:1px solid #EDE9FE;">Phone</td>
                  <td style="padding:10px 16px;font-size:13px;color:#1F2937;border-bottom:1px solid #EDE9FE;">{booking.contact_number}</td>
                </tr>
                <tr style="background:#F5F3FF;">
                  <td style="padding:10px 16px;font-size:12px;font-weight:600;color:#6B7280;border-bottom:1px solid #EDE9FE;">WhatsApp</td>
                  <td style="padding:10px 16px;font-size:13px;color:#1F2937;border-bottom:1px solid #EDE9FE;">{booking.whatsapp_number}</td>
                </tr>
                <tr>
                  <td style="padding:10px 16px;font-size:12px;font-weight:600;color:#6B7280;">Address</td>
                  <td style="padding:10px 16px;font-size:13px;color:#1F2937;">{booking.address}</td>
                </tr>
              </table>

              <!-- Session Details -->
              <p style="margin:0 0 12px 0;font-size:10px;font-weight:700;letter-spacing:2px;color:#7C3AED;text-transform:uppercase;">Session Details</p>
              <table width="100%" cellpadding="0" cellspacing="0" style="border:1px solid #EDE9FE;border-radius:8px;overflow:hidden;margin-bottom:24px;">
                <tr style="background:#F5F3FF;">
                  <td style="padding:10px 16px;font-size:12px;font-weight:600;color:#6B7280;width:40%;border-bottom:1px solid #EDE9FE;">No. of Persons</td>
                  <td style="padding:10px 16px;font-size:13px;font-weight:600;color:#1F2937;border-bottom:1px solid #EDE9FE;">{booking.persons}</td>
                </tr>
                <tr>
                  <td style="padding:10px 16px;font-size:12px;font-weight:600;color:#6B7280;">Slot Time</td>
                  <td style="padding:10px 16px;font-size:13px;color:#1F2937;">{booking.slot_time}</td>
                </tr>
              </table>

              <!-- Payment -->
              <p style="margin:0 0 12px 0;font-size:10px;font-weight:700;letter-spacing:2px;color:#7C3AED;text-transform:uppercase;">Payment</p>
              <table width="100%" cellpadding="0" cellspacing="0" style="border:1px solid #EDE9FE;border-radius:8px;overflow:hidden;margin-bottom:32px;">
                <tr style="background:#F5F3FF;">
                  <td style="padding:10px 16px;font-size:12px;font-weight:600;color:#6B7280;width:40%;">Screenshot</td>
                  <td style="padding:10px 16px;font-size:13px;color:#1F2937;">{payment_screenshot_html}</td>
                </tr>
              </table>

              <!-- Divider -->
              <hr style="border:none;border-top:1px solid #EDE9FE;margin:0 0 28px 0;" />

              <!-- Action Buttons -->
              <p style="margin:0 0 16px 0;font-size:10px;font-weight:700;letter-spacing:2px;color:#7C3AED;text-transform:uppercase;">Admin Actions</p>

              <!-- Approve -->
              <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:12px;">
                <tr>
                  <td>
                    <a href="{approve_url}" target="_blank"
                       style="display:block;background:linear-gradient(135deg,#059669,#10B981);color:#FFFFFF;text-decoration:none;font-size:14px;font-weight:700;text-align:center;padding:14px 24px;border-radius:8px;letter-spacing:0.5px;">
                      ✅ &nbsp; Approve Booking
                    </a>
                  </td>
                </tr>
              </table>

              <!-- Decline Payment -->
              <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:12px;">
                <tr>
                  <td>
                    <a href="{decline_url}" target="_blank"
                       style="display:block;background:#FFFFFF;color:#DC2626;text-decoration:none;font-size:14px;font-weight:700;text-align:center;padding:13px 24px;border-radius:8px;letter-spacing:0.5px;border:2px solid #FCA5A5;">
                      ❌ &nbsp; Decline — Booking Declined
                    </a>
                  </td>
                </tr>
              </table>

              

            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="background:#F5F3FF;border:1px solid #EDE9FE;border-top:none;border-radius:0 0 12px 12px;padding:20px 36px;text-align:center;">
              <p style="margin:0;font-size:11px;color:#9CA3AF;">Automated notification · TirthGhumo VR Darshan System</p>
              <p style="margin:4px 0 0 0;font-size:11px;color:#9CA3AF;">Do not reply to this email.</p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>

</body>
</html>
"""

    resend.Emails.send({
        "from": "Tirth Ghumo <no-reply@tirthghumo.in>",
        "to": ["booking.tirthghumo@gmail.com"],
        "subject": f"[Action Required] VR Darshan Booking #{booking.id} — {booking.full_name}",
        "html": html_body,
    })
    print("mail sent")