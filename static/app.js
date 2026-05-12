// ── Elements ────────────────────────────────────────
const grid        = document.getElementById('deals-grid');
const emptyState  = document.getElementById('empty-state');
const statVisible = document.getElementById('stat-visible');
const searchInput = document.getElementById('search-input');
const searchClear = document.getElementById('search-clear');
const suggestions = document.getElementById('suggestions');
const storeFilter = document.getElementById('store-filter');
const priceFilter = document.getElementById('price-filter');
const sortFilter  = document.getElementById('sort-filter');
const btnReset    = document.getElementById('btn-reset');
const btnReset2   = document.getElementById('btn-reset2');

// ── State ────────────────────────────────────────────
let query    = '';
let storeId  = 'All';
let maxPrice = null;
let sortBy   = 'discount';

// ── Helpers ──────────────────────────────────────────
function escHtml(str) {
  return String(str)
    .replace(/&/g,'&amp;').replace(/</g,'&lt;')
    .replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

function tx(key, vars) {
  if (window.GD_tx) return window.GD_tx(key, vars);
  const FB = {
    badge_free:'🎁 GRATIS', badge_hot:'🔥 OFERTA',
    flag_new:'Nuevo mínimo', flag_hist:'Mínimo histórico', flag_store:'Mínimo en tienda',
    exp_today:'Vence hoy', exp_days:'Vence en {n}d', price_free:'GRATIS',
  };
  let s = FB[key] || key;
  if (vars) Object.keys(vars).forEach(k => { s = s.replace('{' + k + '}', vars[k]); });
  return s;
}

// ── Card HTML ────────────────────────────────────────
function badgeHTML(deal) {
  if (deal.price === 0)    return `<div class="badge badge--free">${tx('badge_free')}</div>`;
  if (deal.discount >= 70) return `<div class="badge badge--hot">${tx('badge_hot')}</div>`;
  return `<div class="badge badge--sale">-${deal.discount}%</div>`;
}

function flagHTML(deal) {
  if (!deal.flag) return '';
  const map = {
    N: { label: tx('flag_new'),   cls: 'flag--new'   },
    H: { label: tx('flag_hist'),  cls: 'flag--hist'  },
    S: { label: tx('flag_store'), cls: 'flag--store' },
  };
  const f = map[deal.flag];
  return f ? `<div class="flag-tag ${f.cls}">${f.label}</div>` : '';
}

function expiryHTML(deal) {
  if (!deal.expiry) return '';
  const diff = Math.ceil((new Date(deal.expiry) - Date.now()) / 86400000);
  if (diff < 0) return '';
  const cls  = diff === 0 ? 'expiry--urgent' : diff <= 2 ? 'expiry--soon' : 'expiry--ok';
  const text = diff === 0 ? tx('exp_today') : tx('exp_days', {n: diff});
  return `<span class="expiry-tag ${cls}">⏰ ${text}</span>`;
}

function voucherHTML(deal) {
  if (!deal.voucher) return '';
  return `<span class="voucher-chip" title="Código de cupón">🎟 ${escHtml(deal.voucher)}</span>`;
}

function cardHTML(deal) {
  const thumb = deal.thumb
    ? `<div class="card-thumb"><img src="${deal.thumb}" alt="${escHtml(deal.name)}" loading="lazy"/></div>`
    : `<div class="card-thumb card-thumb--empty"><span>🎮</span></div>`;

  const kebab = window.GD_USER_LOGGED_IN
    ? `<button class="card-kebab-btn" data-deal="${escHtml(deal.name)}" aria-label="Opciones">⋮</button>`
    : '';

  return `
    <a href="/game/${encodeURIComponent(deal.name)}"
       class="card ${deal.flag==='N'?'card--newlow':''} ${deal.discount>=70?'card--hot':''} ${deal.price===0?'card--free':''}">
      ${thumb}
      ${badgeHTML(deal)}
      ${flagHTML(deal)}
      ${kebab}
      <div class="card-body">
        <div class="card-store-row">
          <span class="card-store">${escHtml(deal.store)}</span>
        </div>
        <div class="card-name">${escHtml(deal.name)}</div>
      </div>
      <div class="card-pricing">
        <span class="price-original" data-usd="${deal.original_price}">${deal.currency} ${deal.original_price.toFixed(2)}</span>
        ${deal.price === 0
          ? `<span class="price-current price-free">${tx('price_free')}</span>`
          : `<span class="price-current" data-usd="${deal.price}">${deal.currency} ${deal.price.toFixed(2)}</span>`
        }
        <span class="discount-tag">-${deal.discount}%</span>
        ${expiryHTML(deal)}
        ${voucherHTML(deal)}
      </div>
    </a>`;
}

// ── Sort ─────────────────────────────────────────────
function applySort(deals) {
  const arr = [...deals];
  switch (sortBy) {
    case 'price_asc':  return arr.sort((a,b) => a.price - b.price);
    case 'price_desc': return arr.sort((a,b) => b.price - a.price);
    case 'alpha':      return arr.sort((a,b) => a.name.localeCompare(b.name));
    case 'alpha_desc': return arr.sort((a,b) => b.name.localeCompare(a.name));
    default:           return arr.sort((a,b) => b.discount - a.discount);
  }
}

// ── Daily deals (expiry ≤ 7 days) ────────────────────
function renderDailyDeals() {
  const section = document.getElementById('daily-deals-section');
  if (!section) return;

  const now      = Date.now();
  const sevenDay = 7 * 24 * 60 * 60 * 1000;

  const urgent = ALL_DEALS
    .filter(d => {
      if (!d.expiry) return false;
      if (window.HIDDEN_NAMES && window.HIDDEN_NAMES.has(d.name)) return false;
      const ms = new Date(d.expiry) - now;
      return ms > 0 && ms <= sevenDay;
    })
    .sort((a, b) => new Date(a.expiry) - new Date(b.expiry))
    .slice(0, 12);

  if (urgent.length === 0) { section.style.display = 'none'; return; }
  section.style.display = '';
  document.getElementById('daily-deals-grid').innerHTML = urgent.map(cardHTML).join('');
  document.dispatchEvent(new CustomEvent('deals:rendered'));
}

// ── Filter & Render ───────────────────────────────────
function applyFilters() {
  let filtered = [...ALL_DEALS];

  if (window.HIDDEN_NAMES && window.HIDDEN_NAMES.size > 0) {
    filtered = filtered.filter(d => !window.HIDDEN_NAMES.has(d.name));
  }

  if (query) {
    const q = query.toLowerCase();
    filtered = filtered.filter(d => d.name.toLowerCase().includes(q));
  }
  if (storeId !== 'All') {
    filtered = filtered.filter(d => d.store_id === storeId);
  }
  if (maxPrice !== null && !isNaN(maxPrice)) {
    filtered = filtered.filter(d => d.price <= maxPrice);
  }

  filtered = applySort(filtered);
  statVisible.textContent = filtered.length;

  if (filtered.length === 0) {
    grid.innerHTML = '';
    emptyState.style.display = 'flex';
  } else {
    emptyState.style.display = 'none';
    grid.innerHTML = filtered.map(cardHTML).join('');
    document.dispatchEvent(new CustomEvent('deals:rendered'));
  }
}

// ── Autocomplete ─────────────────────────────────────
function showSuggestions(val) {
  if (!val || val.length < 2) { suggestions.classList.remove('active'); return; }
  const q = val.toLowerCase();
  const matches = ALL_DEALS.filter(d => d.name.toLowerCase().includes(q)).slice(0, 8);

  if (matches.length === 0) { suggestions.classList.remove('active'); return; }

  suggestions.innerHTML = matches.map(d => {
    const idx    = d.name.toLowerCase().indexOf(q);
    const before = escHtml(d.name.slice(0, idx));
    const match  = escHtml(d.name.slice(idx, idx + val.length));
    const after  = escHtml(d.name.slice(idx + val.length));
    return `<div class="suggestion-item" data-name="${escHtml(d.name)}">
      ${before}<strong>${match}</strong>${after}
      <span class="suggestion-store">${escHtml(d.store)}</span>
    </div>`;
  }).join('');
  suggestions.classList.add('active');
}

suggestions.addEventListener('click', e => {
  const item = e.target.closest('.suggestion-item');
  if (!item) return;
  searchInput.value = item.dataset.name;
  query = item.dataset.name;
  suggestions.classList.remove('active');
  applyFilters();
});

document.addEventListener('click', e => {
  if (!e.target.closest('.search-wrapper')) suggestions.classList.remove('active');
});

// ── Event Listeners ───────────────────────────────────
searchInput.addEventListener('input', () => {
  query = searchInput.value.trim();
  searchClear.style.display = query ? 'flex' : 'none';
  showSuggestions(searchInput.value);
  applyFilters();
});

searchInput.addEventListener('keydown', e => {
  if (e.key === 'Escape') suggestions.classList.remove('active');
  if (e.key === 'Enter')  { suggestions.classList.remove('active'); applyFilters(); }
});

searchClear.addEventListener('click', () => {
  searchInput.value = '';
  query = '';
  searchClear.style.display = 'none';
  suggestions.classList.remove('active');
  applyFilters();
});

storeFilter.addEventListener('change', () => { storeId = storeFilter.value; applyFilters(); });
priceFilter.addEventListener('input',  () => { maxPrice = parseFloat(priceFilter.value) || null; applyFilters(); });
sortFilter.addEventListener('change',  () => { sortBy = sortFilter.value; applyFilters(); });

function resetAll() {
  searchInput.value = '';
  priceFilter.value = '';
  storeFilter.value = 'All';
  sortFilter.value  = 'discount';
  query = ''; storeId = 'All'; maxPrice = null; sortBy = 'discount';
  searchClear.style.display = 'none';
  suggestions.classList.remove('active');
  applyFilters();
}

btnReset.addEventListener('click', resetAll);
btnReset2.addEventListener('click', resetAll);

// ── Init ──────────────────────────────────────────────
searchClear.style.display = 'none';
applyFilters();
renderDailyDeals();

document.addEventListener('lang:changed', function () {
  renderDailyDeals();
  applyFilters();
});

// ── Kebab / deal menu ─────────────────────────────────
(function () {
  if (!window.GD_USER_LOGGED_IN) return;

  // Single shared panel appended to <body> (avoids card overflow clipping)
  const panel = document.createElement('div');
  panel.className = 'ckd-panel';
  panel.innerHTML = `
    <button class="ckd-item" id="ckd-wishlist">
      <span class="ckd-icon" id="ckd-wl-icon">🤍</span>
      <span id="ckd-wl-label">Guardar en deseados</span>
    </button>
    <button class="ckd-item" id="ckd-go">
      <span class="ckd-icon">🛒</span> Ir a la oferta
    </button>
    <button class="ckd-item" id="ckd-hide">
      <span class="ckd-icon">🚫</span> No me interesa
    </button>`;
  document.body.appendChild(panel);

  let activeDeal = null;
  let activeBtn  = null;

  function openPanel(btn, deal) {
    activeDeal = deal;
    activeBtn  = btn;
    const inWl = window.WISHLIST_NAMES && window.WISHLIST_NAMES.has(deal.name);
    document.getElementById('ckd-wl-icon').textContent  = inWl ? '❤️' : '🤍';
    document.getElementById('ckd-wl-label').textContent = inWl ? 'En deseados' : 'Guardar en deseados';

    const r = btn.getBoundingClientRect();
    panel.style.top   = (r.bottom + window.scrollY + 6) + 'px';
    // Align right edge of panel with right edge of button, but clamp to viewport
    const left = Math.min(
      r.right + window.scrollX - 190,
      window.innerWidth + window.scrollX - 196,
    );
    panel.style.left = Math.max(4, left) + 'px';
    panel.classList.add('ckd--open');
  }

  function closePanel() {
    panel.classList.remove('ckd--open');
    activeDeal = null;
    activeBtn  = null;
  }

  // Wishlist toggle
  document.getElementById('ckd-wishlist').addEventListener('click', function () {
    if (!activeDeal) return;
    const deal = activeDeal;
    closePanel();
    fetch('/api/wishlist/toggle', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(deal),
    })
      .then(r => r.json())
      .then(data => {
        if (!window.WISHLIST_NAMES) window.WISHLIST_NAMES = new Set();
        if (data.in_wishlist) {
          window.WISHLIST_NAMES.add(deal.name);
        } else {
          window.WISHLIST_NAMES.delete(deal.name);
        }
        // Update sidebar count
        const sb = document.getElementById('wl-sidebar-count');
        if (sb) {
          const n = window.WISHLIST_NAMES.size;
          sb.textContent   = n;
          sb.style.display = n > 0 ? '' : 'none';
        }
        // Refresh card to show updated heart
        applyFilters();
        renderDailyDeals();
      })
      .catch(() => {});
  });

  // Go to deal
  document.getElementById('ckd-go').addEventListener('click', function () {
    if (!activeDeal) return;
    const url = activeDeal.url;
    closePanel();
    window.open(url, '_blank', 'noopener');
  });

  // Hide for 1 hour
  document.getElementById('ckd-hide').addEventListener('click', function () {
    if (!activeDeal) return;
    const name = activeDeal.name;
    closePanel();
    fetch('/api/deals/hide', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name }),
    }).catch(() => {});
    if (!window.HIDDEN_NAMES) window.HIDDEN_NAMES = new Set();
    window.HIDDEN_NAMES.add(name);
    applyFilters();
    renderDailyDeals();
  });

  // Open panel on kebab click (delegated)
  document.addEventListener('click', function (e) {
    const btn = e.target.closest('.card-kebab-btn');
    if (btn) {
      e.preventDefault();
      e.stopPropagation();
      const name = btn.dataset.deal;
      const deal = (typeof ALL_DEALS !== 'undefined')
        ? ALL_DEALS.find(d => d.name === name)
        : null;
      if (!deal) return;
      if (panel.classList.contains('ckd--open') && activeBtn === btn) {
        closePanel();
      } else {
        openPanel(btn, deal);
      }
      return;
    }
    if (!panel.contains(e.target)) closePanel();
  });

  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') closePanel();
  });
  document.addEventListener('scroll', closePanel, { passive: true });
})();

