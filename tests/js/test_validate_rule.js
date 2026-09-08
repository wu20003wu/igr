/**
 * Behavioral contract tests for the CURRENT validateRule() in static/js/rule-validator.js.
 * Documents current semantics — including surprising ones. Do not "fix" production here.
 */
const { describe, it } = require("node:test");
const assert = require("node:assert/strict");
const { validateRule } = require("../../static/js/rule-validator.js");

function rule(text) {
  return { rule: text };
}

describe("validateRule — IN_LINK equality", () => {
  it("matching link -> true", () => {
    assert.equal(validateRule(rule('IN_LINK = "FIX_A"'), "", "FIX_A"), true);
  });

  it("different link -> false", () => {
    assert.equal(validateRule(rule('IN_LINK = "FIX_A"'), "", "FIX_B"), false);
  });
});

describe("validateRule — IN_LINK LIKE", () => {
  it("wildcard match (* -> .*)", () => {
    assert.equal(validateRule(rule('IN_LINK LIKE "A*"'), "", "AB"), true);
    assert.equal(validateRule(rule('IN_LINK LIKE "A*"'), "", "A"), true);
  });

  it("wildcard mismatch", () => {
    assert.equal(validateRule(rule('IN_LINK LIKE "A*"'), "", "BA"), false);
  });

  it("exact-looking pattern without * matches only the full string", () => {
    // Pattern becomes ^A$ after * replacement (none) — current behavior
    assert.equal(validateRule(rule('IN_LINK LIKE "A"'), "", "A"), true);
    assert.equal(validateRule(rule('IN_LINK LIKE "A"'), "", "AB"), false);
  });

  it("wildcard in middle", () => {
    assert.equal(validateRule(rule('IN_LINK LIKE "A*B"'), "", "AXB"), true);
    assert.equal(validateRule(rule('IN_LINK LIKE "A*B"'), "", "AB"), true);
    assert.equal(validateRule(rule('IN_LINK LIKE "A*B"'), "", "AXYB"), true);
    assert.equal(validateRule(rule('IN_LINK LIKE "A*B"'), "", "AX"), false);
  });
});

describe("validateRule — MESSAGE LIKE", () => {
  it("matching message -> true", () => {
    assert.equal(
      validateRule(rule('MESSAGE LIKE "*35=D*"'), "xxx|35=D|yyy", "A"),
      true
    );
  });

  it("non-matching message -> false", () => {
    assert.equal(
      validateRule(rule('MESSAGE LIKE "*35=D*"'), "xxx|35=8|yyy", "A"),
      false
    );
  });

  it("case-insensitive behavior", () => {
    assert.equal(
      validateRule(rule('MESSAGE LIKE "*abc*"'), "XXABCXX", "A"),
      true
    );
    assert.equal(
      validateRule(rule('MESSAGE LIKE "*ABC*"'), "xxabcxx", "A"),
      true
    );
  });
});

describe("validateRule — MESSAGE UNLIKE", () => {
  it("non-matching message -> true", () => {
    assert.equal(
      validateRule(rule('MESSAGE UNLIKE "*ERROR*"'), "all good", "A"),
      true
    );
  });

  it("matching message -> false", () => {
    assert.equal(
      validateRule(rule('MESSAGE UNLIKE "*ERROR*"'), "got ERROR here", "A"),
      false
    );
  });

  it("case-insensitive unlike", () => {
    assert.equal(
      validateRule(rule('MESSAGE UNLIKE "*error*"'), "got ERROR here", "A"),
      false
    );
  });
});

describe("validateRule — AND combinations", () => {
  const text = 'IN_LINK = "A" AND MESSAGE LIKE "*35=D*"';

  it("all conditions true -> true", () => {
    assert.equal(validateRule(rule(text), "prefix|35=D|suffix", "A"), true);
  });

  it("one condition false (wrong link) -> false", () => {
    assert.equal(validateRule(rule(text), "prefix|35=D|suffix", "B"), false);
  });

  it("one condition false (wrong message) -> false", () => {
    assert.equal(validateRule(rule(text), "prefix|35=8|suffix", "A"), false);
  });
});

describe("validateRule — OR combinations", () => {
  const text = 'IN_LINK = "A" OR IN_LINK = "B"';

  it("first condition true -> true", () => {
    assert.equal(validateRule(rule(text), "", "A"), true);
  });

  it("second condition true -> true", () => {
    assert.equal(validateRule(rule(text), "", "B"), true);
  });

  it("both false -> false", () => {
    assert.equal(validateRule(rule(text), "", "C"), false);
  });
});

describe("validateRule — mixed AND / OR (current JS precedence)", () => {
  // After replacement: IN_LINK = "A" OR IN_LINK = "B" AND MESSAGE LIKE "*X*"
  // becomes: 'A'==='…' || 'B'==='…' && <bool>
  // JS: && binds tighter than ||  =>  left || (right && msg)
  const text = 'IN_LINK = "A" OR IN_LINK = "B" AND MESSAGE LIKE "*X*"';

  it("A alone is enough (left of OR) even if message would fail B-branch", () => {
    assert.equal(validateRule(rule(text), "no-x-here", "A"), true);
  });

  it("B requires matching message due to && binding", () => {
    assert.equal(validateRule(rule(text), "contains X yes", "B"), true);
    assert.equal(validateRule(rule(text), "no match", "B"), false);
  });

  it("neither link -> false", () => {
    assert.equal(validateRule(rule(text), "contains X yes", "C"), false);
  });
});

describe("validateRule — empty / missing rule", () => {
  it("empty rule string -> false", () => {
    assert.equal(validateRule(rule(""), "anything", "A"), false);
  });

  it("ruleObj without rule property -> false", () => {
    assert.equal(validateRule({}, "anything", "A"), false);
  });
});

describe("validateRule — invalid / unsupported strings", () => {
  it("unsupported keyword left as-is causes eval error -> false", () => {
    assert.equal(validateRule(rule("NOT_A_REAL_RULE"), "", "A"), false);
  });

  it("unbalanced remnant / junk after rewrites -> false", () => {
    assert.equal(validateRule(rule("IN_LINK = \"A\" AND (((("), "", "A"), false);
  });

  it("MESSAGE LIKE invalid regex metacharacters throw during rewrite (outside eval try/catch)", () => {
    // RegExp is built in the replace callback BEFORE the try/catch around eval.
    // Current contract: throws SyntaxError instead of returning false.
    assert.throws(
      () => validateRule(rule('MESSAGE LIKE "*35=(D*"'), "35=(D", "A"),
      { name: "SyntaxError" }
    );
  });
});

describe("validateRule — special-character edge cases (current behavior)", () => {
  it("pipe characters in MESSAGE LIKE pattern become regex alternation (surprising current)", () => {
    // Pattern *|35=D|* -> .*|35=D|.* which is OR of .*, 35=D, .* — not literal pipes.
    // Still returns true for typical FIX messages because .* matches.
    assert.equal(
      validateRule(rule('MESSAGE LIKE "*|35=D|*"'), "8=FIX|35=D|49=X", "A"),
      true
    );
  });

  it("dollar in link name with equality", () => {
    assert.equal(validateRule(rule('IN_LINK = "$log"'), "", "$log"), true);
  });

  it("inLink containing a single quote breaks string construction (documents current risk)", () => {
    // Produces: 'O'Brien' === 'A'  -> SyntaxError -> false (current contract)
    assert.equal(validateRule(rule('IN_LINK = "A"'), "", "O'Brien"), false);
  });
});
