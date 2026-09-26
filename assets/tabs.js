// Two top-level tabs. "New Store Status" is the default; it embeds the
// curefoods.in-only Apps Script checklist, loaded lazily on first view.
(function () {
  const TABS = ['status', 'performance'];

  function show(tab) {
    if (TABS.indexOf(tab) < 0) tab = 'status';
    TABS.forEach(t => {
      document.getElementById('view-' + t).hidden = t !== tab;
      document.querySelector('#tabs [data-tab="' + t + '"]').classList.toggle('on', t === tab);
    });
    // The "Data as of" line describes the 90d performance data only.
    document.getElementById('generated-at').hidden = tab === 'status';
    if (tab === 'status') {
      const f = document.getElementById('status-frame');
      if (!f.src) f.src = f.dataset.src;
    }
  }

  window.addEventListener('hashchange', () => show(location.hash.slice(1)));
  show(location.hash.slice(1));
})();
