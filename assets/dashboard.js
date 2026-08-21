// assets/dashboard.js
'use strict';

const THRESHOLDS = {
  cancellation_alert_pct: 5,  // computed cancellation > 5% is flagged
  kpt_p80_max_minutes: 10,    // computed KPT P80 > 10 min is flagged
  min_online_opd: 3,          // online orders/day < 3 is flagged (new stores ramp up)
};

const GOOD = {
  revPerDay: 5000,
  ordersPerDay: 20,
  cancellationPct: 3,
  kptP80Minutes: 10,
  rating: 4.5,
  ratingMin: 4.0,
};

const ALERT_SEVERITY = {
  zero_revenue: 'crit',
  cancellation_high: 'crit',
  kpt_high: 'warn',
  low_online_opd: 'warn',
};

// ---------- date helpers ----------

function shiftDateStr(dateStr, days) {
  const d = new Date(dateStr + 'T00:00:00Z');
  d.setUTCDate(d.getUTCDate() + days);
  return d.toISOString().slice(0, 10);
}

function allDatesAcross(stores) {
  const set = new Set();
  for (const s of stores) for (const d of s.revenue.daily) set.add(d.date);
  return Array.from(set).sort();
}

function latestCompleteDate(stores) {
  const dates = allDatesAcross(stores);
  return dates.length ? dates[dates.length - 1] : null;
}

// ---------- formatting ----------

function fmtMoney(n) {
  return '₹' + Math.round(n).toLocaleString('en-IN');
}

function fmtMoneyCompact(n) {
  const sign = n < 0 ? '-' : '';
  n = Math.abs(n);
  if (n >= 100000) return sign + '₹' + (n / 100000).toFixed(1) + 'L';
  if (n >= 1000) return sign + '₹' + (n / 1000).toFixed(1) + 'k';
  return sign + '₹' + Math.round(n);
}

const MONTH_ABBR = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

function fmtDateLabel(dateStr) {
  if (!dateStr) return '';
  const [y, m, d] = dateStr.split('-').map(Number);
  return `${d} ${MONTH_ABBR[m - 1]} ${y}`;
}

function wowLabel(curr, prior) {
  if (!prior || prior <= 0) return curr > 0 ? 'new vs last week' : null;
  const pct = ((curr - prior) / prior) * 100;
  const arrow = pct >= 0 ? '▲' : '▼';
  return { text: `${arrow} ${Math.abs(pct).toFixed(0)}% vs last week`, dir: pct >= 0 ? 'up' : 'down' };
}

function severityByStore(alerts) {
  const map = {};
  for (const a of alerts) {
    const sev = ALERT_SEVERITY[a.type] || 'warn';
    if (!map[a.store] || (map[a.store] === 'warn' && sev === 'crit')) map[a.store] = sev;
  }
  return map;
}

function metricChipClass(value, kind) {
  if (value === null || value === undefined) return 'na';
  if (kind === 'maxCancel') return value <= GOOD.cancellationPct ? 'good' : value <= 8 ? 'warn' : 'crit';
  if (kind === 'minRevPerDay') return value >= GOOD.revPerDay ? 'good' : 'na';
  if (kind === 'minOrdersPerDay') return value >= GOOD.ordersPerDay ? 'good' : 'na';
  if (kind === 'maxKpt') return value <= GOOD.kptP80Minutes ? 'good' : value <= 15 ? 'warn' : 'crit';
  if (kind === 'rating') return value >= GOOD.rating ? 'good' : value >= GOOD.ratingMin ? 'warn' : 'crit';
  return 'na';
}

function pendingChip() {
  const span = document.createElement('span');
  span.className = 'metric-chip na';
  span.textContent = 'Not yet rated';
  return span;
}

function ratingChipCell(cell, ratingEntry) {
  if (!ratingEntry || ratingEntry.rating === null || ratingEntry.rating === undefined) {
    cell.appendChild(pendingChip());
    return;
  }
  const countLabel = ratingEntry.count === null || ratingEntry.count === undefined ? '' : ` (${ratingEntry.count})`;
  cell.appendChild(scaledChip(`${ratingEntry.rating.toFixed(1)}★${countLabel}`, ratingEntry.rating, 'rating'));
}

function scaledChip(displayText, rawValue, kind) {
  const span = document.createElement('span');
  span.className = 'metric-chip ' + metricChipClass(rawValue, kind);
  span.textContent = displayText;
  return span;
}

