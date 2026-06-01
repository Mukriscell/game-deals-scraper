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


def _send(to_email: str, subject: str, html: str) -> bool:
    server    = os.environ.get('MAIL_SERVER', '')
    port      = int(os.environ.get('MAIL_PORT', '587'))
    username  = os.environ.get('MAIL_USERNAME', '')
    password  = os.environ.get('MAIL_PASSWORD', '')
    from_addr = os.environ.get('MAIL_FROM', username)

    if not (server and username and password):
        return False

    to_email  = to_email.replace('\n', '').replace('\r', '').strip()
    subject   = subject.replace('\n', '').replace('\r', '').strip()
    from_addr = from_addr.replace('\n', '').replace('\r', '').strip()

    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From']    = from_addr
    msg['To']      = to_email
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


def send_password_reset_email(to_email: str, code: str) -> bool:
    html = f"""<!DOCTYPE html>
<html>
<body style="margin:0;padding:1.5rem;background:#0d1117;font-family:sans-serif">
  <div style="max-width:460px;margin:auto;background:#13171f;border-radius:12px;
              padding:2rem;border:1px solid #2a3040">
    <h2 style="margin-top:0;color:#f0c040;font-size:1.4rem">
      🎮 BALA<span style="color:#c4cad6">TO</span>
    </h2>
    <p style="color:#c4cad6;margin-bottom:.5rem">
      Recibimos una solicitud para restablecer tu contraseña.
      Usa este código para continuar:
    </p>
    <div style="font-size:2.6rem;font-weight:700;letter-spacing:.6rem;color:#fff;
                background:#1e2430;border-radius:10px;padding:1.1rem 1.5rem;
                text-align:center;margin:1.2rem 0;border:1px solid #2a3040">
      {code}
    </div>
    <p style="font-size:.83rem;color:#8892a0;margin-bottom:0">
      Este código es válido por <strong style="color:#c4cad6">15 minutos</strong>.<br>
      Si no solicitaste recuperar tu contraseña, ignora este correo.
    </p>
  </div>
</body>
</html>"""
    return _send(to_email, 'Recuperar contraseña – BALATO', html)


def send_verification_email(to_email: str, code: str) -> bool:
    html = f"""<!DOCTYPE html>
<html>
<body style="margin:0;padding:1.5rem;background:#0d1117;font-family:sans-serif">
  <div style="max-width:460px;margin:auto;background:#13171f;border-radius:12px;
              padding:2rem;border:1px solid #2a3040">
    <h2 style="margin-top:0;color:#f0c040;font-size:1.4rem">
      🎮 BALA<span style="color:#c4cad6">TO</span>
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
    return _send(to_email, 'Tu código de verificación – BALATO', html)


def send_account_deletion_email(to_email: str, code: str) -> bool:
    html = f"""<!DOCTYPE html>
<html>
<body style="margin:0;padding:1.5rem;background:#0d1117;font-family:sans-serif">
  <div style="max-width:460px;margin:auto;background:#13171f;border-radius:12px;
              padding:2rem;border:1px solid #2a3040">
    <h2 style="margin-top:0;color:#f0c040;font-size:1.4rem">
      🎮 BALA<span style="color:#c4cad6">TO</span>
    </h2>
    <p style="color:#c4cad6;margin-bottom:.5rem">
      Recibimos una solicitud para <strong style="color:#ef4444">eliminar tu cuenta</strong>.<br>
      Usa este código para confirmar. Esta acción es <strong>irreversible</strong>.
    </p>
    <div style="font-size:2.6rem;font-weight:700;letter-spacing:.6rem;color:#fff;
                background:#1e2430;border-radius:10px;padding:1.1rem 1.5rem;
                text-align:center;margin:1.2rem 0;border:1px solid #ef444440">
      {code}
    </div>
    <p style="font-size:.83rem;color:#8892a0;margin-bottom:0">
      Este código es válido por <strong style="color:#c4cad6">15 minutos</strong>.<br>
      Si no solicitaste esto, ignora este correo y tu cuenta permanecerá segura.
    </p>
  </div>
