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

// ── Card HTML ────────────────────────────────────────
function badgeHTML(deal) {
  if (deal.price === 0)    return `<div class="badge badge--free">🎁 GRATIS</div>`;
  if (deal.discount >= 70) return `<div class="badge badge--hot">🔥 OFERTA</div>`;
  return `<div class="badge badge--sale">-${deal.discount}%</div>`;
}

function flagHTML(deal) {
  if (!deal.flag) return '';
  const map = {
    N: { label: 'Nuevo mínimo',     cls: 'flag--new'   },
    H: { label: 'Mínimo histórico', cls: 'flag--hist'  },
    S: { label: 'Mínimo en tienda', cls: 'flag--store' },
  };
  const f = map[deal.flag];
  return f ? `<div class="flag-tag ${f.cls}">${f.label}</div>` : '';
}

function expiryHTML(deal) {
  if (!deal.expiry) return '';
  const diff = Math.ceil((new Date(deal.expiry) - Date.now()) / 86400000);
  if (diff < 0) return '';
  const cls  = diff === 0 ? 'expiry--urgent' : diff <= 2 ? 'expiry--soon' : 'expiry--ok';
  const text = diff === 0 ? 'Vence hoy' : `Vence en ${diff}d`;
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

  return `
    <a href="${deal.url}" target="_blank" rel="noopener"
       class="card ${deal.flag==='N'?'card--newlow':''} ${deal.discount>=70?'card--hot':''} ${deal.price===0?'card--free':''}">
      ${thumb}
      ${badgeHTML(deal)}
      ${flagHTML(deal)}
      <div class="card-body">
        <div class="card-store-row">
          <span class="card-store">${escHtml(deal.store)}</span>
        </div>
        <div class="card-name">${escHtml(deal.name)}</div>
      </div>
      <div class="card-pricing">
        <span class="price-original" data-usd="${deal.original_price}">${deal.currency} ${deal.original_price.toFixed(2)}</span>
        ${deal.price === 0
          ? `<span class="price-current price-free">GRATIS</span>`
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