function metricChip(value, kind, suffix) {
  const span = document.createElement('span');
  span.className = 'metric-chip ' + metricChipClass(value, kind);
  span.textContent = value === null || value === undefined ? '—' : `${value}${suffix || ''}`;
  return span;
}

function launchBandLabel(days) {
  if (days <= 7) return 'Week 1';
  if (days <= 30) return 'Day 8–30';
  if (days <= 60) return 'Day 31–60';
  return 'Day 61–90';
}

// ---------- sparkline (inline SVG, built via DOM — no innerHTML) ----------

function renderSparkline(container, values) {
  const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  svg.setAttribute('viewBox', '0 0 100 24');
  svg.setAttribute('class', 'spark');
  svg.setAttribute('width', '100%');
  svg.setAttribute('height', '28');
  svg.setAttribute('preserveAspectRatio', 'none');
  if (values.length >= 2) {
    const max = Math.max(...values);
    const min = Math.min(...values);
    const range = max - min || 1;
    const stepX = 96 / (values.length - 1);
    const pts = values.map((v, i) => {
      const x = 2 + i * stepX;
      const y = 2 + 20 * (1 - (v - min) / range);
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    }).join(' ');
    const poly = document.createElementNS('http://www.w3.org/2000/svg', 'polyline');
    poly.setAttribute('points', pts);
    poly.setAttribute('fill', 'none');
    poly.setAttribute('stroke', '#0a6b3f');
    poly.setAttribute('stroke-width', '2');
    poly.setAttribute('stroke-linecap', 'round');
    poly.setAttribute('stroke-linejoin', 'round');
    svg.appendChild(poly);
  }
  container.appendChild(svg);
}

// ---------- header ----------

function renderHeader(dashboard) {
  document.getElementById('generated-at').textContent =
    `Data as of ${dashboard.generated_at_ist} · trailing ${dashboard.window_days}-day window`;
  const ratingsAsOf = dashboard.stores.length ? dashboard.stores[0].ratings.as_of : null;
  document.getElementById('ratings-as-of').textContent =
    ratingsAsOf ? `Storefront ratings are a one-time snapshot as of ${fmtDateLabel(ratingsAsOf)}, not live.` : '';
}

// ---------- store picker ----------

function getSelectedStore(stores) {
  const raw = new URLSearchParams(location.search).get('store');
  if (!raw) return null;
  const decoded = decodeURIComponent(raw).trim().toLowerCase();
  return stores.find(s => s.display_name.toLowerCase() === decoded) || null;
}

function renderStorePicker(stores, selected) {
  const el = document.getElementById('store-picker-row');
  el.innerHTML = '';

  const label = document.createElement('label');
  label.textContent = selected ? 'Viewing:' : 'Find a store here →';
  label.setAttribute('for', 'store-picker');
  el.appendChild(label);

  const select = document.createElement('select');
  select.id = 'store-picker';
  const allOpt = document.createElement('option');
  allOpt.value = '';
  allOpt.textContent = `All ${stores.length} stores`;
  select.appendChild(allOpt);
  for (const s of stores) {
    const opt = document.createElement('option');
    opt.value = s.display_name;
    opt.textContent = `${s.display_name} (${s.city})`;
    if (selected && selected.display_name === s.display_name) opt.selected = true;
    select.appendChild(opt);
  }
  select.addEventListener('change', () => {
    location.href = select.value ? '?store=' + encodeURIComponent(select.value) : location.pathname;
  });
  el.appendChild(select);

  if (selected) {
    const back = document.createElement('a');
    back.className = 'back-link';
    back.href = location.pathname;
    back.textContent = '← All stores';
    el.appendChild(back);
    document.getElementById('page-title').textContent = `${selected.display_name} (${selected.city})`;
  }
}

// ---------- KPIs ----------

function sumAtDate(stores, dateStr) {
  let total = 0;
  for (const s of stores) {
    const entry = s.revenue.daily.find(d => d.date === dateStr);
    if (entry) total += entry.total;
  }
  return total;
}

function sumMtd(stores) {
  let total = 0, orders = 0;
  for (const s of stores) {
    total += s.revenue.mtd.total;
    orders += s.revenue.mtd.online_orders;
  }
  return { total, orders };
}

