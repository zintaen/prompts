// Vercel Web Analytics - Static import for vanilla HTML
(function() {
  window.va = window.va || function () { 
    (window.vaq = window.vaq || []).push(arguments); 
  };
  var script = document.createElement('script');
  script.defer = true;
  script.src = '/_vercel/insights/script.js';
  document.head.appendChild(script);
})();
