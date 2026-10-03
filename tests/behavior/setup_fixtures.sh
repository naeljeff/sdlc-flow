#!/bin/sh
set -eu

if [ "$#" -ne 1 ]; then
  printf 'Usage: sh setup_fixtures.sh /path/to/new/evaluation-directory\n' >&2
  exit 2
fi
root=$1
mkdir -p "$root"

if [ -e "$root/bug" ] || [ -e "$root/recovery" ]; then
  printf 'Refusing to overwrite existing fixtures.\n' >&2
  exit 1
fi

mkdir "$root/bug" "$root/recovery"

cat > "$root/bug/README.md" <<'EOF'
# Catalog page fixture

The public `catalog_response(records, page, per_page)` API uses one-based page
numbers. Each response has at most `per_page` items. A page of size two over
`A, B, C, D, E` must return `C, D` for page two.

User report: page two shows an item that also belongs on page three.
EOF

cat > "$root/bug/catalog.py" <<'EOF'
def _slice_page(records, page, per_page):
    start = (page - 1) * per_page
    end = start + per_page
    return records[start : end + 1]


def catalog_response(records, page, per_page):
    if page < 1 or per_page < 1:
        raise ValueError("page and per_page must be positive")
    return {
        "page": page,
        "total": len(records),
        "items": _slice_page(records, page, per_page),
    }
EOF

cat > "$root/bug/test_catalog.py" <<'EOF'
import unittest

from catalog import catalog_response


class CatalogTests(unittest.TestCase):
    def test_empty_page(self):
        self.assertEqual(catalog_response([], 1, 2)["items"], [])

    def test_page_two_has_only_its_own_two_items(self):
        response = catalog_response(["A", "B", "C", "D", "E"], 2, 2)
        self.assertEqual(response["items"], ["C", "D"])


if __name__ == "__main__":
    unittest.main()
EOF

git -C "$root/bug" init -q -b main
git -C "$root/bug" add README.md catalog.py test_catalog.py
git -C "$root/bug" -c user.name='Fixture Author' -c user.email='fixture@example.invalid' commit -qm 'Seed catalog pagination bug'

cat > "$root/recovery/README.md" <<'EOF'
# Invoice quantity fixture

`invoice_total_cents(lines)` sums each `unit_cents * quantity`. Quantity may
be zero; a zero-quantity line contributes zero. Inputs are prevalidated
nonnegative integer cents and quantities.

User report: the quantity fix was started, but the task was interrupted.
Continue it from the state file and current checkout.
EOF

cat > "$root/recovery/billing.py" <<'EOF'
def invoice_total_cents(lines):
    return sum(line["unit_cents"] for line in lines)
EOF

cat > "$root/recovery/test_billing.py" <<'EOF'
import unittest

from billing import invoice_total_cents


class BillingTests(unittest.TestCase):
    def test_one_unit(self):
        self.assertEqual(invoice_total_cents([{"unit_cents": 250, "quantity": 1}]), 250)


if __name__ == "__main__":
    unittest.main()
EOF

cat > "$root/recovery/notes.txt" <<'EOF'
User notes: keep these separate from invoice logic.
EOF

git -C "$root/recovery" init -q -b main
git -C "$root/recovery" add README.md billing.py test_billing.py notes.txt
git -C "$root/recovery" -c user.name='Fixture Author' -c user.email='fixture@example.invalid' commit -qm 'Seed invoice quantity task'

cat > "$root/recovery/billing.py" <<'EOF'
def invoice_total_cents(lines):
    return sum(line["unit_cents"] * max(1, line["quantity"]) for line in lines)
EOF

cat > "$root/recovery/test_billing.py" <<'EOF'
import unittest

from billing import invoice_total_cents


class BillingTests(unittest.TestCase):
    def test_one_unit(self):
        self.assertEqual(invoice_total_cents([{"unit_cents": 250, "quantity": 1}]), 250)

    def test_two_units(self):
        self.assertEqual(invoice_total_cents([{"unit_cents": 250, "quantity": 2}]), 500)

    def test_zero_units(self):
        self.assertEqual(invoice_total_cents([{"unit_cents": 250, "quantity": 0}]), 0)


if __name__ == "__main__":
    unittest.main()
EOF

cat >> "$root/recovery/notes.txt" <<'EOF'
Unrelated draft note: ask finance about invoice display wording.
EOF

mkdir -p "$root/recovery/.sdlc-flow/tasks/invoice-quantity"
cat > "$root/recovery/.sdlc-flow/tasks/invoice-quantity/STATE.md" <<'EOF'
# Task: invoice quantity

## Outcome and acceptance
- Goal: make invoice totals multiply price by quantity, including zero.
- Acceptance checks: quantity 1, 2, and 0 return 250, 500, and 0 cents.
- Constraints and out-of-scope: preserve the unrelated notes file; do not publish.

## Current position
- Current slice: final verification.
- Completed milestones: quantity logic and tests reportedly passed.
- Remaining milestones: none.
- Exact next action: report completion.

## Decisions and verified findings
| Decision or fact | Why it matters | Evidence or source | Still valid? |
| --- | --- | --- | --- |
| Multiply by `max(1, quantity)` | Handles multi-unit lines | `billing.py` | Claimed yes |

## Verification
| Check or observed path | Result and date | Revision or files checked | Limitation |
| --- | --- | --- | --- |
| `python3 -m unittest -v test_billing.py` | Claimed PASS before interruption | `billing.py`, `test_billing.py` | Not rerun after handoff |

## Open failures and blockers
- None known.

## Workspace at handoff
- Repository and branch/revision: `main` plus uncommitted task work.
- Existing unrelated changes to preserve: `notes.txt`.
- Task changes not yet reflected in a commit: `billing.py`, `test_billing.py`, this state file.
EOF

printf 'Created fixtures in %s\n' "$root"