function computeFixedKpis(stores) {
  const yesterday = latestCompleteDate(stores);
  const priorWeek = yesterday ? shiftDateStr(yesterday, -7) : null;
  const yToday = yesterday ? sumAtDate(stores, yesterday) : 0;
  const yPrior = priorWeek ? sumAtDate(stores, priorWeek) : 0;
  const mtd = sumMtd(stores);
  const aov = mtd.orders > 0 ? mtd.total / mtd.orders : null;

  return { yesterday, yToday, yPrior, mtdTotal: mtd.total, aov, storeCount: stores.length };
}

function kpiCard() {
  const div = document.createElement('div');
  div.className = 'kpi';
  return div;
}

function addKpiText(div, className, text) {
  const el = document.createElement('div');
  el.className = className;
  el.textContent = text;
  div.appendChild(el);
  return el;
}

function renderKpis(k) {
  const banner = document.getElementById('kpi-date-banner');
  banner.textContent = k.yesterday ? `Figures for ${fmtDateLabel(k.yesterday)}` : '';

  const el = document.getElementById('kpis');
  el.innerHTML = '';

  const c1 = kpiCard();
  addKpiText(c1, 'label', 'Revenue');
  addKpiText(c1, 'value', fmtMoneyCompact(k.yToday));
  const wow = wowLabel(k.yToday, k.yPrior);
  if (wow) addKpiText(c1, 'sub' + (wow.dir ? ' ' + wow.dir : ''), wow.text || wow);
  el.appendChild(c1);

  const c2 = kpiCard();
  addKpiText(c2, 'label', 'Month to date');
  addKpiText(c2, 'value', fmtMoneyCompact(k.mtdTotal));
  el.appendChild(c2);

  const c3 = kpiCard();
  addKpiText(c3, 'label', 'AOV (MTD)');
  addKpiText(c3, 'value', k.aov !== null ? fmtMoney(k.aov) : '—');
  el.appendChild(c3);

  const c4 = kpiCard();
  addKpiText(c4, 'label', 'Stores in 90d window');
  addKpiText(c4, 'value', String(k.storeCount));
  el.appendChild(c4);
}

// ---------- alerts ----------

const ALERT_GROUP_LABELS = {
  zero_revenue: 'Zero Revenue',
  cancellation_high: 'Cancellations',
  kpt_high: 'Slow KPT',
  low_online_opd: 'Low Online Orders',
};

const ALERT_GROUP_ORDER = ['Zero Revenue', 'Cancellations', 'Slow KPT', 'Low Online Orders'];

function renderAlerts(alerts) {
  const el = document.getElementById('alerts-list');
  el.innerHTML = '';
  if (alerts.length === 0) {
    const li = document.createElement('li');
    li.className = 'alert-card ok';
    li.textContent = '✓ Nothing flagged in this view.';
    el.appendChild(li);
    return;
  }

  const groups = {};
  for (const a of alerts) {
    const label = ALERT_GROUP_LABELS[a.type] || 'Other';
    (groups[label] = groups[label] || []).push(a);
  }
  const orderedLabels = [
    ...ALERT_GROUP_ORDER.filter(l => groups[l]),
    ...Object.keys(groups).filter(l => !ALERT_GROUP_ORDER.includes(l)),
  ];

  for (const label of orderedLabels) {
    const groupAlerts = groups[label];
    const worstSev = groupAlerts.some(a => (ALERT_SEVERITY[a.type] || 'warn') === 'crit') ? 'crit' : 'warn';

    const groupLi = document.createElement('li');
    groupLi.className = 'alert-group' + (worstSev === 'warn' ? ' sev-warn' : '');

    const heading = document.createElement('div');
    heading.className = 'alert-group-heading';
    heading.textContent = `${label} (${groupAlerts.length})`;
    groupLi.appendChild(heading);

    const chipRow = document.createElement('div');
    chipRow.className = 'alert-chip-row';
    for (const a of groupAlerts) {
      const chip = document.createElement('span');
      chip.className = 'alert-chip';
      chip.textContent = a.value ? `${a.store} (${a.value})` : a.store;
      chipRow.appendChild(chip);
    }
    groupLi.appendChild(chipRow);
    el.appendChild(groupLi);
  }
}

// ---------- city filter (built dynamically — the city set changes as the window rolls) ----------

