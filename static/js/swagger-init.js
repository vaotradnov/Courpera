/* Initialize Swagger UI without inline scripts to satisfy CSP */
(function () {
  function init() {
    var el = document.getElementById('swagger-ui');
    if (!el || typeof window.SwaggerUIBundle !== 'function') return;
    var url = el.getAttribute('data-schema-url') || '/api/schema/';
    try {
      window.ui = window.SwaggerUIBundle({
        url: url,
        dom_id: '#swagger-ui',
        presets: [window.SwaggerUIBundle.presets.apis, window.SwaggerUIStandalonePreset],
        layout: 'StandaloneLayout',
        deepLinking: true,
      });
    } catch (e) {
      // No-op: avoid breaking page if assets not loaded yet
    }
  }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
