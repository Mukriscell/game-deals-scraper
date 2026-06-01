# BALATO — Game Deals Aggregator

Agregador de ofertas de videojuegos construido con Flask. Consolida datos de múltiples fuentes (ITAD, SteamSpy, GG.deals) en una interfaz web oscura con autenticación completa, panel de administración, wishlist, PWA y sistema de afiliados.

> Proyecto de portafolio — desplegable en Render, Railway o cualquier plataforma con soporte Python + PostgreSQL.

---

## Características

### Contenido
- **Juegos en oferta** — Cientos de deals desde Steam, GOG, Epic, Humble, Fanatical y más (via ITAD API)
- **Suscripciones** — Xbox Game Pass, PlayStation Plus, EA Play, Prime Gaming y más
- **Licencias digitales** — Cursos, ebooks y software en oferta
- **Bundles** — Packs con múltiples juegos
- **Carrusel de destacados** — Juegos populares con mayor descuento
- **Deals urgentes** — Ofertas que vencen en menos de 7 días

### UX / Frontend
- Búsqueda en tiempo real, filtros por tienda, precio máximo y orden
- Conversión de moneda en vivo: USD, CLP, EUR, GBP, BRL (via ExchangeRate-API)
- Internacionalización ES / EN
- Diseño dark mode con animaciones GPU-optimizadas (60 fps)
- PWA — instalable en móvil y escritorio (Service Worker + manifest)
- Responsive, carga lazy de imágenes

### Autenticación & Usuarios
- Registro con verificación de correo electrónico
- Login con sesión segura + rotación de versión de sesión
- Recuperación de contraseña vía email
- Cambio de email con confirmación
- Avatar personalizado (upload) o presets de iconos retro
- 2FA (TOTP compatible con Google Authenticator / Authy)

### Wishlist & Colección
- Agregar / quitar juegos de la wishlist con un click
- Marcar juegos como "ya los tengo" (colección personal)
- Ocultar juegos que no interesan
- Vista dedicada `/wishlist`

### Panel de Administración (`/admin`)
- Login independiente con 2FA
- Dashboard con métricas de uso
- Banner global configurable (marquee animado)
- Modo mantenimiento
- Gestión de usuarios (ban, eliminar, ver actividad)
- Log de errores del servidor en tiempo real
- Control del TTL de caché y carousel pin
- Blacklist de juegos

### Backend
- Caché en memoria con TTL configurable y refresh en background
- Rate limiting por IP (flask-limiter + Redis opcional)
- CSRF protection en todos los formularios y endpoints AJAX
- Headers de seguridad: CSP, X-Frame-Options, HSTS en producción
- Sistema de afiliados: tagging automático de URLs por tienda
- PostgreSQL en producción, SQLite para desarrollo local

---

## Stack tecnológico

| Capa | Tecnología |
|------|-----------|
| Backend | Python 3 + Flask 3 |
| Base de datos | PostgreSQL (producción) / SQLite (desarrollo) |
| Frontend | HTML + CSS + JS vanilla (sin frameworks) |
| Auth | Flask sessions + Werkzeug password hashing + PyOTP (2FA) |
| Email | SMTP (Gmail / Outlook) via smtplib |
| Rate limiting | flask-limiter (Redis opcional para multi-worker) |
| CSRF | Flask-WTF |
| Deploy | Gunicorn + Procfile (Render / Railway / Heroku) |
| PWA | Service Worker con cache-first para assets |

---

## APIs externas

| API | Uso | Key requerida |
|-----|-----|---------------|
| [IsThereAnyDeal](https://isthereanydeal.com/dev/app/) | Deals multi-tienda, suscripciones, historial de precios | Sí (gratis) |
| [SteamSpy](https://steamspy.com/api.php) | Popularidad y top 100 juegos Steam | No |
| [GG.deals](https://gg.deals/api/) | Mejores precios retail | Sí (gratis) |
| [RAWG](https://rawg.io/apidocs) | Metadata de juegos, screenshots, géneros | Sí (gratis) |
| [Steam Web API](https://steamcommunity.com/dev/apikey) | Importar biblioteca del usuario desde Steam | Sí (gratis) |
| [ExchangeRate-API](https://open.exchangerate-api.com) | Tasas de cambio en tiempo real | No |

---

## Instalación local

### 1. Clonar el repositorio

```bash
git clone https://github.com/tu-usuario/balato.git
cd balato
```

### 2. Crear entorno virtual e instalar dependencias

```bash
python -m venv venv

# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate

pip install -r requirements.txt
```

### 3. Configurar variables de entorno

```bash
cp .env.example .env
```

Edita `.env` con tus valores. Variables mínimas requeridas:

```env
DATABASE_URL=postgresql://usuario:contraseña@host:5432/balato
SECRET_KEY=genera-una-con-python-secrets
ITAD_API_KEY=tu-itad-key
```

Para correr localmente con SQLite puedes usar `DATABASE_URL=sqlite:///local.db`.

### 4. Ejecutar

```bash
python app.py
```

Abre [http://localhost:5000](http://localhost:5000).

El panel de administración está en `/admin/login`. Configura `ADMIN_EMAIL` y `ADMIN_PASSWORD_HASH` en `.env` (ver `.env.example` para cómo generar el hash).

---

## Estructura del proyecto

```
balato/
├── app.py                  # Factory de la app Flask
├── blueprints/
│   ├── games.py            # Rutas principales (/, /licencias, /suscripciones, etc.)
│   ├── auth.py             # Registro, login, logout, verificación email
│   ├── settings.py         # Perfil, avatar, 2FA, cambio de email/contraseña
│   ├── admin.py            # Panel de administración
│   └── api.py              # Endpoints JSON (wishlist, colección, deals)
├── scraper.py              # Integración con ITAD, SteamSpy, GG.deals, RAWG
├── cache.py                # Caché en memoria + background refresh
├── auth.py                 # Lógica de autenticación y base de datos de usuarios
├── affiliates.py           # Tagging automático de URLs de afiliados
├── admin_db.py             # Base de datos del panel admin
├── mail.py                 # Envío de emails transaccionales
├── static/
│   ├── app.js              # Lógica frontend principal
│   ├── currency.js         # Widget de conversión de moneda
│   ├── i18n.js             # Sistema de internacionalización
│   ├── sw.js               # Service Worker (PWA)
│   └── style.css           # Estilos (dark mode, animaciones)
└── templates/              # Templates Jinja2
```

---

## Deploy en Render (gratuito)

1. Crea una base de datos PostgreSQL en [Render](https://render.com) o [Neon](https://neon.tech)
2. Crea un nuevo **Web Service** conectado a este repo
3. Build command: `pip install -r requirements.txt`
4. Start command: `gunicorn wsgi:app` (el `Procfile` ya lo configura)
5. Agrega las variables de entorno desde `.env.example`
6. Setea `FLASK_ENV=production`

---

## Sistema de afiliados

El archivo `affiliates.py` contiene un mapa de dominios de tiendas a parámetros de tracking. Si configuras la variable de entorno correspondiente, los links de salida se tagean automáticamente:

```env
AFFILIATE_FANATICAL=tu-id
AFFILIATE_GMG=tu-id
# etc — ver .env.example para la lista completa
```

Las tiendas sin código configurado muestran el link original sin cambios.

---

## Licencia

MIT
