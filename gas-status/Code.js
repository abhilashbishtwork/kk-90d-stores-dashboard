// "New Store Status" launch checklist for Krispy Kreme stores. Served as a
// curefoods.in-only web app (Workspace blocks anonymous Apps Script, so the
// public GitHub Pages dashboard links/embeds this page instead of writing to
// the Sheet itself). Every change is appended to a Log tab with the editor.

const SHEET_ID = '1NGtk8SJjELTwfmV2pt-H50Zx2ml-k63sPlC_HY0blYk';
const TAB = 'Status';

const CHECK_FIELDS = [
  'fssai_ack', 'fssai_licence',
  'swiggy_fssai_pending', 'swiggy_request', 'swiggy_live',
  'zomato_fssai_pending', 'zomato_request', 'zomato_live',
  'ownly_fssai_pending', 'ownly_request', 'ownly_live',
  'zomato_district', 'swiggy_dineout', 'google_listing',
];
const META_FIELDS = ['key', 'store_name', 'city', 'type', 'source', 'launch_date', 'archived'];
const HEADERS = META_FIELDS.concat(CHECK_FIELDS, ['updated_at', 'updated_by']);
const DATA_JSON_URL = 'https://abhilashbishtwork.github.io/kk-90d-stores-dashboard/data.json';
const EDITABLE = CHECK_FIELDS.concat(['type', 'city', 'store_name', 'archived']);
const TYPES = ['Dine-in / Mall', 'Shop-in-shop (SB)', 'Delivery / Cloud Kitchen', 'Kiosk', 'Other'];

function sheet_() {
  const ss = SpreadsheetApp.openById(SHEET_ID);
  let sh = ss.getSheetByName(TAB);
  if (!sh) {
    sh = ss.insertSheet(TAB);
    sh.getRange(1, 1, 1, HEADERS.length).setValues([HEADERS]).setFontWeight('bold');
    sh.setFrozenRows(1);
    const def = ss.getSheetByName('Sheet1');
    if (def && ss.getSheets().length > 1) ss.deleteSheet(def);
  }
  return sh;
}

function readAll_(sh) {
  const values = sh.getDataRange().getValues();
  const head = values[0];
  return values.slice(1).filter(r => r[0] !== '').map(r => {
    const o = {};
    head.forEach((h, i) => { o[h] = r[i]; });
    CHECK_FIELDS.concat(['archived']).forEach(f => { o[f] = o[f] === true || o[f] === 'TRUE'; });
    if (o.launch_date instanceof Date) o.launch_date = Utilities.formatDate(o.launch_date, 'Asia/Kolkata', 'yyyy-MM-dd');
    if (o.updated_at instanceof Date) o.updated_at = o.updated_at.toISOString();
    return o;
  });
}

function clean_(v, max) {
  return String(v == null ? '' : v).replace(/[\u0000-\u001f]/g, '').trim().slice(0, max || 120);
}

function newRow_(o) {
  return HEADERS.map(h => {
    if (h === 'updated_at') return new Date();
    if (h === 'updated_by') return user_();
    if (CHECK_FIELDS.indexOf(h) >= 0 || h === 'archived') return false;
    return o[h] || '';
  });
}

function user_() {
  try { return Session.getActiveUser().getEmail() || ''; } catch (e) { return ''; }
}

function log_(key, field, value) {
  const ss = SpreadsheetApp.openById(SHEET_ID);
  let lg = ss.getSheetByName('Log');
  if (!lg) {
    lg = ss.insertSheet('Log');
    lg.appendRow(['at', 'by', 'key', 'field', 'value']);
    lg.setFrozenRows(1);
  }
  lg.appendRow([new Date(), user_(), key, field, String(value)]);
}