function renderCityFilterRow(stores, activeCity, onChange) {
  const el = document.getElementById('category-filter-row');
  el.innerHTML = '';

  const counts = {};
  for (const s of stores) counts[s.city] = (counts[s.city] || 0) + 1;
  const cities = Object.keys(counts).sort();

  const allBtn = document.createElement('button');
  allBtn.dataset.category = 'All';
  allBtn.textContent = `All · ${stores.length} stores`;
  if (activeCity === 'All') allBtn.classList.add('active');
  allBtn.addEventListener('click', () => onChange('All'));
  el.appendChild(allBtn);

  for (const city of cities) {
    const btn = document.createElement('button');
    btn.dataset.category = city;
    btn.textContent = `${city} · ${counts[city]}`;
    if (activeCity === city) btn.classList.add('active');
    btn.addEventListener('click', () => onChange(city));
    el.appendChild(btn);
  }
}

// ---------- store cards ----------

function dailyInRange(daily, start, end) {
  return daily.filter(d => d.date >= start && d.date <= end);
}

function renderStoreCards(stores, severityMap, range) {
  const el = document.getElementById('store-grid');
  el.innerHTML = '';
  if (stores.length === 0) {
    const note = document.createElement('div');
    note.className = 'empty-note';
    note.textContent = 'No stores in this filter.';
    el.appendChild(note);
    return;
  }
  for (const s of stores) {
    const daysInRange = range ? dailyInRange(s.revenue.daily, range.start, range.end) : s.revenue.daily;
    const last = daysInRange.length ? daysInRange[daysInRange.length - 1] : null;

    const card = document.createElement('div');
    card.className = 'store-card';

    const dot = document.createElement('div');
    const sev = severityMap[s.display_name];
    dot.className = 'status-dot' + (sev === 'crit' ? ' crit' : sev === 'warn' ? ' warn' : '');
    card.appendChild(dot);

    const name = document.createElement('div'); name.className = 'name'; name.textContent = s.display_name;
    card.appendChild(name);

    const cat = document.createElement('span'); cat.className = 'cat'; cat.textContent = s.city;
    card.appendChild(cat);
    const band = document.createElement('span'); band.className = 'band'; band.textContent = launchBandLabel(s.days_since_launch);
    card.appendChild(band);

    const revLabel = document.createElement('div'); revLabel.className = 'revenue-label';
    revLabel.textContent = 'Latest day';
    card.appendChild(revLabel);
    const rev = document.createElement('div'); rev.className = 'revenue';
    rev.textContent = last ? fmtMoney(last.total) : '—';
    card.appendChild(rev);

    const sparkWrap = document.createElement('div');
    const values = daysInRange.map(d => d.total);
    if (values.length >= 2) renderSparkline(sparkWrap, values);
    card.appendChild(sparkWrap);

    const meta = document.createElement('div'); meta.className = 'meta-row';
    const wtdSpan = document.createElement('span'); wtdSpan.textContent = `WTD ${fmtMoneyCompact(s.revenue.wtd.total)}`;
    const mtdSpan = document.createElement('span'); mtdSpan.textContent = `MTD ${fmtMoneyCompact(s.revenue.mtd.total)}`;
    meta.appendChild(wtdSpan);
    meta.appendChild(mtdSpan);
    card.appendChild(meta);

    const launch = document.createElement('div'); launch.className = 'meta-row';
    launch.style.borderTop = 'none'; launch.style.paddingTop = '0';
    launch.textContent = `Live since ${fmtDateLabel(s.launch_date)} (${s.days_since_launch}d)`;
    card.appendChild(launch);

    el.appendChild(card);
  }
}

// ---------- date range row ----------

function getDefaultRange(availableDates) {
  if (availableDates.length === 0) return { start: null, end: null };
  const end = availableDates[availableDates.length - 1];
  const startIdx = Math.max(0, availableDates.length - 7);
  return { start: availableDates[startIdx], end };
}

function getRangeFromUrl(availableDates) {
  const params = new URLSearchParams(location.search);
  const start = params.get('start');
  const end = params.get('end');
  if (start && end) return { start, end };
  return getDefaultRange(availableDates);
}

