'use strict';

function computeAlerts(stores, thresholds, todayStr) {
  const alerts = [];

  for (const store of stores) {
    if (store.launch_date && store.launch_date <= todayStr) {
      const todayEntry = store.revenue.daily.find(d => d.date === todayStr);
      const hasAnyHistory = store.revenue.daily.some(d => d.date < todayStr);
      // Orders, not revenue: zero orders always means zero revenue, but
      // the reverse isn't reliable (a fully-discounted order can show
      // ₹0 revenue while still being a real order) — orders is the
      // sharper "did anything actually happen" signal.
      const todayTotalOrders = todayEntry ? todayEntry.online_orders + todayEntry.dine_in_orders : 0;
      if (hasAnyHistory && (!todayEntry || todayTotalOrders === 0)) {
        alerts.push({ store: store.display_name, type: 'zero_orders', value: '0 orders', detail: `No orders recorded for ${todayStr}` });
      }

      const hasSwiggyHistory = store.revenue.daily.some(d => d.date < todayStr && d.orders_by_channel.swiggy > 0);
      if (hasSwiggyHistory && (!todayEntry || todayEntry.orders_by_channel.swiggy === 0)) {
        alerts.push({ store: store.display_name, type: 'zero_swiggy_orders', value: '0 orders', detail: `No Swiggy orders recorded for ${todayStr}` });
      }

      const hasZomatoHistory = store.revenue.daily.some(d => d.date < todayStr && d.orders_by_channel.zomato > 0);
      if (hasZomatoHistory && (!todayEntry || todayEntry.orders_by_channel.zomato === 0)) {
        alerts.push({ store: store.display_name, type: 'zero_zomato_orders', value: '0 orders', detail: `No Zomato orders recorded for ${todayStr}` });
      }

      if (todayEntry && todayEntry.online_orders < thresholds.min_online_opd) {
        alerts.push({ store: store.display_name, type: 'low_online_opd', value: String(todayEntry.online_orders), detail: `Only ${todayEntry.online_orders} online orders on ${todayStr} (< ${thresholds.min_online_opd})` });
      }
    }

    const opsComputedDaily = (store.ops_computed && store.ops_computed.daily) || [];
    const todaysComputed = opsComputedDaily.filter(d => d.date === todayStr);
    if (todaysComputed.length) {
      let orders = 0, cancelled = 0, kptWeightedSum = 0, kptWeight = 0;
      for (const d of todaysComputed) {
        orders += d.order_count;
        cancelled += d.cancelled_orders;
        if (d.kpt_p80_minutes !== null) { kptWeightedSum += d.kpt_p80_minutes * d.order_count; kptWeight += d.order_count; }
      }
      const cancellationPct = orders > 0 ? (cancelled / orders) * 100 : null;
      const kptP80 = kptWeight > 0 ? kptWeightedSum / kptWeight : null;
      if (cancellationPct !== null && cancellationPct > thresholds.cancellation_alert_pct) {
        alerts.push({ store: store.display_name, type: 'cancellation_high', value: `${cancellationPct.toFixed(1)}%`, detail: `Cancellation ${cancellationPct.toFixed(1)}% > ${thresholds.cancellation_alert_pct}%` });
      }
      if (kptP80 !== null && kptP80 > thresholds.kpt_p80_max_minutes) {
        alerts.push({ store: store.display_name, type: 'kpt_high', value: `${kptP80.toFixed(1)} min`, detail: `KPT P80 ${kptP80.toFixed(1)} min > ${thresholds.kpt_p80_max_minutes} min` });
      }
    }
  }

  return alerts;
}

function filterByCity(stores, city) {
  if (!city || city === 'All') return stores;
  return stores.filter(s => s.city === city);
}

const AlertsModule = { computeAlerts, filterByCity };

if (typeof module !== 'undefined' && module.exports) {
  module.exports = AlertsModule;
}
if (typeof window !== 'undefined') {
  window.Alerts = AlertsModule;
}