// ── Analytics tracking ────────────────────────────────
(function () {
  // Search tracking: debounced, sent after 1.5s idle
  let searchTimer = null;
  searchInput.addEventListener('input', () => {
    clearTimeout(searchTimer);
    const q = searchInput.value.trim();
    if (q.length < 2) return;
    searchTimer = setTimeout(() => {
      fetch('/api/log/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: q }),
      }).catch(() => {});
    }, 1500);
  });

  // Click tracking: intercept card clicks before navigation
  document.addEventListener('click', function (e) {
    const card = e.target.closest('a.card');
    if (!card) return;
    const nameEl  = card.querySelector('.card-name');
    const storeEl = card.querySelector('.card-store');
    if (!nameEl) return;
    fetch('/api/log/click', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name:  nameEl.textContent.trim(),
        store: storeEl ? storeEl.textContent.trim() : '',
      }),
    }).catch(() => {});
  });
})();

// ── Carousel ──────────────────────────────────────────
(function () {
  const track = document.getElementById('carousel-track');
  if (!track) return;
  const slides = track.children;
  const total  = slides.length;
  if (total === 0) return;

  const dots    = document.querySelectorAll('.carousel-dot');
  const carousel = document.getElementById('carousel');
  let current   = 0;
  let timer     = null;

  function goTo(idx) {
    current = (idx + total) % total;
    track.style.transform = `translateX(-${current * 100}%)`;
    dots.forEach((d, i) => d.classList.toggle('carousel-dot--active', i === current));
  }

  function startAuto() {
    clearInterval(timer);
    timer = setInterval(() => goTo(current + 1), 5000);
  }

  document.getElementById('carousel-next')
    ?.addEventListener('click', () => { goTo(current + 1); startAuto(); });
  document.getElementById('carousel-prev')
    ?.addEventListener('click', () => { goTo(current - 1); startAuto(); });

  dots.forEach((d, i) => d.addEventListener('click', () => { goTo(i); startAuto(); }));

  carousel.addEventListener('mouseenter', () => clearInterval(timer));
  carousel.addEventListener('mouseleave', startAuto);

  let touchX = 0;
  carousel.addEventListener('touchstart', e => { touchX = e.touches[0].clientX; }, { passive: true });
  carousel.addEventListener('touchend', e => {
    const dx = e.changedTouches[0].clientX - touchX;
    if (Math.abs(dx) > 40) { dx < 0 ? goTo(current + 1) : goTo(current - 1); startAuto(); }
  });

  startAuto();
})();