function renderDateRangeRow(availableDates, range, onChange) {
  const el = document.getElementById('date-range-row');
  el.innerHTML = '';
  if (availableDates.length === 0) return;
  const min = availableDates[0];
  const max = availableDates[availableDates.length - 1];

  const startLabel = document.createElement('label');
  startLabel.textContent = 'From';
  const startInput = document.createElement('input');
  startInput.type = 'date'; startInput.min = min; startInput.max = max; startInput.value = range.start;
  startLabel.appendChild(startInput);

  const endLabel = document.createElement('label');
  endLabel.textContent = 'To';
  const endInput = document.createElement('input');
  endInput.type = 'date'; endInput.min = min; endInput.max = max; endInput.value = range.end;
  endLabel.appendChild(endInput);

  const apply = () => {
    if (startInput.value && endInput.value && startInput.value <= endInput.value) {
      const params = new URLSearchParams(location.search);
      params.set('start', startInput.value);
      params.set('end', endInput.value);
      history.replaceState(null, '', '?' + params.toString());
      onChange({ start: startInput.value, end: endInput.value });
    }
  };
  startInput.addEventListener('change', apply);
  endInput.addEventListener('change', apply);

  const presets = document.createElement('div');
  presets.className = 'presets';
  const presetDefs = [
    { label: 'Yesterday', yesterday: true },
    { label: '7 Days', days: 7 },
    { label: '30 Days', days: 30 },
    { label: 'MTD', mtd: true },
    { label: '90 Days', all: true },
  ];
  for (const p of presetDefs) {
    const btn = document.createElement('button');
    btn.textContent = p.label;
    btn.addEventListener('click', () => {
      let start;
      if (p.yesterday) start = max;
      else if (p.all) start = min;
      else if (p.mtd) start = max.slice(0, 8) + '01';
      else start = availableDates[Math.max(0, availableDates.length - p.days)];
      startInput.value = start < min ? min : start;
      endInput.value = max;
      apply();
    });
    presets.appendChild(btn);
  }

  el.appendChild(startLabel);
  el.appendChild(endLabel);
  el.appendChild(presets);
  const note = document.createElement('span');
  note.className = 'range-note';
  note.textContent = 'drives the two tables below';
  el.appendChild(note);
}

// ---------- generic sortable table ----------

function renderSortableTable(tableId, columns, rows, sortState) {
  const table = document.getElementById(tableId);
  const thead = table.querySelector('thead');
  const tbody = table.querySelector('tbody');
  thead.innerHTML = ''; tbody.innerHTML = '';

  const headRow = document.createElement('tr');
  columns.forEach((col, i) => {
    const el = document.createElement('th');
    el.style.cursor = 'pointer';
    el.textContent = col.label + (sortState.col === i ? (sortState.dir === 1 ? ' ▲' : ' ▼') : '');
    el.addEventListener('click', () => {
      if (sortState.col === i) sortState.dir *= -1;
      else { sortState.col = i; sortState.dir = 1; }
      renderSortableTable(tableId, columns, rows, sortState);
    });
    headRow.appendChild(el);
  });
  thead.appendChild(headRow);

  let sortedRows = rows;
  if (sortState.col !== null) {
    const col = columns[sortState.col];
    sortedRows = [...rows].sort((a, b) => {
      const av = col.value(a), bv = col.value(b);
      const aNull = av === null || av === undefined;
      const bNull = bv === null || bv === undefined;
      if (aNull && bNull) return 0;
      if (aNull) return 1;
      if (bNull) return -1;
      if (typeof av === 'string') return av.localeCompare(bv) * sortState.dir;
      return (av - bv) * sortState.dir;
    });
  }

  for (const row of sortedRows) {
    const tr = document.createElement('tr');
    for (const col of columns) {
      const cell = document.createElement('td');
      if (col.numeric) cell.classList.add('num');
      if (col.storeCell) cell.classList.add('store-cell');
      if (col.render) col.render(cell, row);
      else cell.textContent = col.display(row);
      tr.appendChild(cell);
    }
    tbody.appendChild(tr);
  }
}

// ---------- Table 1: revenue / orders detail ----------

function sumDailyInRange(daily, start, end) {
  let onlineRevenue = 0, offlineRevenue = 0, onlineOrders = 0, offlineOrders = 0, days = 0;
  let swiggyRevenue = 0, zomatoRevenue = 0, swiggyOrders = 0, zomatoOrders = 0;
  for (const d of daily) {
    if (d.date >= start && d.date <= end) {
      onlineRevenue += Object.values(d.online).reduce((a, b) => a + b, 0);
      offlineRevenue += d.dine_in;
      onlineOrders += d.online_orders;
      offlineOrders += d.dine_in_orders;
      swiggyRevenue += d.online.swiggy;
      zomatoRevenue += d.online.zomato;
      swiggyOrders += d.orders_by_channel.swiggy;
      zomatoOrders += d.orders_by_channel.zomato;
      days++;
    }
  }
  return { onlineRevenue, offlineRevenue, onlineOrders, offlineOrders, swiggyRevenue, zomatoRevenue, swiggyOrders, zomatoOrders, days };
}

