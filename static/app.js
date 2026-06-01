// ── CSRF helper ─────────────────────────────────────
function getCsrfToken() {
  const meta = document.querySelector('meta[name="csrf-token"]');
  return meta ? meta.content : '';
}

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
let query          = '';
let storeId        = 'All';
let maxPrice       = null;
let sortBy         = 'discount';
let _rawgResults   = [];
let _filteredCache = [];
let _visibleCount  = 0;
const PAGE_SIZE    = 40;

// ── Toast notifications ──────────────────────────────
(function () {
  const container = document.createElement('div');
  container.id = 'toast-container';
  document.body.appendChild(container);
})();

function showToast(msg, type) {
  type = type || 'error';
  const t = document.createElement('div');
  t.className = 'toast toast--' + type;
  t.textContent = msg;
  document.getElementById('toast-container').appendChild(t);
  setTimeout(() => t.remove(), 3500);
}

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

function histLowHTML(deal) {
  if (!deal.history_low || deal.history_low <= 0) return '';
  const atLow = deal.price > 0 && deal.price <= deal.history_low;
  const near  = !atLow && deal.price > 0 && deal.price <= deal.history_low * 1.10;
  if (!atLow && !near) return '';
  const label = tx('hist_low_lbl');
  const fmt   = deal.currency + ' ' + deal.history_low.toFixed(2);
  const cls   = atLow ? 'hist-low--match' : 'hist-low--near';
  const icon  = atLow ? '🏆 ' : '≈ ';
  return `<span class="hist-low-tag ${cls}" title="${label}: ${fmt}">${icon}${label}</span>`;
}

function ownedHTML(deal) {
  if (!window.COLLECTION_NAMES || !window.COLLECTION_NAMES.has(deal.name)) return '';
  return `<div class="owned-overlay">${tx('col_owned_badge')}</div>`;
}

function cardHTML(deal) {
  const thumb = deal.thumb
    ? `<div class="card-thumb"><img src="${deal.thumb}" alt="${escHtml(deal.name)}" loading="lazy"
         onload="this.style.opacity=1"
         onerror="var p=this.parentElement;p.className='card-thumb card-thumb--empty';p.innerHTML='<span>🎮</span>';"/></div>`
    : `<div class="card-thumb card-thumb--empty"><span>🎮</span></div>`;

  const kebab = window.GD_USER_LOGGED_IN
    ? `<button class="card-kebab-btn" data-deal="${escHtml(deal.name)}" aria-label="Opciones">⋮</button>`
    : '';

  const owned = window.COLLECTION_NAMES && window.COLLECTION_NAMES.has(deal.name);
  return `
    <a href="/game/${encodeURIComponent(deal.name)}"
       class="card ${deal.flag==='N'?'card--newlow':''} ${deal.discount>=70?'card--hot':''} ${deal.price===0?'card--free':''} ${owned?'card--owned':''}">
      ${thumb}
      ${badgeHTML(deal)}
      ${flagHTML(deal)}
      ${ownedHTML(deal)}
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
        ${histLowHTML(deal)}
        ${expiryHTML(deal)}
        ${voucherHTML(deal)}
      </div>
    </a>`;
}

// ── Sort ─────────────────────────────────────────────
function applySort(deals) {
  const arr = [...deals];
  switch (sortBy) {
    case 'popular':    return arr.sort((a,b) => (b.popularity||0) - (a.popularity||0));
    case 'price_asc':  return arr.sort((a,b) => a.price - b.price);
    case 'price_desc': return arr.sort((a,b) => b.price - a.price);
    case 'alpha':      return arr.sort((a,b) => a.name.localeCompare(b.name));
    case 'alpha_desc': return arr.sort((a,b) => b.name.localeCompare(a.name));
    default:           return arr.sort((a,b) => b.discount - a.discount);
  }
}

