/* IGR index page wiring — admin clear, graph bootstrap, navigation chrome. */
(function () {
  var data = window.IGR_DATA || {};
  var clearMessageUrl = data.clearMessageUrl || "";

  function clearInput() {
    fetch(clearMessageUrl, {
      method: "POST",
      credentials: "same-origin",
      headers: { Accept: "application/json" },
    })
      .then(function (response) {
        if (response.ok) {
          document.getElementById("message").value = "";
        } else {
          alert("Clear requires admin login.");
        }
      })
      .catch(function () {
        alert("Clear failed.");
      });
  }

  var clearButton = document.getElementById("clearButton");
  if (clearButton) {
    clearButton.addEventListener("click", clearInput);
  }

  window.IGR.createGraph({
    container: document.getElementById("cy"),
    nodes: data.nodes || [],
    edges: data.edges || [],
    routingRules: data.routingRules || {},
    reverseRoutingRules: data.reverseRoutingRules || {},
    messageInput: document.getElementById("message"),
    recenterBtn: document.getElementById("recenterBtn"),
    validateRule: window.IGR.validateRule,
  });

  document.getElementById("messageForm").addEventListener("submit", function (e) {
    e.preventDefault();
    var message = document.getElementById("message").value;

    if (!message) {
      alert("Bitte gib eine Nachricht ein");
      return;
    }

    console.log("Sending:", { message: message });
  });

  document.getElementById("scrollToGraphBtn").addEventListener("click", function () {
    document.getElementById("cy").scrollIntoView({ behavior: "smooth" });
  });

  document.getElementById("scrollToMessageBtn").addEventListener("click", function () {
    document.getElementById("messageContainer").scrollIntoView({ behavior: "smooth" });
  });

  document.getElementById("scrollToBottomBtn").addEventListener("click", function () {
    window.scrollTo({ top: document.body.scrollHeight, behavior: "smooth" });
  });
})();
