/**
 * Routing-rule validation only.
 * Browser: window.IGR.validateRule
 * Node/tests: module.exports = { validateRule }
 * No DOM / Cytoscape / IGR_DATA / fetch.
 */
(function (root) {
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

  if (typeof module === "object" && module.exports) {
    module.exports = { validateRule: validateRule };
  }

  root.IGR = root.IGR || {};
  root.IGR.validateRule = validateRule;
})(typeof window !== "undefined" ? window : globalThis);