function rawgCardHTML(game) {
  const thumb = game.thumb
    ? `<div class="card-thumb"><img src="${escHtml(game.thumb)}" alt="${escHtml(game.name)}" loading="lazy"
         onload="this.style.opacity=1"
         onerror="var p=this.parentElement;p.className='card-thumb card-thumb--empty';p.innerHTML='<span>🎮</span>';"/></div>`
    : `<div class="card-thumb card-thumb--empty"><span>🎮</span></div>`;
  return `
    <a href="/game/${encodeURIComponent(game.name)}" class="card card--explore">
      ${thumb}
      <div class="card-explore-badge">Explorar</div>
      <div class="card-body">
        <div class="card-store-row"><span class="card-store">RAWG</span></div>
        <div class="card-name">${escHtml(game.name)}</div>
      </div>
      <div class="card-pricing card-pricing--explore">
        <span class="card-explore-cta">Ver detalles →</span>
      </div>
    </a>`;
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
  requestAnimationFrame(() => {
    document.getElementById('daily-deals-grid').innerHTML = urgent.map(cardHTML).join('');
    document.dispatchEvent(new CustomEvent('deals:rendered'));
  });
}

// ── Filter & Render ───────────────────────────────────
const loadMoreWrap = document.getElementById('load-more-wrap');
const loadMoreBtn  = document.getElementById('load-more-btn');

function _updateLoadMoreBtn(total, rawgCount) {
  const hasMore = _visibleCount < total;
  if (loadMoreWrap) loadMoreWrap.style.display = hasMore ? 'block' : 'none';
  if (statVisible) {
    statVisible.textContent = hasMore
      ? Math.min(_visibleCount, total) + ' de ' + (total + rawgCount)
      : total + rawgCount;
  }
}

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

  // Append RAWG-only cards when searching (games not already in filtered deals)
  let extraRawg = [];
  if (query && _rawgResults.length > 0) {
    const filteredNames = new Set(filtered.map(d => d.name.toLowerCase()));
    extraRawg = _rawgResults.filter(g => !filteredNames.has(g.name.toLowerCase()));
  }

  if (filtered.length === 0 && extraRawg.length === 0) {
    requestAnimationFrame(() => {
      grid.innerHTML = '';
      emptyState.style.display = 'flex';
      if (loadMoreWrap) loadMoreWrap.style.display = 'none';
      if (statVisible) statVisible.textContent = '0';
    });
    return;
  }

  _filteredCache = filtered;
  _visibleCount  = PAGE_SIZE;

  requestAnimationFrame(() => {
    emptyState.style.display = 'none';
    grid.innerHTML = _filteredCache.slice(0, _visibleCount).map(cardHTML).join('')
                   + extraRawg.map(rawgCardHTML).join('');
    document.dispatchEvent(new CustomEvent('deals:rendered'));
    _updateLoadMoreBtn(_filteredCache.length, extraRawg.length);
  });
}

function loadMore() {
  const start = _visibleCount;
  _visibleCount += PAGE_SIZE;
  const next = _filteredCache.slice(start, _visibleCount).map(cardHTML).join('');
  if (next) {
    grid.insertAdjacentHTML('beforeend', next);
    document.dispatchEvent(new CustomEvent('deals:rendered'));
  }
  _updateLoadMoreBtn(_filteredCache.length, 0);
}

if (loadMoreBtn) loadMoreBtn.addEventListener('click', loadMore);

// ── Autocomplete ─────────────────────────────────────
// ── Search suggestions (local + remote) ──────────────
let _searchTimer = null;

function _highlightMatch(text, val) {
  const idx = text.toLowerCase().indexOf(val.toLowerCase());
  if (idx < 0) return escHtml(text);
  return escHtml(text.slice(0, idx))
       + '<strong>' + escHtml(text.slice(idx, idx + val.length)) + '</strong>'
       + escHtml(text.slice(idx + val.length));
}