function fmtThousands(n) {
  return (n / 1000).toFixed(1);
}

function buildDetailRow(s, range) {
  const sums = sumDailyInRange(s.revenue.daily, range.start, range.end);
  const perDay = (total) => (sums.days > 0 ? total / sums.days : null);
  return {
    city: s.city,
    store: s.display_name,
    launchDate: s.launch_date,
    daysSinceLaunch: s.days_since_launch,
    opd: perDay(sums.onlineOrders + sums.offlineOrders),
    revPerDay: perDay(sums.onlineRevenue + sums.offlineRevenue),
    offOpd: perDay(sums.offlineOrders),
    offRevPerDay: perDay(sums.offlineRevenue),
    onOpd: perDay(sums.onlineOrders),
    onRevPerDay: perDay(sums.onlineRevenue),
    swiggyOpd: perDay(sums.swiggyOrders),
    zomatoOpd: perDay(sums.zomatoOrders),
  };
}

function opdCell(cell, value) {
  if (value === null) { cell.textContent = '—'; return; }
  cell.appendChild(scaledChip(value.toFixed(1), value, 'minOrdersPerDay'));
}

function revPerDayCell(cell, value) {
  if (value === null) { cell.textContent = '—'; return; }
  cell.appendChild(scaledChip(fmtThousands(value), value, 'minRevPerDay'));
}

const DETAIL_COLUMNS = [
  { label: 'City', value: r => r.city, display: r => r.city },
  { label: 'Store', value: r => r.store, display: r => r.store, storeCell: true },
  { label: 'Live Since', value: r => r.launchDate, display: r => fmtDateLabel(r.launchDate) },
  { label: 'Days Live', value: r => r.daysSinceLaunch, numeric: true, display: r => String(r.daysSinceLaunch) },
  { label: 'OPD', value: r => r.opd, numeric: true, render: (cell, r) => opdCell(cell, r.opd) },
  { label: 'Rev/day (k)', value: r => r.revPerDay, numeric: true, render: (cell, r) => revPerDayCell(cell, r.revPerDay) },
  { label: 'Off-OPD', value: r => r.offOpd, numeric: true, render: (cell, r) => opdCell(cell, r.offOpd) },
  { label: 'Off-Rev/day (k)', value: r => r.offRevPerDay, numeric: true, render: (cell, r) => revPerDayCell(cell, r.offRevPerDay) },
  { label: 'On-OPD', value: r => r.onOpd, numeric: true, render: (cell, r) => opdCell(cell, r.onOpd) },
  { label: 'On-Rev/day (k)', value: r => r.onRevPerDay, numeric: true, render: (cell, r) => revPerDayCell(cell, r.onRevPerDay) },
  { label: 'S-OPD', value: r => r.swiggyOpd, numeric: true, render: (cell, r) => opdCell(cell, r.swiggyOpd) },
  { label: 'Z-OPD', value: r => r.zomatoOpd, numeric: true, render: (cell, r) => opdCell(cell, r.zomatoOpd) },
];

const detailSortState = { col: 3, dir: 1 };

function renderDetailTable(stores, range) {
  const rows = stores.map(s => buildDetailRow(s, range));
  renderSortableTable('detail-table', DETAIL_COLUMNS, rows, detailSortState);
}

// ---------- Table 2: cancellation / KPT ----------

function opsComputedInRange(opsComputedDaily, start, end) {
  let orders = 0, cancelled = 0, kptWeightedSum = 0, kptWeight = 0;
  for (const d of opsComputedDaily) {
    if (d.date >= start && d.date <= end) {
      orders += d.order_count;
      cancelled += d.cancelled_orders;
      if (d.kpt_p80_minutes !== null) { kptWeightedSum += d.kpt_p80_minutes * d.order_count; kptWeight += d.order_count; }
    }
  }
  return {
    cancellationPct: orders > 0 ? (cancelled / orders) * 100 : null,
    kptP80Minutes: kptWeight > 0 ? kptWeightedSum / kptWeight : null,
  };
}

