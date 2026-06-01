"""
test_notify.py — Fuerza una notificación de cambio de precio para el primer
                 ítem de tu wishlist. Ejecutar con: python test_notify.py
"""
from dotenv import load_dotenv
load_dotenv()

from db import get_connection
from auth import wishlist_get_all_with_emails
from mail import send_price_change_email, send_expiry_warning_email, is_configured

def main():
    if not is_configured():
        print("ERROR: El correo no está configurado (.env MAIL_* vars)")
        return

    items = wishlist_get_all_with_emails()
    if not items:
        print("No hay ítems en ninguna wishlist. Agrega un juego primero.")
        return

    item = items[0]
    print(f"Usando: '{item['deal_name']}' del usuario {item['email']}")

    # Simular precio anterior distinto al actual
    fake_old_price = round((item['deal_price'] or 5.0) * 2, 2)
    current_price  = item['deal_price'] or 5.0
    currency       = item['deal_currency'] or 'USD'

    print(f"Enviando email: precio bajo de {currency} {fake_old_price} -> {currency} {current_price:.2f}")
    ok = send_price_change_email(
        to_email  = item['email'],
        name      = item['deal_name'],
        old_price = fake_old_price,
        new_price = current_price,
        url       = item.get('deal_url', ''),
        currency  = currency,
        store     = item.get('deal_store', ''),
    )
    print("OK Email enviado correctamente" if ok else "ERROR al enviar el email")

    # También probar aviso de expiración
    print("\nEnviando email de expiración de prueba...")
    from datetime import datetime, timezone, timedelta
    expiry_soon = (datetime.now(timezone.utc) + timedelta(hours=30)).isoformat()
    ok2 = send_expiry_warning_email(
        to_email   = item['email'],
        name       = item['deal_name'],
        price      = current_price,
        expiry_str = expiry_soon,
        url        = item.get('deal_url', ''),
        currency   = currency,
        store      = item.get('deal_store', ''),
        days_left  = 1,
    )
    print("OK Email de expiracion enviado" if ok2 else "ERROR al enviar email de expiracion")

if __name__ == '__main__':
    main()