function _renderSuggestions(deals, rawgGames, val) {
  if (deals.length === 0 && rawgGames.length === 0) {
    suggestions.classList.remove('active');
    return;
  }
  let html = '';
  if (deals.length > 0) {
    html += '<div class="sg-group-label">Ofertas activas</div>';
    html += deals.map(d =>
      `<div class="suggestion-item suggestion-item--deal" data-name="${escHtml(d.name)}">
        <span class="suggestion-name">${_highlightMatch(d.name, val)}</span>
        <span class="suggestion-store">${escHtml(d.store)}</span>
      </div>`
    ).join('');
  }
  if (rawgGames.length > 0) {
    html += '<div class="sg-group-label">Explorar juegos</div>';
    html += rawgGames.map(g =>
      `<div class="suggestion-item suggestion-item--rawg" data-url="/game/${encodeURIComponent(g.name)}">
        <span class="suggestion-name">${_highlightMatch(g.name, val)}</span>
        <span class="suggestion-badge">Ver detalles →</span>
      </div>`
    ).join('');
  }
  suggestions.innerHTML = html;
  suggestions.classList.add('active');
}

function showSuggestions(val) {
  if (!val || val.length < 2) { suggestions.classList.remove('active'); return; }
  const q = val.toLowerCase();

  // Instant local results
  const localDeals = ALL_DEALS.filter(d => d.name.toLowerCase().includes(q)).slice(0, 5);
  _renderSuggestions(localDeals, [], val);

  // Remote results after debounce
  clearTimeout(_searchTimer);
  _searchTimer = setTimeout(() => {
    fetch('/api/search?q=' + encodeURIComponent(val))
      .then(r => r.json())
      .then(data => {
        const localNames = new Set(localDeals.map(d => d.name.toLowerCase()));
        const remoteDeals = data
          .filter(r => r.type === 'deal' && !localNames.has(r.name.toLowerCase()))
          .slice(0, Math.max(0, 5 - localDeals.length));
        const rawgGames = data.filter(r => r.type === 'rawg').slice(0, 5);
        _rawgResults = rawgGames;
        _renderSuggestions([...localDeals, ...remoteDeals], rawgGames, val);
        applyFilters();
      })
      .catch(() => {});
  }, 350);
}

suggestions.addEventListener('click', e => {
  const item = e.target.closest('.suggestion-item');
  if (!item) return;
  if (item.dataset.url) {
    window.location.href = item.dataset.url;
  } else {
    searchInput.value = item.dataset.name;
    query = item.dataset.name;
    suggestions.classList.remove('active');
    applyFilters();
  }
});

document.addEventListener('click', e => {
  if (!e.target.closest('.search-wrapper')) suggestions.classList.remove('active');
});

// ── Event Listeners ───────────────────────────────────
let _filterTimer = null;
searchInput.addEventListener('input', () => {
  query = searchInput.value.trim();
  searchClear.style.display = query ? 'flex' : 'none';
  _rawgResults = [];
  showSuggestions(searchInput.value);
  clearTimeout(_filterTimer);
  _filterTimer = setTimeout(applyFilters, 150);
});

searchInput.addEventListener('keydown', e => {
  if (e.key === 'Escape') { suggestions.classList.remove('active'); return; }

  const items = suggestions.querySelectorAll('.suggestion-item');
  if (!items.length) {
    if (e.key === 'Enter') { suggestions.classList.remove('active'); applyFilters(); }
    return;
  }

  const active = suggestions.querySelector('.suggestion-item--focus');
  let idx = Array.from(items).indexOf(active);

  if (e.key === 'ArrowDown') {
    e.preventDefault();
    if (active) active.classList.remove('suggestion-item--focus');
    idx = (idx + 1) % items.length;
    items[idx].classList.add('suggestion-item--focus');
    items[idx].scrollIntoView({ block: 'nearest' });
  } else if (e.key === 'ArrowUp') {
    e.preventDefault();
    if (active) active.classList.remove('suggestion-item--focus');
    idx = idx <= 0 ? items.length - 1 : idx - 1;
    items[idx].classList.add('suggestion-item--focus');
    items[idx].scrollIntoView({ block: 'nearest' });
  } else if (e.key === 'Enter') {
    if (active) {
      e.preventDefault();
      if (active.dataset.url) {
        window.location.href = active.dataset.url;
      } else {
        searchInput.value = active.dataset.name;
        query = active.dataset.name;
        suggestions.classList.remove('active');
        applyFilters();
      }
    } else {
      suggestions.classList.remove('active');
      applyFilters();
    }
  }
});

