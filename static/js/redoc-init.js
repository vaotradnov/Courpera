/* Initialize Redoc without inline scripts to satisfy CSP */
(function () {
  function init() {
    var el = document.getElementById('redoc-container');
    if (!el || typeof window.Redoc === 'undefined') return;
    var url = el.getAttribute('data-schema-url') || '/api/schema/';
    try {
      window.Redoc.init(url, {}, el);
    } catch (e) {
      // No-op
    }
  }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