</body>
</html>"""
    return _send(to_email, 'Confirma la eliminación de tu cuenta – BALATO', html)


def send_newsletter_email(to_email: str, deals: list) -> bool:
    if not deals:
        return False
    rows_html = ""
    for d in deals[:10]:
        name     = d.get('name', '')
        price    = d.get('price', 0)
        discount = d.get('discount', 0)
        currency = d.get('currency', 'USD')
        url      = d.get('url', '')
        store    = d.get('store', '')
        thumb    = d.get('thumb', '')
        img_tag  = f'<img src="{thumb}" width="60" height="40" style="object-fit:cover;border-radius:4px;vertical-align:middle;margin-right:.7rem" alt="">' if thumb else ''
        rows_html += f"""
        <tr>
          <td style="padding:.6rem .4rem;border-bottom:1px solid #1e2430;vertical-align:middle">
            {img_tag}<strong style="color:#e0e0e0">{name}</strong>
            {'<span style="color:#8892a0;font-size:.8rem"> · ' + store + '</span>' if store else ''}
          </td>
          <td style="padding:.6rem .4rem;border-bottom:1px solid #1e2430;text-align:right;white-space:nowrap;vertical-align:middle">
            <span style="color:#4ade80;font-weight:700">{currency} {price:.2f}</span>
            <span style="color:#f0c040;font-size:.85rem;margin-left:.4rem">−{discount}%</span>
          </td>
          <td style="padding:.6rem .4rem;border-bottom:1px solid #1e2430;text-align:right;vertical-align:middle">
            <a href="{url}" style="color:#f0c040;font-size:.82rem;text-decoration:none">Ver →</a>
          </td>
        </tr>"""

    html = f"""<!DOCTYPE html>
<html>
<body style="margin:0;padding:1.5rem;background:#0d1117;font-family:sans-serif">
  <div style="max-width:560px;margin:auto;background:#13171f;border-radius:12px;
              padding:2rem;border:1px solid #2a3040">
    <h2 style="margin-top:0;color:#f0c040;font-size:1.4rem">
      🎮 BALA<span style="color:#c4cad6">TO</span>
      <span style="font-size:.9rem;color:#8892a0;font-weight:400"> · Mejores ofertas de la semana</span>
    </h2>
    <table width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse">
      {rows_html}
    </table>
    <div style="margin-top:1.4rem;text-align:center">
      <a href="https://balato.app/games"
         style="display:inline-block;background:#f0c040;color:#0d1117;font-weight:700;
                padding:.7rem 1.6rem;border-radius:8px;text-decoration:none">
        Ver todas las ofertas →
      </a>
    </div>
    <p style="font-size:.75rem;color:#4a5568;margin-top:1.5rem;margin-bottom:0;text-align:center">
      Recibiste esto porque estás suscrito al newsletter de BALATO.<br>
      Puedes cancelar tu suscripción en <a href="https://balato.app/settings" style="color:#8892a0">Ajustes de cuenta</a>.
    </p>
  </div>
</body>
</html>"""
    return _send(to_email, '🎮 Mejores ofertas de la semana — BALATO', html)


def send_price_change_email(to_email: str, name: str, old_price: float,
                             new_price: float, url: str, currency: str, store: str) -> bool:
    went_down = new_price < old_price
    direction = '📉 bajó' if went_down else '📈 subió'
    color     = '#4ade80' if went_down else '#f87171'
    arrow     = '▼' if went_down else '▲'
    diff      = abs(new_price - old_price)
    subject   = f"{'🔥 Bajó el precio' if went_down else '⚠️ Subió el precio'}: {name} – BALATO"

    html = f"""<!DOCTYPE html>
<html>
<body style="margin:0;padding:1.5rem;background:#0d1117;font-family:sans-serif">
  <div style="max-width:480px;margin:auto;background:#13171f;border-radius:12px;
              padding:2rem;border:1px solid #2a3040">
    <h2 style="margin-top:0;color:#f0c040;font-size:1.3rem">
      🎮 BALA<span style="color:#c4cad6">TO</span>
    </h2>
    <p style="color:#c4cad6;font-size:1rem;margin-bottom:1.2rem">
      El precio de un juego en tu lista de deseados <strong style="color:{color}">{direction}</strong>:
    </p>
    <div style="background:#1e2430;border-radius:10px;padding:1.2rem 1.4rem;
                border:1px solid #2a3040;margin-bottom:1.2rem">
      <div style="color:#fff;font-size:1.1rem;font-weight:600;margin-bottom:.6rem">{name}</div>
      <div style="display:flex;gap:1rem;align-items:center;flex-wrap:wrap">
        <span style="color:#8892a0;text-decoration:line-through;font-size:.95rem">
          {currency} {old_price:.2f}
        </span>
        <span style="color:{color};font-size:1.3rem;font-weight:700">
          {arrow} {currency} {new_price:.2f}
        </span>
        <span style="color:{color};font-size:.85rem">
          ({arrow} {currency} {diff:.2f})
        </span>
      </div>
      {'<div style="color:#8892a0;font-size:.82rem;margin-top:.4rem">en ' + store + '</div>' if store else ''}
    </div>
    <a href="{url}" style="display:inline-block;background:#f0c040;color:#0d1117;
       font-weight:700;padding:.7rem 1.4rem;border-radius:8px;text-decoration:none;
       font-size:.95rem">
      Ver oferta →
    </a>
    <p style="font-size:.78rem;color:#4a5568;margin-top:1.5rem;margin-bottom:0">
      Recibes esto porque tienes este juego en tu lista de deseados en BALATO.
    </p>
  </div>
