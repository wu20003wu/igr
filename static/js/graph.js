/**
 * Cytoscape graph construction and interaction.
 * Depends on: cytoscape, window.IGR.validateRule
 * Does not own page navigation / admin clear / scroll-button chrome.
 */
(function (root) {
  function createGraph(options) {
    var nodes = (options.nodes || []).slice().sort(function (a, b) {
      return String(a.link_name).localeCompare(String(b.link_name));
    });
    var edges = options.edges || [];
    var routingRules = options.routingRules || {};
    var reverseRoutingRules = options.reverseRoutingRules || {};
    var validateRule = options.validateRule || root.IGR.validateRule;
    var messageInput =
      options.messageInput || document.getElementById("message");
    var container =
      options.container || document.getElementById("cy");
    var recenterBtn =
      options.recenterBtn || document.getElementById("recenterBtn");

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
      container: container,

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

    cy.on("tap", "edge", function (evt) {
      var message = messageInput.value;
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

    if (recenterBtn) {
      recenterBtn.addEventListener("click", function () {
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
    }

    window.addEventListener("resize", function () {
      cy.resize();
      cy.fit(null, 50);
    });
  }

  root.IGR = root.IGR || {};
  root.IGR.createGraph = createGraph;
})(typeof window !== "undefined" ? window : globalThis);
