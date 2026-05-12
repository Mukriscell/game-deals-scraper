import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


def is_configured() -> bool:
    return bool(
        os.environ.get('MAIL_SERVER') and
        os.environ.get('MAIL_USERNAME') and
        os.environ.get('MAIL_PASSWORD')
    )


def send_verification_email(to_email: str, code: str) -> bool:
    """Sends a 6-digit verification code. Returns True on success."""
    server    = os.environ.get('MAIL_SERVER', '')
    port      = int(os.environ.get('MAIL_PORT', '587'))
    username  = os.environ.get('MAIL_USERNAME', '')
    password  = os.environ.get('MAIL_PASSWORD', '')
    from_addr = os.environ.get('MAIL_FROM', username)

    if not (server and username and password):
        return False

    msg = MIMEMultipart('alternative')
    msg['Subject'] = 'Tu código de verificación – GAMEDEALS'
    msg['From']    = from_addr
    msg['To']      = to_email

    html = f"""<!DOCTYPE html>
<html>
<body style="margin:0;padding:1.5rem;background:#0d1117;font-family:sans-serif">
  <div style="max-width:460px;margin:auto;background:#13171f;border-radius:12px;
              padding:2rem;border:1px solid #2a3040">
    <h2 style="margin-top:0;color:#f0c040;font-size:1.4rem">
      🎮 GAME<span style="color:#c4cad6">DEALS</span>
    </h2>
    <p style="color:#c4cad6;margin-bottom:.5rem">Tu código de verificación es:</p>
    <div style="font-size:2.6rem;font-weight:700;letter-spacing:.6rem;color:#fff;
                background:#1e2430;border-radius:10px;padding:1.1rem 1.5rem;
                text-align:center;margin:1.2rem 0;border:1px solid #2a3040">
      {code}
    </div>
    <p style="font-size:.83rem;color:#8892a0;margin-bottom:0">
      Este código es válido por <strong style="color:#c4cad6">30 minutos</strong>.<br>
      Si no solicitaste esto, ignora este correo.
    </p>
  </div>
</body>
</html>"""

    msg.attach(MIMEText(html, 'html'))

    try:
        if port == 465:
            with smtplib.SMTP_SSL(server, port, timeout=10) as smtp:
                smtp.login(username, password)
                smtp.sendmail(from_addr, to_email, msg.as_string())
        else:
            with smtplib.SMTP(server, port, timeout=10) as smtp:
                smtp.ehlo()
                smtp.starttls()
                smtp.login(username, password)
                smtp.sendmail(from_addr, to_email, msg.as_string())
        return True
    except Exception:
        return False
