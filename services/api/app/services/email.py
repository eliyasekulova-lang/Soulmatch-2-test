import logging
from enum import Enum

import httpx

logger = logging.getLogger("soulmatch.email")


class EmailTemplate(str, Enum):
    BETA_WELCOME = "beta_welcome"
    SUBSCRIPTION_CONFIRMED = "subscription_confirmed"
    SUBSCRIPTION_CANCELED = "subscription_canceled"


def _beta_welcome_html(position: int) -> str:
    if 11 <= (position % 100) <= 13:
        suffix = "th"
    elif position % 10 == 1:
        suffix = "st"
    elif position % 10 == 2:
        suffix = "nd"
    elif position % 10 == 3:
        suffix = "rd"
    else:
        suffix = "th"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>You're on the SoulMatch waitlist</title>
</head>
<body style="margin:0;padding:0;background:#0B0E14;font-family:'Helvetica Neue',Arial,sans-serif;color:#E8E8F0;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#0B0E14;padding:40px 0;">
    <tr>
      <td align="center">
        <table width="560" cellpadding="0" cellspacing="0" style="max-width:560px;width:100%;">

          <!-- Logo / wordmark -->
          <tr>
            <td style="padding:0 0 32px 0;text-align:center;">
              <span style="font-size:28px;font-weight:800;background:linear-gradient(135deg,#7B2FBE,#E040FB);-webkit-background-clip:text;-webkit-text-fill-color:transparent;letter-spacing:-0.5px;">SoulMatch</span>
            </td>
          </tr>

          <!-- Hero card -->
          <tr>
            <td style="background:#151822;border-radius:16px;padding:40px 36px;">
              <p style="margin:0 0 8px 0;font-size:13px;font-weight:600;color:#7B2FBE;text-transform:uppercase;letter-spacing:1px;">You&rsquo;re in</p>
              <h1 style="margin:0 0 16px 0;font-size:28px;font-weight:800;line-height:1.2;color:#F0F0FA;">
                You&rsquo;re #{position:,}{suffix} on the waitlist.
              </h1>
              <p style="margin:0 0 24px 0;font-size:16px;line-height:1.6;color:#A0A0C0;">
                We&rsquo;re building something different — matchmaking that starts with <strong style="color:#E8E8F0;">who you actually are</strong>, not just your photos.
              </p>
              <p style="margin:0;font-size:15px;line-height:1.6;color:#A0A0C0;">
                SoulMatch maps your psychology across 12 dimensions — attachment style, conflict approach, core values, emotional regulation — and finds people who complement you deeply, for both romance and friendship.
              </p>
            </td>
          </tr>

          <!-- What to expect -->
          <tr>
            <td style="padding:24px 0 0 0;">
              <table width="100%" cellpadding="0" cellspacing="0">
                <tr>
                  <td width="50%" style="padding:0 8px 16px 0;">
                    <div style="background:#151822;border-radius:12px;padding:20px;">
                      <div style="font-size:22px;margin-bottom:8px;">&#129488;</div>
                      <p style="margin:0 0 4px 0;font-size:14px;font-weight:700;color:#E8E8F0;">Deep Assessment</p>
                      <p style="margin:0;font-size:13px;color:#808098;line-height:1.5;">12 scientifically-grounded questions that map your attachment style, values, and communication patterns.</p>
                    </div>
                  </td>
                  <td width="50%" style="padding:0 0 16px 8px;">
                    <div style="background:#151822;border-radius:12px;padding:20px;">
                      <div style="font-size:22px;margin-bottom:8px;">&#129309;</div>
                      <p style="margin:0 0 4px 0;font-size:14px;font-weight:700;color:#E8E8F0;">Complementary Matches</p>
                      <p style="margin:0;font-size:13px;color:#808098;line-height:1.5;">We find people who complement you — not just who&rsquo;s similar — for both romance and friendship.</p>
                    </div>
                  </td>
                </tr>
                <tr>
                  <td width="50%" style="padding:0 8px 0 0;">
                    <div style="background:#151822;border-radius:12px;padding:20px;">
                      <div style="font-size:22px;margin-bottom:8px;">&#127757;</div>
                      <p style="margin:0 0 4px 0;font-size:14px;font-weight:700;color:#E8E8F0;">Behaviour Signals</p>
                      <p style="margin:0;font-size:13px;color:#808098;line-height:1.5;">Your response patterns refine your profile over time — the more you use it, the more accurate it gets.</p>
                    </div>
                  </td>
                  <td width="50%" style="padding:0 0 0 8px;">
                    <div style="background:#151822;border-radius:12px;padding:20px;">
                      <div style="font-size:22px;margin-bottom:8px;">&#11088;</div>
                      <p style="margin:0 0 4px 0;font-size:14px;font-weight:700;color:#E8E8F0;">Astrology (Optional)</p>
                      <p style="margin:0;font-size:13px;color:#808098;line-height:1.5;">Add your birth chart for an astrology compatibility layer — enrichment on top of the science, never instead of it.</p>
                    </div>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- CTA -->
          <tr>
            <td style="padding:24px 0 0 0;text-align:center;">
              <a href="https://soulmatch.app" style="display:inline-block;padding:14px 36px;background:linear-gradient(135deg,#7B2FBE,#E040FB);color:#fff;text-decoration:none;border-radius:50px;font-size:15px;font-weight:700;letter-spacing:0.3px;">Visit SoulMatch</a>
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="padding:32px 0 0 0;text-align:center;">
              <p style="margin:0 0 8px 0;font-size:12px;color:#50506A;">
                You signed up for early access at soulmatch.app
              </p>
              <p style="margin:0;font-size:12px;color:#50506A;">
                Questions? <a href="mailto:support@soulmatch.app" style="color:#7B2FBE;text-decoration:none;">support@soulmatch.app</a>
                &nbsp;&middot;&nbsp;
                <a href="https://soulmatch.app/legal/privacy" style="color:#7B2FBE;text-decoration:none;">Privacy Policy</a>
              </p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


