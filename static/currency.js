(function () {
  'use strict';

  const CURRENCIES = [
    { code: 'USD', symbol: 'US$',  name: 'Dólar Americano', flag: '🇺🇸', decimals: 2 },
    { code: 'CLP', symbol: 'CLP$', name: 'Peso Chileno',    flag: '🇨🇱', decimals: 0 },
    { code: 'EUR', symbol: '€',    name: 'Euro',            flag: '🇪🇺', decimals: 2 },
    { code: 'GBP', symbol: '£',    name: 'Libra Esterlina', flag: '🇬🇧', decimals: 2 },
    { code: 'BRL', symbol: 'R$',   name: 'Real Brasileño',  flag: '🇧🇷', decimals: 2 },
  ];

  const RATES_KEY = 'gd_fx_rates_v1';
  const SEL_KEY   = 'gd_fx_sel';
  const CACHE_TTL = 6 * 60 * 60 * 1000; // 6 h

  let rates    = {};
  let selected = localStorage.getItem(SEL_KEY) || 'USD';

  // ── Format ──────────────────────────────────────────────────────
  function getCur() {
    return CURRENCIES.find(c => c.code === selected) || CURRENCIES[0];
  }

  function formatAmount(usd) {
    const cur    = getCur();
    const rate   = selected === 'USD' ? 1 : (rates[selected] || 1);
    const amount = usd * rate;
    if (cur.decimals === 0) {
      return `${cur.symbol} ${Math.round(amount).toLocaleString('es-CL')}`;
    }
    return `${cur.symbol} ${amount.toFixed(cur.decimals)}`;
  }

  // Expose so app.js can use it when rendering cards
  window.gd_formatPrice = formatAmount;

  // ── Apply conversion to every [data-usd] element ─────────────
  function applyConversion() {
    document.querySelectorAll('[data-usd]').forEach(el => {
      const usd = parseFloat(el.dataset.usd);
      if (isNaN(usd)) return;
      const period = el.querySelector('.plan-period');
      if (period) {
        el.innerHTML = `${formatAmount(usd)} <span class="plan-period">/mes</span>`;
      } else {
        el.textContent = formatAmount(usd);
      }
    });
  }

  // ── Widget UI ───────────────────────────────────────────────────
  function updateBtn() {
    const el = document.getElementById('gd-cx-code');
    if (el) el.textContent = getCur().code;
  }

  function renderOptions() {
    const list = document.getElementById('gd-cx-list');
    if (!list) return;
    list.innerHTML = CURRENCIES.map(c => `
      <button class="cx-option${c.code === selected ? ' cx-option--active' : ''}" data-cx="${c.code}">
        <span class="cx-flag">${c.flag}</span>
        <span class="cx-name">${c.name}</span>
        <span class="cx-sym">${c.symbol}</span>
      </button>`).join('');
    list.querySelectorAll('[data-cx]').forEach(btn => {
      btn.addEventListener('click', () => {
        selected = btn.dataset.cx;
        localStorage.setItem(SEL_KEY, selected);
        renderOptions();
        updateBtn();
        applyConversion();
        closePanel();
      });
    });
  }

  function closePanel()  { document.getElementById('gd-cx-panel')?.classList.remove('cx-panel--open'); }
  function togglePanel() { document.getElementById('gd-cx-panel')?.classList.toggle('cx-panel--open'); }

  // ── Fetch rates (ExchangeRate-API open endpoint, no key needed) ─
  async function fetchRates() {
    const cached = localStorage.getItem(RATES_KEY);
    if (cached) {
      try {
        const { ts, data } = JSON.parse(cached);
        if (Date.now() - ts < CACHE_TTL) { rates = data; return; }
      } catch (_) { /* stale cache, re-fetch */ }
    }
    try {
      const resp = await fetch('https://open.exchangerate-api.com/v6/latest/USD');
      const json = await resp.json();
      if (json.rates) {
        rates = json.rates;
        localStorage.setItem(RATES_KEY, JSON.stringify({ ts: Date.now(), data: rates }));
      }
    } catch (e) {
      console.warn('[currency] Rate fetch failed:', e);
    }
  }

  // ── Init ────────────────────────────────────────────────────────
  function init() {
    document.getElementById('gd-cx-btn')?.addEventListener('click', e => {
      e.stopPropagation();
      togglePanel();
    });
    document.addEventListener('click', e => {
      if (!e.target.closest('#gd-cx-widget')) closePanel();
    });
    document.addEventListener('keydown', e => { if (e.key === 'Escape') closePanel(); });
    document.addEventListener('deals:rendered', applyConversion);

    renderOptions();
    updateBtn();
    fetchRates().then(applyConversion);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
