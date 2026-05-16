#!/bin/sh
# Tests that the Makefile is structurally sound and its targets behave correctly.
set -e

PASS=0
FAIL=0

pass() { echo "PASS: $1"; PASS=$((PASS + 1)); }
fail() { echo "FAIL: $1"; FAIL=$((FAIL + 1)); }

# ---------------------------------------------------------------------------
# 1. venv python exists and is executable
# ---------------------------------------------------------------------------
if [ -x venv/bin/python ]; then
    pass "venv/bin/python exists and is executable"
else
    fail "venv/bin/python missing or not executable"
fi

# ---------------------------------------------------------------------------
# 2. All .PHONY targets are defined in the Makefile
# ---------------------------------------------------------------------------
EXPECTED_TARGETS="run setup load-demo reset-demo test install-hooks"
PHONY_LINE=$(grep -E '^\.PHONY:' Makefile)
for target in $EXPECTED_TARGETS; do
    if echo "$PHONY_LINE" | grep -qw "$target"; then
        pass ".PHONY declares '$target'"
    else
        fail ".PHONY missing '$target'"
    fi
done

# ---------------------------------------------------------------------------
# 3. Each expected target has a recipe defined
# ---------------------------------------------------------------------------
for target in $EXPECTED_TARGETS; do
    # A target recipe line follows "target:" and starts with a tab
    if awk -v t="$target" '$0 == t":" { found=1; next } found && /^\t/ { exit 0 } found { exit 1 } END { exit found ? 0 : 1 }' Makefile 2>/dev/null; then
        pass "recipe exists for '$target'"
    else
        fail "no recipe found for '$target'"
    fi
done

# ---------------------------------------------------------------------------
# 4. PYTHON variable is set to venv/bin/python
# ---------------------------------------------------------------------------
PYTHON_VAR=$(grep -E '^PYTHON\s*=' Makefile | head -1 | sed 's/.*=[[:space:]]*//' | xargs)
if [ "$PYTHON_VAR" = "venv/bin/python" ]; then
    pass "PYTHON variable is 'venv/bin/python'"
else
    fail "PYTHON variable is '$PYTHON_VAR', expected 'venv/bin/python'"
fi

# ---------------------------------------------------------------------------
# 5. make install-hooks succeeds and hooks become executable
# ---------------------------------------------------------------------------
if make install-hooks > /dev/null 2>&1; then
    pass "make install-hooks exits 0"
else
    fail "make install-hooks exited non-zero"
fi

for hook in .githooks/pre-commit .githooks/pre-push; do
    if [ -x "$hook" ]; then
        pass "$hook is executable after install-hooks"
    else
        fail "$hook is not executable after install-hooks"
    fi
done

if [ "$(git config core.hooksPath)" = ".githooks" ]; then
    pass "git core.hooksPath set to .githooks"
else
    fail "git core.hooksPath not set correctly"
fi

# ---------------------------------------------------------------------------
# 6. make test exits 0 (runs the real suite)
# ---------------------------------------------------------------------------
if make test > /dev/null 2>&1; then
    pass "make test exits 0"
else
    fail "make test exited non-zero"
fi

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo ""
echo "Results: $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ]
