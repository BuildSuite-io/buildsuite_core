# JV Expense → BOQ Cost Code → Actual

Charge a **Journal Entry (JV)** expense line to a **BOQ cost code**, so direct GL spend posted by a
Journal Voucher lands in **BOQ actual** — with a hyperlink from the BOQ drill-down back to the JV.

Before this, only three rails produced BOQ actual (Material Consumption, Subcontractor Bill,
Expense Entry). The Journal Entry is the fourth.

---

## Where a user does it (Desk Journal Entry)

The JV is the standard **Desk** Journal Entry form (`/app/journal-entry`). The cost code lives on
each **accounts line** (the `Journal Entry Account` child row), which is where an expense is
recognised.

On each line, three columns are shown in the accounts grid:

| Column | Field | Notes |
|---|---|---|
| **Project** | `project` (native) | Set this first — cost codes are resolved per project. |
| **Cost Code Type** | `custom_cost_code_type` | `Group` or `Item`. Picking it opens the code picker. |
| **Cost Code** | `custom_cost_code_label` | Read-only result, e.g. `A · Civil`. |

**Flow:** on an expense (debit) line, set **Project** → set **Cost Code Type** → a dialog lists that
project's **Approved-BOQ** cost codes → pick one. The line's group/item/label are stamped. Only the
line's **debit** books to actual, so the balancing credit leg needs no code.

> If nothing appears, hard-refresh the form (`Ctrl/Cmd+Shift+R`). The fields are custom fields +
> a property setter applied on migrate; the picker is a client script served from the built assets.

---

## The actuals rails (what feeds BOQ actual)

BOQ actual is a **derived getter** (`buildsuite_core/api/boq_actuals.py`) — computed live from
**submitted** source documents, never stored. Cost is recognised **at consumption**, not at
request/order/receipt. Each rail carries a cost code and emits a source reference for the
drill-down.

| Source document | Amount used | Cost type | Feeds actual? |
|---|---|---|---|
| **Material Consumption** — Stock Entry / *Material Issue* | outgoing value | Material | ✅ |
| **Subcontractor Bill** | this-period certified amount | Subcontract | ✅ |
| **Expense Entry** | line amount | Overhead | ✅ |
| **Journal Entry** *(this feature)* | line **debit** | Overhead | ✅ |
| **Material Request (MR)** | — | — | ❌ a request is not spend |
| **Purchase Order / Purchase Receipt** | — | — | ❌ cost recognised at consumption, not receipt |
| **Subcontractor Work Order** | commitment | — | ❌ *Committed*, a separate column — not actual |

So **Expense Entry and Subcontractor Bill already populate actual**, as does **Material
Consumption** (the *Material Issue*, not the Material Request). This change adds **Journal Entry**.
An **MR does not** feed actual, by design.

---

## The BOQ actual hyperlink (drill-down)

Every rail emits `{source_doctype, source_name, source_line}`. The BOQ detail view
(`frontend/src/views/BoqDetailView.vue`, `openActualSource`) turns that into a link to the source
document:

- Subcontractor Bill → in-app `/subcontractor-bills/<name>`
- Stock Entry / Expense Entry / **Journal Entry** → Desk form in a new tab
  (`/app/journal-entry/<name>`)

---

## Behaviour

- **Submit** posts the contribution; **Cancel** removes it — the getter reads only submitted docs,
  so reversal is automatic (no stored ledger to unwind).
- Only the **debit** on a line contributes (a credit leg has debit = 0 and self-excludes).
- JV expense is classed as **Overhead** (matching Expense Entry). If a JV should count as
  Material/Labour/Plant, that would be a follow-up (derive from the expense account, or add a field).

---

## Implementation map

| Area | File | Change |
|---|---|---|
| Line fields | `buildsuite_core/custom_property_list/custom_field.py` | 4 `custom_cost_code_*` fields on `Journal Entry Account` (type + label `in_list_view`) |
| Grid Project | `buildsuite_core/custom_property_list/property_field.py` | property setter: `Journal Entry Account.project` `in_list_view` |
| Desk picker | `buildsuite_core/public/js/journal_entry.js` | line-level cost-code picker (`get_project_cost_codes`) |
| Actuals rail | `buildsuite_core/api/boq_actuals.py` | `_journal_entries` feeder, wired into `_actual_entries` |
| Drill-down link | `frontend/src/views/BoqDetailView.vue` | Journal Entry → Desk hyperlink |
| Test | `buildsuite_core/tests/test_cost_report.py` | `test_journal_entry_actual_by_cost_code` |

## Deployment

Fields + property setter apply automatically on **`bench migrate`** (`after_migrate` →
`create_custom_fields` + `make_property_setters`). No separate patch. The client-script picker is
served from the built app assets — run `bench build --app buildsuite_core` on deploy (part of the
normal build). Cost codes come from the project's **Approved** BOQ only.
