const test = require('node:test');
const assert = require('node:assert');
const { computeAlerts, filterByCity } = require('../alerts');

const THRESHOLDS = { cancellation_alert_pct: 5, kpt_p80_max_minutes: 10, min_online_opd: 3 };

function dayEntry(date, { swiggy = 0, zomato = 0, ownly = 0, dineIn = 0 } = {}) {
  return {
    date,
    online: { swiggy, zomato, ownly },
    orders_by_channel: { swiggy, zomato, ownly },
    online_orders: swiggy + zomato + ownly,
    dine_in_orders: dineIn,
    total: swiggy + zomato + ownly + dineIn,
  };
}

test('computeAlerts flags zero orders today when history exists', () => {
  // ₹0 revenue with orders > 0 (e.g. a fully-discounted order) must NOT
  // be treated the same as zero orders — orders is the sharper signal.
  const stores = [{
    display_name: 'Ravet', launch_date: '2026-07-17',
    revenue: { daily: [dayEntry('2026-08-18', { swiggy: 5 })] },
  }];
  const alerts = computeAlerts(stores, THRESHOLDS, '2026-08-19');
  assert.ok(alerts.some(a => a.type === 'zero_orders'));
});

test('computeAlerts suppresses zero-orders alert before launch_date', () => {
  const stores = [{ display_name: 'Niyati Plaza', launch_date: '2026-08-20', revenue: { daily: [] } }];
  const alerts = computeAlerts(stores, THRESHOLDS, '2026-08-19');
  assert.strictEqual(alerts.some(a => a.type === 'zero_orders'), false);
});

test('computeAlerts suppresses zero-orders alert when store has no history yet at all', () => {
  const stores = [{ display_name: 'Sangvi', launch_date: '2026-08-01', revenue: { daily: [] } }];
  const alerts = computeAlerts(stores, THRESHOLDS, '2026-08-19');
  assert.strictEqual(alerts.some(a => a.type === 'zero_orders'), false);
});

test('computeAlerts flags zero Swiggy orders when Swiggy order history exists', () => {
  const stores = [{
    display_name: 'Ravet', launch_date: '2026-07-17',
    revenue: { daily: [
      dayEntry('2026-08-17', { swiggy: 8, zomato: 4 }),
      dayEntry('2026-08-18', { swiggy: 0, zomato: 5 }),
    ] },
  }];
  const alerts = computeAlerts(stores, THRESHOLDS, '2026-08-19');
  assert.ok(alerts.some(a => a.type === 'zero_swiggy_orders'));
});

test('computeAlerts does not flag zero Swiggy orders when the store never had a Swiggy order', () => {
  const stores = [{
    display_name: 'GIP Mall', launch_date: '2026-07-23',
    revenue: { daily: [
      dayEntry('2026-08-17', { dineIn: 10 }),
      dayEntry('2026-08-18', { dineIn: 5 }),
    ] },
  }];
  const alerts = computeAlerts(stores, THRESHOLDS, '2026-08-19');
  assert.strictEqual(alerts.some(a => a.type === 'zero_swiggy_orders'), false);
});

test('computeAlerts flags zero Zomato orders when Zomato order history exists', () => {
  const stores = [{
    display_name: 'Ravet', launch_date: '2026-07-17',
    revenue: { daily: [
      dayEntry('2026-08-17', { swiggy: 4, zomato: 8 }),
      dayEntry('2026-08-18', { swiggy: 5, zomato: 0 }),
    ] },
  }];
  const alerts = computeAlerts(stores, THRESHOLDS, '2026-08-19');
  assert.ok(alerts.some(a => a.type === 'zero_zomato_orders'));
});

test('computeAlerts does not flag zero Zomato orders when the store never had a Zomato order', () => {
  const stores = [{
    display_name: 'GIP Mall', launch_date: '2026-07-23',
    revenue: { daily: [
      dayEntry('2026-08-17', { dineIn: 10 }),
      dayEntry('2026-08-18', { dineIn: 5 }),
    ] },
  }];
  const alerts = computeAlerts(stores, THRESHOLDS, '2026-08-19');
  assert.strictEqual(alerts.some(a => a.type === 'zero_zomato_orders'), false);
});

test('computeAlerts flags low online orders-per-day for the most recent day', () => {
  const stores = [{
    display_name: 'Kothrud', launch_date: '2026-07-07',
    revenue: { daily: [dayEntry('2026-08-19', { swiggy: 1 })] },
  }];
  const alerts = computeAlerts(stores, THRESHOLDS, '2026-08-19');
  assert.ok(alerts.some(a => a.type === 'low_online_opd'));
});

test('computeAlerts flags high cancellation for the most recent day', () => {
  const stores = [{
    display_name: 'Wagholi', launch_date: '2026-07-15', revenue: { daily: [] },
    ops_computed: { daily: [{ date: '2026-08-19', platform: 'Swiggy', order_count: 20, cancelled_orders: 2, kpt_p80_minutes: 3 }] },
  }];
  const alerts = computeAlerts(stores, THRESHOLDS, '2026-08-19');
  assert.ok(alerts.some(a => a.type === 'cancellation_high'));
});

test('computeAlerts flags high KPT P80 for the most recent day', () => {
  const stores = [{
    display_name: 'Wagholi', launch_date: '2026-07-15', revenue: { daily: [] },
    ops_computed: { daily: [{ date: '2026-08-19', platform: 'Swiggy', order_count: 20, cancelled_orders: 0, kpt_p80_minutes: 12 }] },
  }];
  const alerts = computeAlerts(stores, THRESHOLDS, '2026-08-19');
  assert.ok(alerts.some(a => a.type === 'kpt_high'));
});

test('computeAlerts does not flag cancellation/KPT within thresholds', () => {
  const stores = [{
    display_name: 'Wagholi', launch_date: '2026-07-15', revenue: { daily: [] },
    ops_computed: { daily: [{ date: '2026-08-19', platform: 'Swiggy', order_count: 20, cancelled_orders: 0, kpt_p80_minutes: 3 }] },
  }];
  const alerts = computeAlerts(stores, THRESHOLDS, '2026-08-19');
  assert.strictEqual(alerts.some(a => a.type === 'cancellation_high'), false);
  assert.strictEqual(alerts.some(a => a.type === 'kpt_high'), false);
});

test('filterByCity returns only matching stores', () => {
  const stores = [{ city: 'Pune' }, { city: 'NCR' }];
  assert.strictEqual(filterByCity(stores, 'NCR').length, 1);
});

test('filterByCity returns all stores for "All"', () => {
  const stores = [{ city: 'Pune' }, { city: 'NCR' }];
  assert.strictEqual(filterByCity(stores, 'All').length, 2);
});
