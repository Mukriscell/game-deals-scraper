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
