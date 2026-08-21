const test = require('node:test');
const assert = require('node:assert');
const { computeAlerts, filterByCity } = require('../alerts');

const THRESHOLDS = { cancellation_alert_pct: 5, kpt_p80_max_minutes: 10, min_online_opd: 3 };

test('computeAlerts flags zero revenue today when history exists', () => {
  const stores = [{
    display_name: 'Ravet', launch_date: '2026-07-17',
    revenue: { daily: [{ date: '2026-08-18', online: { swiggy: 100, zomato: 0, ownly: 0 }, total: 100, online_orders: 5 }] },
  }];
  const alerts = computeAlerts(stores, THRESHOLDS, '2026-08-19');
  assert.ok(alerts.some(a => a.type === 'zero_revenue'));
});

test('computeAlerts suppresses zero-revenue alert before launch_date', () => {
  const stores = [{ display_name: 'Niyati Plaza', launch_date: '2026-08-20', revenue: { daily: [] } }];
  const alerts = computeAlerts(stores, THRESHOLDS, '2026-08-19');
  assert.strictEqual(alerts.some(a => a.type === 'zero_revenue'), false);
});

test('computeAlerts suppresses zero-revenue alert when store has no history yet at all', () => {
  const stores = [{ display_name: 'Sangvi', launch_date: '2026-08-01', revenue: { daily: [] } }];
  const alerts = computeAlerts(stores, THRESHOLDS, '2026-08-19');
  assert.strictEqual(alerts.some(a => a.type === 'zero_revenue'), false);
});

test('computeAlerts flags low online orders-per-day for the most recent day', () => {
  const stores = [{
    display_name: 'Kothrud', launch_date: '2026-07-07',
    revenue: { daily: [{ date: '2026-08-19', online: { swiggy: 50, zomato: 0, ownly: 0 }, total: 50, online_orders: 1 }] },
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