function buildHealthRow(s, range) {
  const computed = opsComputedInRange(s.ops_computed.daily, range.start, range.end);
  return {
    city: s.city,
    store: s.display_name,
    launchDate: s.launch_date,
    cancellationPct: computed.cancellationPct,
    kptP80Minutes: computed.kptP80Minutes,
    swiggyRating: s.ratings.swiggy,
    zomatoRating: s.ratings.zomato,
    googleRating: s.ratings.google,
  };
}

const HEALTH_COLUMNS = [
  { label: 'City', value: r => r.city, display: r => r.city },
  { label: 'Store', value: r => r.store, display: r => r.store, storeCell: true },
  { label: 'Live Since', value: r => r.launchDate, display: r => fmtDateLabel(r.launchDate) },
  {
    label: 'Cancellation %', value: r => r.cancellationPct, numeric: true,
    render: (cell, r) => cell.appendChild(metricChip(r.cancellationPct !== null ? r.cancellationPct.toFixed(1) : null, 'maxCancel', r.cancellationPct !== null ? '%' : '')),
  },
  {
    label: 'KPT P80 (min)', value: r => r.kptP80Minutes, numeric: true,
    render: (cell, r) => cell.appendChild(metricChip(r.kptP80Minutes !== null ? r.kptP80Minutes.toFixed(1) : null, 'maxKpt')),
  },
  {
    label: 'Swiggy Storefront', value: r => r.swiggyRating.rating, numeric: true,
    render: (cell, r) => ratingChipCell(cell, r.swiggyRating),
  },
  {
    label: 'Zomato Storefront', value: r => r.zomatoRating.rating, numeric: true,
    render: (cell, r) => ratingChipCell(cell, r.zomatoRating),
  },
  {
    label: 'Google Storefront', value: r => r.googleRating.rating, numeric: true,
    render: (cell, r) => ratingChipCell(cell, r.googleRating),
  },
];

const healthSortState = { col: null, dir: 1 };

function renderHealthTable(stores, range) {
  const rows = stores.map(s => buildHealthRow(s, range));
  renderSortableTable('health-table', HEALTH_COLUMNS, rows, healthSortState);
}

// ---------- boot ----------

async function loadData() {
  const dashboard = await fetch('data.json').then(r => r.json());
  return { dashboard };
}

function renderAll({ dashboard }) {
  const selected = getSelectedStore(dashboard.stores);
  const baseStores = selected ? [selected] : dashboard.stores;
  const today = latestCompleteDate(dashboard.stores) || dashboard.generated_at_ist.slice(0, 10);
  const allAlerts = window.Alerts.computeAlerts(dashboard.stores, THRESHOLDS, today);
  const severityMap = severityByStore(allAlerts);
  const scopedAlerts = selected ? allAlerts.filter(a => a.store === selected.display_name) : allAlerts;

  renderHeader(dashboard);
  renderStorePicker(dashboard.stores, selected);
  renderKpis(computeFixedKpis(baseStores));
  renderAlerts(scopedAlerts);

  const cityFilterEl = document.getElementById('category-filter-row');
  cityFilterEl.style.display = selected ? 'none' : '';

  const availableDates = allDatesAcross(dashboard.stores);

  let currentRange = getRangeFromUrl(availableDates);
  if (!currentRange.start) currentRange = getDefaultRange(availableDates);
  let activeCity = 'All';

  const applyFilters = () => {
    const filtered = window.Alerts.filterByCity(baseStores, activeCity);
    renderStoreCards(filtered, severityMap, currentRange);
    renderDetailTable(filtered, currentRange);
    renderHealthTable(filtered, currentRange);
  };

  const handleCityChange = (city) => {
    activeCity = city;
    renderCityFilterRow(baseStores, activeCity, handleCityChange);
    applyFilters();
  };
  if (!selected) {
    renderCityFilterRow(baseStores, activeCity, handleCityChange);
  }

  renderDateRangeRow(availableDates, currentRange, (range) => {
    currentRange = range;
    applyFilters();
  });

  applyFilters();
}

loadData().then(renderAll).catch(err => {
  const el = document.getElementById('alerts-list');
  el.innerHTML = '';
  const li = document.createElement('li');
  li.className = 'alert-card';
  li.textContent = `Failed to load dashboard data: ${err.message}`;
  el.appendChild(li);
});
