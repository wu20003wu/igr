document.addEventListener('DOMContentLoaded', function() {
  const cy = cytoscape({
    // Ursprüngliche Konfiguration hier einfügen
    container: document.getElementById('cy'),
    elements: [/* ... */],
    style: [/* ... */],
    layout: {/* ... */}
  });

  // Routing-Regeln und Event-Handler hier einfügen
  const routingRules = {/* ... */};
  
  cy.on('tap', 'edge', function(evt) {
    // Ursprüngliche Logik hier
  });
}); 