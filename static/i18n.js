(function () {
  'use strict';

  var STRINGS = {
    es: {
      // Sidebar
      sidebar_title:  'Categorías',
      nav_games:      'Juegos',
      nav_licenses:   'Licencias',
      nav_subs:       'Suscripciones',
      // User dropdown
      menu_settings:  'Ajustes',
      menu_language:  'Idioma',
      menu_logout:    'Cerrar sesión',
      // Auth buttons
      btn_login:      'Iniciar sesión',
      btn_register:   'Registrarse',
      // Index — sections
      sec_games_pfx:  'Juegos',
      sec_pop:        'Populares',
      sec_trend_pfx:  'Juegos',
      sec_trend:      'Tendencia',
      sec_ltd_pfx:    '⏰ Ofertas',
      sec_ltd:        'por Tiempo Limitado',
      badge_expires:  'Vencen en <7 días',
      cat_games:      'Juegos',
      stat_shown:     'Mostrados',
      // Controls
      label_store:    'Tienda',
      opt_all:        'Todas',
      label_price:    'Precio máx. (USD)',
      ph_price:       'Cualquiera',
      label_sort:     'Ordenar por',
      sort_disc:      'Mayor descuento',
      sort_popular:   'Más populares',
      sort_pasc:      'Precio: menor a mayor',
      sort_pdesc:     'Precio: mayor a menor',
      sort_az:        'Alfabético A–Z',
      sort_za:        'Alfabético Z–A',
      btn_reset:      '↺ Reset',
      ph_search:      'Buscar juego...',
      // Empty state
      empty_msg:      'No se encontraron juegos con esos filtros.',
      empty_btn:      'Limpiar filtros',
      // Cards (used by app.js)
      badge_free:     '🎁 GRATIS',
      badge_hot:      '🔥 OFERTA',
      flag_new:       'Nuevo mínimo',
      flag_hist:      'Mínimo histórico',
      flag_store:     'Mínimo en tienda',
      exp_today:      'Vence hoy',
      exp_days:       'Vence en {n}d',
      price_free:     'GRATIS',
      // Carousel
      car_deal:       'Ver oferta',
      car_itad:       'Ver en ITAD',
      car_hot:        '🔥 OFERTA',
      // Settings
      settings_title: 'Ajustes',
      settings_acct:  'Cuenta',
      settings_email: 'Correo electrónico',
      settings_since: 'Miembro desde',
      settings_soon:  'Más opciones próximamente.',
      // Game detail — navigation & hero
      gd_back:         '← Volver a ofertas',
      gd_in:           'en',
      gd_offer_cta:    'Ver oferta →',
      // Game detail — tabs
      gd_tab_offers:   'Ofertas',
      gd_tab_dlcs:     'DLCs',
      gd_tab_arts:     'Artículos',
      gd_tab_streams:  'Streams',
      gd_tab_similar:  'Juegos similares',
      // Game detail — section titles
      gd_sec_offers:   'Ofertas',
      gd_sec_dlcs:     'DLCs y expansiones',
      gd_sec_arts:     'Artículos',
      gd_sec_streams:  'Streams en vivo',
      gd_sec_similar:  'Juegos similares',
      gd_sec_ratings:  'Calificaciones de jugadores',
      gd_sec_info:     'Información',
      gd_sec_desc:     'Descripción',
      gd_sec_history:  'Historial de precios',
      gd_sec_ss:       'Capturas de pantalla',
      gd_sec_reqs:     'Requisitos de sistema (PC)',
      gd_sec_tags:     'Etiquetas',
      // Game detail — info labels
      gd_info_dev:     'Desarrollador',
      gd_info_pub:     'Publisher',
      gd_info_rel:     'Lanzamiento',
      gd_info_genres:  'Géneros',
      gd_info_plat:    'Plataformas',
      gd_info_esrb:    'Clasificación',
      gd_info_web:     'Web oficial',
      gd_info_mc:      'Metacritic por plataforma',
      // Game detail — description
      gd_read_more:    'Leer más ↓',
      // Game detail — price history
      gd_ins_min:      'Mínimo histórico',
      gd_ins_disc:     'Descuento promedio',
      gd_ins_days:     'Última oferta',
      gd_hist_load:    'Cargando historial...',
      gd_hist_na:      'Historial no disponible para este juego.',
      gd_hist_err:     'Error al cargar el historial.',
      gd_days_ago:     'Hace {n} días',
      gd_price_lbl:    'Precio ({c})',
      // Game detail — system requirements
      gd_req_min:      'Mínimos',
      gd_req_rec:      'Recomendados',
      // Game detail — JS empty states & errors
      gd_sec_err:      'No se pudo cargar esta sección.',
      gd_no_offers:    'No hay ofertas disponibles en este momento.',
      gd_offer_btn:    'Ver oferta →',
      gd_no_dlcs:      'No hay DLCs disponibles.',
      gd_no_arts:      'No hay artículos disponibles.',
      gd_no_streams:   'No hay datos de streams disponibles.',
      gd_no_similar:   'No hay juegos similares disponibles.',
      // Sidebar
      nav_wishlist:    'Mis Deseados',
      // Wishlist menu labels
      menu_wishlist:    'Guardar en deseados',
      menu_in_wishlist: 'En deseados',
      // Wishlist errors
      wl_err:          'Error al actualizar la lista de deseados',
      wl_remove_confirm: '¿Quitar de deseados?',
      wl_remove_yes:   'Sí, quitar',
      wl_remove_no:    'Cancelar',
      wl_price_invalid: 'Precio inválido',
      // Wishlist — price alert
      wl_alert_lbl:    'Alerta de precio',
      wl_alert_ph:     'Precio objetivo',
      wl_alert_set:    'Guardar alerta',
      wl_alert_clear:  'Quitar alerta',
      wl_alert_saved:  'Alerta guardada',
      wl_alert_active: 'Alerta activa: {c} {p}',
      wl_alert_err:    'Error al guardar la alerta',
      // Collections
      menu_own:        'Ya lo tengo',
      menu_unown:      'Quitar de mi colección',
      col_err:         'Error al actualizar la colección',
      col_owned_badge: '✓ Tengo',
      // Historical low
      hist_low_lbl:    'Mín. hist.',
    },
    en: {
      sidebar_title:  'Categories',
      nav_games:      'Games',
      nav_licenses:   'Licenses',
      nav_subs:       'Subscriptions',
      menu_settings:  'Settings',
      menu_language:  'Language',
      menu_logout:    'Sign out',
      btn_login:      'Sign in',
      btn_register:   'Sign up',
      sec_games_pfx:  'Games',
      sec_pop:        'Popular',
      sec_trend_pfx:  'Games',
      sec_trend:      'Trending',
      sec_ltd_pfx:    '⏰ Deals',
      sec_ltd:        'Time-Limited',
      badge_expires:  'Expires in <7 days',
      cat_games:      'Games',
      stat_shown:     'Shown',
      label_store:    'Store',
      opt_all:        'All',
      label_price:    'Max price (USD)',
      ph_price:       'Any',
      label_sort:     'Sort by',
      sort_disc:      'Biggest discount',
      sort_popular:   'Most popular',
      sort_pasc:      'Price: low to high',
      sort_pdesc:     'Price: high to low',
      sort_az:        'A–Z',
      sort_za:        'Z–A',
      btn_reset:      '↺ Reset',
      ph_search:      'Search game...',
      empty_msg:      'No games found with those filters.',
      empty_btn:      'Clear filters',
      badge_free:     '🎁 FREE',
      badge_hot:      '🔥 DEAL',
      flag_new:       'New low',
      flag_hist:      'Historical low',
      flag_store:     'Store low',
      exp_today:      'Expires today',
      exp_days:       'Expires in {n}d',
      price_free:     'FREE',
      car_deal:       'Get deal',
      car_itad:       'View on ITAD',
      car_hot:        '🔥 DEAL',
      settings_title: 'Settings',
      settings_acct:  'Account',
      settings_email: 'Email address',
      settings_since: 'Member since',
      settings_soon:  'More options coming soon.',
      // Game detail — navigation & hero
      gd_back:         '← Back to deals',
      gd_in:           'at',
      gd_offer_cta:    'Get deal →',
      // Game detail — tabs
      gd_tab_offers:   'Deals',
      gd_tab_dlcs:     'DLCs',
      gd_tab_arts:     'Articles',
      gd_tab_streams:  'Streams',
      gd_tab_similar:  'Similar games',
      // Game detail — section titles
      gd_sec_offers:   'Deals',
      gd_sec_dlcs:     'DLCs & Expansions',
      gd_sec_arts:     'Articles',
      gd_sec_streams:  'Live Streams',
      gd_sec_similar:  'Similar Games',
      gd_sec_ratings:  'Player Ratings',
      gd_sec_info:     'Information',
      gd_sec_desc:     'Description',
      gd_sec_history:  'Price History',
      gd_sec_ss:       'Screenshots',
      gd_sec_reqs:     'System Requirements (PC)',
      gd_sec_tags:     'Tags',
      // Game detail — info labels
      gd_info_dev:     'Developer',
      gd_info_pub:     'Publisher',
      gd_info_rel:     'Release',
      gd_info_genres:  'Genres',
      gd_info_plat:    'Platforms',
      gd_info_esrb:    'Rating',
      gd_info_web:     'Official website',
      gd_info_mc:      'Metacritic by platform',
      // Game detail — description
      gd_read_more:    'Read more ↓',
      // Game detail — price history
      gd_ins_min:      'Historical Low',
      gd_ins_disc:     'Avg. Discount',
      gd_ins_days:     'Last Sale',
      gd_hist_load:    'Loading history...',
      gd_hist_na:      'No history available for this game.',
      gd_hist_err:     'Error loading history.',
      gd_days_ago:     '{n} days ago',
      gd_price_lbl:    'Price ({c})',
      // Game detail — system requirements
      gd_req_min:      'Minimum',
      gd_req_rec:      'Recommended',
      // Game detail — JS empty states & errors
      gd_sec_err:      'Could not load this section.',
      gd_no_offers:    'No deals available at the moment.',
      gd_offer_btn:    'Get deal →',
      gd_no_dlcs:      'No DLCs available.',
      gd_no_arts:      'No articles available.',
      gd_no_streams:   'No stream data available.',
      gd_no_similar:   'No similar games available.',
      // Sidebar
      nav_wishlist:    'My Wishlist',
      // Wishlist menu labels
      menu_wishlist:    'Add to wishlist',
      menu_in_wishlist: 'In wishlist',
      // Wishlist errors
      wl_err:          'Error updating wishlist',
      wl_remove_confirm: 'Remove from wishlist?',
      wl_remove_yes:   'Remove',
      wl_remove_no:    'Cancel',
      wl_price_invalid: 'Invalid price',
      // Wishlist — price alert
      wl_alert_lbl:    'Price alert',
      wl_alert_ph:     'Target price',
      wl_alert_set:    'Save alert',
      wl_alert_clear:  'Clear alert',
      wl_alert_saved:  'Alert saved',
      wl_alert_active: 'Alert active: {c} {p}',
      wl_alert_err:    'Error saving alert',
      // Collections
      menu_own:        'I own this',
      menu_unown:      'Remove from collection',
      col_err:         'Error updating collection',
      col_owned_badge: '✓ Owned',
      // Historical low
      hist_low_lbl:    'Hist. low',
    },
  };

  var lang = localStorage.getItem('gd-lang') || 'es';

  function tx(key, vars) {
    var s = (STRINGS[lang] || STRINGS.es)[key];
    if (s === undefined) return key;
    if (vars) {
      Object.keys(vars).forEach(function (k) {
        s = s.replace('{' + k + '}', vars[k]);
      });
    }
    return s;
  }

  function applyDOM() {
    var t = STRINGS[lang] || STRINGS.es;
    document.querySelectorAll('[data-i18n]').forEach(function (el) {
      var key = el.getAttribute('data-i18n');
      if (t[key] !== undefined) el.textContent = t[key];
    });
    document.querySelectorAll('[data-i18n-ph]').forEach(function (el) {
      var key = el.getAttribute('data-i18n-ph');
      if (t[key] !== undefined) el.placeholder = t[key];
    });
    document.querySelectorAll('.ud-lang-btn').forEach(function (btn) {
      btn.classList.toggle('ud-lang-btn--active', btn.getAttribute('data-lang') === lang);
    });
    // Update the header lang code badge
    var codeEl = document.getElementById('gd-lang-code');
    if (codeEl) codeEl.textContent = lang.toUpperCase();
    window.GD_tx = tx;
  }

  window.GD_setLang = function (l) {
    if (!STRINGS[l]) return;
    lang = l;
    localStorage.setItem('gd-lang', l);
    applyDOM();
    document.dispatchEvent(new CustomEvent('lang:changed'));
  };

  window.GD_tx = tx;

  applyDOM();
  document.addEventListener('deals:rendered', applyDOM);
})();