</body>
</html>"""
    return _send(to_email, subject, html)


def send_price_alert_email(to_email: str, name: str, alert_price: float,
                            current_price: float, url: str, currency: str, store: str) -> bool:
    subject = f"🔔 ¡Alerta de precio alcanzada! {name} – BALATO"
    html = f"""<!DOCTYPE html>
<html>
<body style="margin:0;padding:1.5rem;background:#0d1117;font-family:sans-serif">
  <div style="max-width:480px;margin:auto;background:#13171f;border-radius:12px;
              padding:2rem;border:1px solid #2a3040">
    <h2 style="margin-top:0;color:#f0c040;font-size:1.3rem">
      🎮 BALA<span style="color:#c4cad6">TO</span>
    </h2>
    <p style="color:#c4cad6;font-size:1rem;margin-bottom:1.2rem">
      🔔 <strong>¡Tu alerta de precio se activó!</strong> El juego que vigilabas llegó a tu precio objetivo.
    </p>
    <div style="background:#1e2430;border-radius:10px;padding:1.2rem 1.4rem;
                border:1px solid #2a3040;margin-bottom:1.2rem">
      <div style="color:#fff;font-size:1.1rem;font-weight:600;margin-bottom:.6rem">{name}</div>
      <div style="display:flex;gap:1rem;align-items:center;flex-wrap:wrap">
        <span style="color:#8892a0;font-size:.9rem">Tu objetivo: {currency} {alert_price:.2f}</span>
        <span style="color:#4ade80;font-size:1.3rem;font-weight:700">
          🎯 {currency} {current_price:.2f}
        </span>
      </div>
      {'<div style="color:#8892a0;font-size:.82rem;margin-top:.4rem">en ' + store + '</div>' if store else ''}
    </div>
    <a href="{url}" style="display:inline-block;background:#f0c040;color:#0d1117;
       font-weight:700;padding:.7rem 1.4rem;border-radius:8px;text-decoration:none;
       font-size:.95rem">
      Ver oferta →
    </a>
    <p style="font-size:.78rem;color:#4a5568;margin-top:1.5rem;margin-bottom:0">
      Recibes esto porque configuraste una alerta de precio en BALATO. Puedes quitarla desde tu lista de deseados.
    </p>
  </div>
</body>
</html>"""
    return _send(to_email, subject, html)


def send_expiry_warning_email(to_email: str, name: str, price: float, expiry_str: str,
                               url: str, currency: str, store: str, days_left: int) -> bool:
    days_label = 'mañana' if days_left <= 1 else f'en {days_left} días'
    subject    = f"⏰ La oferta de {name} expira {days_label} – BALATO"

    try:
        from datetime import datetime, timezone
        exp_dt    = datetime.fromisoformat(expiry_str.replace('Z', '+00:00'))
        expiry_fmt = exp_dt.strftime('%d/%m/%Y %H:%M UTC')
    except Exception:
        expiry_fmt = expiry_str

    html = f"""<!DOCTYPE html>
<html>
<body style="margin:0;padding:1.5rem;background:#0d1117;font-family:sans-serif">
  <div style="max-width:480px;margin:auto;background:#13171f;border-radius:12px;
              padding:2rem;border:1px solid #2a3040">
    <h2 style="margin-top:0;color:#f0c040;font-size:1.3rem">
      🎮 BALA<span style="color:#c4cad6">TO</span>
    </h2>
    <p style="color:#c4cad6;font-size:1rem;margin-bottom:1.2rem">
      ⏰ Una oferta en tu lista de deseados
      <strong style="color:#f0c040">expira {days_label}</strong>:
    </p>
    <div style="background:#1e2430;border-radius:10px;padding:1.2rem 1.4rem;
                border:1px solid #f0c04040;margin-bottom:1.2rem">
      <div style="color:#fff;font-size:1.1rem;font-weight:600;margin-bottom:.6rem">{name}</div>
      <div style="color:#4ade80;font-size:1.2rem;font-weight:700;margin-bottom:.3rem">
        {currency} {price:.2f}
      </div>
      <div style="color:#8892a0;font-size:.82rem">
        Expira: <span style="color:#f0c040">{expiry_fmt}</span>
        {'&nbsp;·&nbsp;en ' + store if store else ''}
      </div>
    </div>
    <a href="{url}" style="display:inline-block;background:#f0c040;color:#0d1117;
       font-weight:700;padding:.7rem 1.4rem;border-radius:8px;text-decoration:none;
       font-size:.95rem">
      Comprar antes de que expire →
    </a>
    <p style="font-size:.78rem;color:#4a5568;margin-top:1.5rem;margin-bottom:0">
      Recibes esto porque tienes este juego en tu lista de deseados en BALATO.
    </p>
  </div>
</body>
</html>"""
    return _send(to_email, subject, html)