// Best guess from the aggregator/POS store name; editable in the UI.
function guessType_(name) {
  const n = ' ' + String(name).toLowerCase() + ' ';
  if (/\bpos\b/.test(n) || n.indexOf(' mall') >= 0) return 'Dine-in / Mall';
  if (n.indexOf(' kk sb ') >= 0) return 'Shop-in-shop (SB)';
  return 'Delivery / Cloud Kitchen';
}

// Adds any store the daily ClickHouse build detected as new (data.json) that
// the Sheet hasn't seen yet. Failure to reach data.json never blocks the page.
function syncAutoStores_(sh, rows) {
  let stores;
  try {
    const res = UrlFetchApp.fetch(DATA_JSON_URL, { muteHttpExceptions: true });
    if (res.getResponseCode() !== 200) return false;
    stores = JSON.parse(res.getContentText()).stores || [];
  } catch (e) {
    return false;
  }
  const keys = rows.map(r => String(r.key));
  const add = stores.filter(s => s.store_name && keys.indexOf(clean_(s.store_name)) < 0).map(s => newRow_({
    key: clean_(s.store_name),
    store_name: clean_(s.display_name || s.store_name),
    city: clean_(s.city, 60),
    type: guessType_(s.store_name),
    source: 'auto',
    launch_date: clean_(s.launch_date, 10),
  }));
  if (add.length) sh.getRange(sh.getLastRow() + 1, 1, add.length, HEADERS.length).setValues(add);
  return true;
}

function state_(sh, synced) {
  return { types: TYPES, fields: CHECK_FIELDS, rows: readAll_(sh), synced: synced, me: user_() };
}

function doGet() {
  return HtmlService.createHtmlOutputFromFile('Index')
    .setTitle('KK New Store Status')
    .addMetaTag('viewport', 'width=device-width, initial-scale=1')
    .setXFrameOptionsMode(HtmlService.XFrameOptionsMode.ALLOWALL);
}

function getState() {
  const lock = LockService.getScriptLock();
  lock.waitLock(20000);
  try {
    const sh = sheet_();
    const synced = syncAutoStores_(sh, readAll_(sh));
    return state_(sh, synced);
  } finally {
    lock.releaseLock();
  }
}

function setField(key, field, value) {
  const lock = LockService.getScriptLock();
  lock.waitLock(20000);
  try {
    const sh = sheet_();
    const keys = readAll_(sh).map(r => String(r.key));
    const idx = keys.indexOf(clean_(key));
    if (idx < 0) throw new Error('Unknown store');
    if (EDITABLE.indexOf(field) < 0) throw new Error('Field not editable');
    let v = value;
    if (CHECK_FIELDS.indexOf(field) >= 0 || field === 'archived') v = v === true;
    else if (field === 'type') { if (TYPES.indexOf(v) < 0) throw new Error('Bad type'); }
    else { v = clean_(v); if (field === 'store_name' && !v) throw new Error('Name required'); }
    const rowNum = idx + 2;
    sh.getRange(rowNum, HEADERS.indexOf(field) + 1).setValue(v);
    sh.getRange(rowNum, HEADERS.indexOf('updated_at') + 1).setValue(new Date());
    sh.getRange(rowNum, HEADERS.indexOf('updated_by') + 1).setValue(user_());
    log_(key, field, v);
    return state_(sh, true);
  } finally {
    lock.releaseLock();
  }
}

function addStore(o) {
  const lock = LockService.getScriptLock();
  lock.waitLock(20000);
  try {
    o = o || {};
    const name = clean_(o.store_name);
    if (!name) throw new Error('Store name is required');
    const sh = sheet_();
    const key = 'M-' + Date.now();
    sh.appendRow(newRow_({
      key: key, store_name: name, city: clean_(o.city, 60),
      type: TYPES.indexOf(o.type) >= 0 ? o.type : 'Other',
      source: 'manual', launch_date: clean_(o.launch_date, 10),
    }));
    log_(key, 'added', name);
    return state_(sh, true);
  } finally {
    lock.releaseLock();
  }
}