def _subscription_confirmed_html() -> str:
    return """<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"/><title>Welcome to SoulMatch Premium</title></head>
<body style="margin:0;padding:0;background:#0B0E14;font-family:'Helvetica Neue',Arial,sans-serif;color:#E8E8F0;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#0B0E14;padding:40px 0;">
    <tr><td align="center">
      <table width="560" cellpadding="0" cellspacing="0" style="max-width:560px;width:100%;">
        <tr><td style="padding:0 0 32px 0;text-align:center;">
          <span style="font-size:28px;font-weight:800;background:linear-gradient(135deg,#7B2FBE,#E040FB);-webkit-background-clip:text;-webkit-text-fill-color:transparent;">SoulMatch Premium</span>
        </td></tr>
        <tr><td style="background:#151822;border-radius:16px;padding:40px 36px;">
          <h1 style="margin:0 0 16px 0;font-size:26px;font-weight:800;color:#F0F0FA;">Welcome to Premium &#127775;</h1>
          <p style="margin:0 0 20px 0;font-size:16px;line-height:1.6;color:#A0A0C0;">
            Your premium subscription is now active. You now have access to unlimited matches, full compatibility reports, and detailed psychological insights.
          </p>
          <p style="margin:0;font-size:14px;line-height:1.6;color:#808098;">
            Manage your subscription any time from the Settings screen in the app.
          </p>
        </td></tr>
        <tr><td style="padding:32px 0 0 0;text-align:center;">
          <p style="margin:0;font-size:12px;color:#50506A;">Questions? <a href="mailto:support@soulmatch.app" style="color:#7B2FBE;text-decoration:none;">support@soulmatch.app</a></p>
        </td></tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""


async def send_email(
    *,
    to: str,
    subject: str,
    html: str,
    from_address: str = "SoulMatch <hello@soulmatch.app>",
    resend_api_key: str,
) -> bool:
    if not resend_api_key:
        logger.warning("email_skipped_no_api_key", extra={"to": to})
        return False

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                "https://api.resend.com/emails",
                headers={"Authorization": f"Bearer {resend_api_key}", "Content-Type": "application/json"},
                json={"from": from_address, "to": [to], "subject": subject, "html": html},
            )
        if resp.status_code == 200:
            logger.info("email_sent", extra={"to_domain": to.split("@")[-1], "subject": subject})
            return True
        else:
            logger.warning("email_send_failed", extra={"status": resp.status_code, "body": resp.text[:200]})
            return False
    except Exception as exc:
        logger.error("email_send_error", extra={"error": str(exc)})
        return False


async def send_beta_welcome(to: str, position: int, resend_api_key: str) -> bool:
    return await send_email(
        to=to,
        subject="You're on the SoulMatch waitlist",
        html=_beta_welcome_html(position),
        resend_api_key=resend_api_key,
    )


async def send_subscription_confirmed(to: str, resend_api_key: str) -> bool:
    return await send_email(
        to=to,
        subject="Welcome to SoulMatch Premium",
        html=_subscription_confirmed_html(),
        resend_api_key=resend_api_key,
    )
