# 🎮 GameDeals Scraper

Agregador de ofertas de videojuegos, suscripciones y licencias digitales. Combina datos de **ITAD**, **SteamSpy** y **GG.deals** en una interfaz web oscura con carrusel, filtros y conversión de moneda en tiempo real.

## Características

- 🎮 **Juegos** — Cientos de ofertas desde Steam, GOG, Epic, Humble, Fanatical y más (via ITAD API)
- 📊 **SteamSpy** — Juegos populares con descuento directo desde Steam
- 🏷️ **GG.deals** — Mejores precios en tiendas retail de los 100 juegos más jugados
- ♾ **Suscripciones** — Netflix, Disney+, Xbox Game Pass, PlayStation Plus y más
- 🔑 **Licencias** — Udemy, Coursera, O'Reilly, Adobe CC, Microsoft 365 y más
- 💱 **Conversión de moneda** — USD, CLP, EUR, GBP, BRL en tiempo real
- ⏰ **Ofertas por tiempo limitado** — Deals que vencen en menos de 7 días
- 🔍 **Búsqueda y filtros** — Por tienda, precio máximo y orden

## Instalación

### 1. Clona el repositorio

```bash
git clone https://github.com/tu-usuario/game-deals-scraper.git
cd game-deals-scraper
```

### 2. Crea el entorno virtual e instala dependencias

```bash
python -m venv venv
# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate

pip install -r requirements.txt
```

### 3. Configura las API keys

```bash
cp .env.example .env
```

Edita `.env` con tus keys:

| Variable | Dónde conseguirla |
|---|---|
| `ITAD_API_KEY` | [isthereanydeal.com/dev/app](https://isthereanydeal.com/dev/app/) — gratis |
| `GGDEALS_API_KEY` | [gg.deals/api](https://gg.deals/api/) — gratis (requiere confirmar email) |

SteamSpy no requiere API key.

### 4. Ejecuta la aplicación

```bash
python app.py
```

Abre [http://localhost:5000](http://localhost:5000) en tu navegador.

## APIs utilizadas

| API | Uso | Key requerida |
|---|---|---|
| [IsThereAnyDeal](https://isthereanydeal.com/dev/app/) | Ofertas multi-tienda, suscripciones | Sí |
| [SteamSpy](https://steamspy.com/api.php) | Top 100 juegos más jugados | No |
| [GG.deals](https://gg.deals/api/) | Mejores precios retail entre tiendas | Sí |
| [ExchangeRate-API](https://open.exchangerate-api.com) | Tasas de cambio de moneda | No |

## Stack

- **Backend** — Python 3 + Flask
- **Frontend** — HTML/CSS/JS vanilla (sin frameworks)
- **Caché** — En memoria, TTL de 5 minutos
