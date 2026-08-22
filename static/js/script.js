/* IGR index page application script — reads server data from window.IGR_DATA only. */
(function () {
  var data = window.IGR_DATA || {};
  var nodes = (data.nodes || []).slice().sort(function (a, b) {
    return String(a.link_name).localeCompare(String(b.link_name));
  });
  var edges = data.edges || [];
  var routingRules = data.routingRules || {};
  var reverseRoutingRules = data.reverseRoutingRules || {};
  var clearMessageUrl = data.clearMessageUrl || "";

  window.clearInput = function clearInput() {
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
  };

  var elements = nodes.map(function (node) {
    return { data: { id: node.link_name } };
  });
  elements.push({ data: { id: "Router" } });
  edges.forEach(function (edge) {
    elements.push({
      data: {
        id: edge.id,
        source: edge.source,
        target: edge.target,
        label: edge.label != null ? edge.label : "",
      },
    });
  });

  var cy = cytoscape({
    container: document.getElementById("cy"),

    elements: elements,

    style: [
      {
        selector: "node",
        style: {
          label: "data(id)",
          "background-color": "#FFFFFF",
          "border-color": "#0074D9",
          "border-width": 1,
          color: "#0074D9",
          "text-valign": "center",
          "text-halign": "center",
          width: 200,
          height: 200,
          "font-size": 80,
        },
      },
      {
        selector: 'node[id="Router"]',
        style: {
          "background-color": "#FF4136",
          shape: "hexagon",
          label: "IGT",
        },
      },
      {
        selector: "edge",
        style: {
          label: "data(label)",
          "font-size": 80,
          "text-rotation": "autorotate",
          width: 3,
          "line-color": "#aaa",
          "curve-style": "unbundled-bezier",
          "control-point-distances": [70, -70],
          "text-outline-color": "#fff",
          "text-outline-width": 2,
          "mid-source-arrow-color": "#f00",
          "mid-target-arrow-shape": "vee",
          "mid-target-arrow-color": "#00f",
          "control-point-weights": [0.8],
          "arrow-scale": 3,
        },
      },
      {
        selector: ".highlight-in",
        style: {
          "line-color": "red",
          "target-arrow-color": "red",
          width: 5,
        },
      },
      {
        selector: ".highlight-out",
        style: {
          "line-color": "green",
          "target-arrow-color": "green",
          width: 5,
        },
      },
    ],

    layout: {
      name: "concentric",
      concentric: function (node) {
        return node.id() === "Router" ? 2 : 1;
      },
      levelWidth: function () {
        return 1;
      },
      spacingFactor: 2,
    },
  });

  function validateRule(ruleObj, message, inLink) {
    var ruleString = ruleObj.rule || "";
    console.log("Processing rule string:", ruleString);
    var conditions = ruleString
      .replace(/IN_LINK\s*=\s*"([^"]*)"/g, function (match, value) {
        return "'" + inLink + "' === '" + value + "'";
      })
      .replace(/IN_LINK\s+LIKE\s*"([^"]*)"/g, function (match, pattern) {
        var regexPattern = pattern.replace(/\*/g, ".*");
        return "new RegExp('^" + regexPattern + "$').test('" + inLink + "')";
      })
      .replace(/MESSAGE\s+LIKE\s*"([^"]*)"/g, function (match, pattern) {
        var regexPattern = pattern.replace(/\*/g, ".*");
        console.log("Converted MESSAGE LIKE pattern to regex:", regexPattern);
        var regex = new RegExp("^" + regexPattern + "$", "i");
        var matchResult = regex.test(message);
        console.log("Testing message against regex:", message, "Result:", matchResult);
        return matchResult;
      })
      .replace(/MESSAGE\s+UNLIKE\s*"([^"]*)"/g, function (match, pattern) {
        var regexPattern = pattern.replace(/\*/g, ".*");
        console.log("Converted MESSAGE UNLIKE pattern to regex:", regexPattern);
        var regex = new RegExp("^" + regexPattern + "$", "i");
        var matchResult = !regex.test(message);
        console.log("Testing message UNLIKE regex:", message, "Result:", matchResult);
        return matchResult;
      })
      .replace(/\bAND\b/g, "&&")
      .replace(/\bOR\b/g, "||");

    console.log("Evaluating conditions:", conditions);
    console.log("Message:", message, "InLink:", inLink);

    try {
      var result = conditions ? eval(conditions) : false;
      console.log("Validation result:", result);
      return result;
    } catch (error) {
      console.error("Error evaluating conditions:", error);
      return false;
    }
  }

  cy.on("tap", "edge", function (evt) {
    var message = document.getElementById("message").value;
    cy.edges().removeClass("highlight-in highlight-out").data("label", "");
    var clickedEdge = evt.target;
    var sourceNode = clickedEdge.data("source");
    var targetNode = clickedEdge.data("target");

    console.log("Clicked edge:", sourceNode, "to", targetNode);

    if (sourceNode === "Router") {
      var targetLink = targetNode;
      var rules = reverseRoutingRules[targetLink] || [];

      var validRules =
        message.trim() === ""
          ? rules
          : rules.filter(function (rule) {
              return validateRule(rule, message, rule.source);
            });

      console.log("Valid reverse rules after filtering:", validRules);

      clickedEdge.addClass("highlight-out").data(
        "label",
        Array.from(
          new Set(
            validRules.map(function (r) {
              return r.order;
            })
          )
        ).join(", ")
      );

      validRules.forEach(function (rule) {
        var edgeId = rule.source + "_to_Router";
        var originEdge = cy.getElementById(edgeId);
        if (originEdge.length) {
          originEdge.addClass("highlight-in").data("label", rule.order);
        }
      });
    } else {
      var inRules = routingRules[sourceNode] || [];
      console.log("Rules for source node:", sourceNode, inRules);

      var validInRules =
        message.trim() === ""
          ? inRules
          : inRules.filter(function (rule) {
              return validateRule(rule, message, sourceNode);
            });

      console.log("Valid rules after filtering:", validInRules);

      clickedEdge.addClass("highlight-in").data(
        "label",
        Array.from(
          new Set(
            validInRules.map(function (r) {
              return r.order;
            })
          )
        ).join(", ")
      );

      validInRules.forEach(function (rule) {
        var outEdgeId = "Router_to_" + rule.target;
        var targetEdge = cy.getElementById(outEdgeId);
        if (targetEdge.length) {
          targetEdge.addClass("highlight-out").data("label", rule.order);
        }
      });
    }

    var edgeLabel = clickedEdge.data("label");
    var ruleOrders = String(edgeLabel)
      .split(",")
      .map(Number)
      .filter(function (n) {
        return !isNaN(n);
      });

    document.querySelectorAll(".rule-row").forEach(function (row) {
      row.classList.remove("highlight-rule");
      if (ruleOrders.includes(Number(row.dataset.order))) {
        row.classList.add("highlight-rule");
      }
    });

    cy.style().update();
  });

  document.getElementById("recenterBtn").addEventListener("click", function () {
    cy.animate({
      fit: {
        padding: 100,
        nodes: cy.nodes(),
      },
      center: {
        nodes: cy.nodes(),
      },
      zoom: 0.8,
      duration: 500,
    });
  });

  window.addEventListener("resize", function () {
    cy.resize();
    cy.fit(null, 50);
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

  var scrollToMessageBtn = document.getElementById("scrollToMessageBtn");
  Object.assign(scrollToMessageBtn.style, {
    position: "fixed",
    right: "20px",
    bottom: "80px",
    zIndex: 1000,
    background: "#0074D9",
    color: "white",
    border: "none",
    borderRadius: "50%",
    width: "50px",
    height: "50px",
    cursor: "pointer",
    boxShadow: "0 2px 5px rgba(0,0,0,0.3)",
    transition: "all 0.3s ease",
  });

  document.getElementById("scrollToBottomBtn").addEventListener("click", function () {
    window.scrollTo({ top: document.body.scrollHeight, behavior: "smooth" });
  });

  var scrollToBottomBtn = document.getElementById("scrollToBottomBtn");
  Object.assign(scrollToBottomBtn.style, {
    position: "fixed",
    right: "20px",
    bottom: "20px",
    zIndex: 1000,
    background: "#0074D9",
    color: "white",
    border: "none",
    borderRadius: "50%",
    width: "50px",
    height: "50px",
    cursor: "pointer",
    boxShadow: "0 2px 5px rgba(0,0,0,0.3)",
    transition: "all 0.3s ease",
  });

  var scrollToGraphBtn = document.getElementById("scrollToGraphBtn");
  Object.assign(scrollToGraphBtn.style, {
    position: "fixed",
    right: "20px",
    bottom: "140px",
    zIndex: 1000,
    background: "#0074D9",
    color: "white",
    border: "none",
    borderRadius: "50%",
    width: "50px",
    height: "50px",
    cursor: "pointer",
    boxShadow: "0 2px 5px rgba(0,0,0,0.3)",
    transition: "all 0.3s ease",
  });
})();