searchClear.addEventListener('click', () => {
  searchInput.value = '';
  query = '';
  searchClear.style.display = 'none';
  suggestions.classList.remove('active');
  _rawgResults = [];
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
    <button class="ckd-item" id="ckd-own">
      <span class="ckd-icon" id="ckd-own-icon">🎮</span>
      <span id="ckd-own-label">Ya lo tengo</span>
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
    const inWl  = window.WISHLIST_NAMES    && window.WISHLIST_NAMES.has(deal.name);
    const inCol = window.COLLECTION_NAMES  && window.COLLECTION_NAMES.has(deal.name);
    document.getElementById('ckd-wl-icon').textContent  = inWl  ? '❤️' : '🤍';
    document.getElementById('ckd-wl-label').textContent = inWl  ? (window.GD_tx ? window.GD_tx('menu_in_wishlist') : 'En deseados') : (window.GD_tx ? window.GD_tx('menu_wishlist') : 'Guardar en deseados');
    document.getElementById('ckd-own-icon').textContent  = inCol ? '✅' : '🎮';
    document.getElementById('ckd-own-label').textContent = inCol ? (window.GD_tx ? window.GD_tx('menu_unown') : 'Quitar de mi colección') : (window.GD_tx ? window.GD_tx('menu_own') : 'Ya lo tengo');

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
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCsrfToken() },
      body: JSON.stringify(deal),
    })
      .then(r => { if (!r.ok) throw new Error(r.status); return r.json(); })
      .then(data => {
        if (typeof data.in_wishlist === 'undefined') throw new Error('bad response');
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
      .catch(() => showToast(window.GD_tx ? window.GD_tx('wl_err') : 'Error al actualizar la lista de deseados', 'error'));
  });

  // Collection toggle
  document.getElementById('ckd-own').addEventListener('click', function () {
    if (!activeDeal) return;
    const deal = activeDeal;
    closePanel();
    fetch('/api/collection/toggle', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCsrfToken() },
      body: JSON.stringify({ name: deal.name }),
    })
      .then(r => { if (!r.ok) throw new Error(r.status); return r.json(); })
      .then(data => {
        if (typeof data.in_collection === 'undefined') throw new Error('bad response');
        if (!window.COLLECTION_NAMES) window.COLLECTION_NAMES = new Set();
        if (data.in_collection) {
          window.COLLECTION_NAMES.add(deal.name);
        } else {
          window.COLLECTION_NAMES.delete(deal.name);
        }
        applyFilters();
        renderDailyDeals();
      })
      .catch(() => showToast(window.GD_tx ? window.GD_tx('col_err') : 'Error al actualizar la colección', 'error'));
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
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCsrfToken() },
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
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCsrfToken() },
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
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCsrfToken() },
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
  let current    = 0;
  let timer      = null;
  let _isHovering = false;

  function goTo(idx) {
    current = (idx + total) % total;
    track.style.transform = `translateX(-${current * 100}%)`;
    dots.forEach((d, i) => d.classList.toggle('carousel-dot--active', i === current));
  }

  function startAuto() {
    clearInterval(timer);
    if (_isHovering) return;
    timer = setInterval(() => goTo(current + 1), 5000);
  }

  document.getElementById('carousel-next')
    ?.addEventListener('click', () => { goTo(current + 1); startAuto(); });
  document.getElementById('carousel-prev')
    ?.addEventListener('click', () => { goTo(current - 1); startAuto(); });

  dots.forEach((d, i) => d.addEventListener('click', () => { goTo(i); startAuto(); }));

  carousel.addEventListener('mouseenter', () => { _isHovering = true; clearInterval(timer); });
  carousel.addEventListener('mouseleave', () => { _isHovering = false; startAuto(); });

  let touchX = 0;
  carousel.addEventListener('touchstart', e => { touchX = e.touches[0].clientX; }, { passive: true });
  carousel.addEventListener('touchend', e => {
    const dx = e.changedTouches[0].clientX - touchX;
    if (Math.abs(dx) > 40) { dx < 0 ? goTo(current + 1) : goTo(current - 1); startAuto(); }
  });

  startAuto();
})();
