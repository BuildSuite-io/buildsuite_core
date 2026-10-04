# Plan: Subcontractor Bill → Purchase Invoice + Vue frontend

## Context

The Subcontract module ships Subcontractor → Work Order (SOV) → Measurement Book, and a
**tracking-only** `Subcontractor Bill` doctype (no GL, cost-code lines, `SB-` series). The UI
prototype (`buildsuite-core-demo`) has since moved to a **PI-generating** bill: on submit it
produces a real ERPNext **Purchase Invoice** (payable, retention, taxes, TDS), with a full
billing waterfall, separate **Payment Entries**, and Cancel. There is no Vue screen yet — the
workspace only links out to Desk.

This pass brings the real app in line with the prototype: rework the doctype to generate a real
PI on submit, and build the Vue frontend. Taxes stay **country-agnostic** — the bill picks a
tax template and the PI (plus India Compliance, if installed) does the authoritative posting;
no GST is hard-coded (confirmed by cloning India Compliance: its transaction logic is
server-side `doc_events` on Purchase Invoice, so a generated PI inherits GST/TDS automatically).

**Decisions (confirmed with user):**
- **Scope = Core + Payment.** Create/edit (WO + Direct modes), Submit→PI, list/detail with the
  waterfall, Record Payment, Cancel. **Defer Amend** and the ERPNext-shell GL surface views.
- **Auto-create the Supplier** from the Subcontractor on first submit when none is linked.
- **Native submittable** Draft→Submitted (docstatus) — no certification workflow.
- Keep the doctype in **BuildSuite Core** module and the **`SB-.YYYY.-.#####`** series (avoid a
  disruptive module/series migration on the existing doctype).
- **Addendum:** generalize the Subcontractor's `gstin`/`pan` to country-neutral tax-id fields.

## Backend

### 1. Doctype: `Subcontractor Bill` (extend the existing JSON)
- `work_order` → make **optional**; add `is_direct` (Check) to flag direct bills.
- **Billing block** (new fields): `bill_type` (Select: Normal/Final, default Normal),
  `taxes_and_charges` (Link → Purchase Taxes and Charges Template), `tax_category` (Link → Tax
  Category), `taxes` (Table → **new** `Subcontractor Bill Tax`), `apply_tds` (Check),
  `tax_withholding_category` (Link → Tax Withholding Category), `additional_discount_on`
  (Select: Net Total/Grand Total), `additional_discount_percentage` (Percent), `discount_amount`
  (Currency), `advance_recovery` (Currency).
- **Computed totals** (read_only): keep `gross`; add `taxable_value`, `total_taxes`,
  `grand_total`, `tds_amount`, `invoice_value`; keep `retention_amount`, `net_payable`.
- `purchase_invoice` (Link → Purchase Invoice, read_only, no_copy). Keep `status`, `amended_from`.
- **New child `Subcontractor Bill Tax`** (istable): `charge_type` (Select, default "On Net
  Total"), `account_head` (Data/Link Account), `rate` (Float), `tax_amount` (Currency, read_only).
- `Subcontractor Bill Line`: make `scope` + `this_period_amount` writable and `cost_code_*`,
  `rate`, qty fields nullable so **Direct** lines (free text + amount) reuse the same table.

### 2. Controller `subcontractor_bill.py`
- `validate()` — mode-aware. Compute the waterfall exactly per prototype
  `_recomputeBillTotals`: `gross = Σ line.this_period_amount`; taxable = gross − (Net-Total
  discount); per-tax `tax_amount = taxable × rate/100`; `grand_total = taxable + Σ taxes`;
  `invoice_value = grand_total − (Grand-Total discount)`; `tds_amount = taxable × tds_rate/100`
  when `apply_tds`; `retention_amount = taxable × retention_percent/100`;
  `net_payable = invoice_value − tds − retention − advance_recovery`. Assign `ra_no`; sync
  `status` from docstatus; keep the open-WO guard for WO bills.
- `@frappe.whitelist() fetch_lines()` — WO mode: reuse
  `api/subcontract.get_wo_measurements()['measured_by_line']` + a new
  `previously_billed_by_line(work_order)` (Σ submitted bills' `this_period_qty` per WO line);
  `this_period_qty = max(0, measured − previous)`.
- `on_submit()` — **generate the PI** (idempotent: skip if `purchase_invoice` set; atomic: any
  failure raises → Frappe rolls the submit back):
  1. Resolve the Supplier: `subcontractor.supplier`, else **auto-create** an ERPNext Supplier
     (name, tax ids) and link it back on the Subcontractor.
  2. Resolve accounts + service item from settings (seeded, below).
  3. `frappe.new_doc("Purchase Invoice")`: `supplier`, `project`, `posting_date=date`,
     `bill_no`/`bill_date`, `update_stock=0`, `set_posting_time=1`; one **item row per bill
     line** → the service Item, `description = line.scope`, `qty`, `rate`(or amount), full
     line amount to `expense_account = Subcontractor Charges`, `project`, `cost_center`.
  4. **Taxes**: copy `taxes[]` rows into PI `taxes` (charge_type, account_head, rate). Retention
     → a PI tax row `add_deduct_tax=Deduct`, `account_head=Retention Payable`,
     `tax_amount=retention_amount` (Normal); **Final** bills instead `Add` back retention held on
     prior bills. Advance → `Deduct` row to the advance account. Discount → PI
     `apply_discount_on` + `additional_discount_percentage`/`discount_amount`. TDS → set
     `apply_tds=1` + `tax_withholding_category` (ERPNext computes it on submit).
  5. `pi.insert(); pi.submit()`; set `self.purchase_invoice = pi.name` and the PI's
     `subcontractor_bill` custom field.
- `on_cancel()` — cancel the linked PI (guard: no allocated Payment Entries), then sync status.

### 3. Custom field on Purchase Invoice
- `subcontractor_bill` (Link → Subcontractor Bill, read_only) via a custom-field seed
  (`create_custom_fields`) run in install/after-migrate — mirrors how India Compliance adds
  its fields.

### 4. One-time setup seeds (idempotent) — new `doctype/subcontractor_bill/seed_bill.py`
- Service **Item** "Subcontractor Work" (`is_stock_item=0`, Item Group "Subcontract",
  default expense = Subcontractor Charges).
- **Accounts** per company: "Retention Payable" (Current Liability), "Subcontractor Charges"
  (Expense Account), "Supplier Advance" if needed — auto-create under the right parent if absent.
- Store the three names in **BuildSuite Core Settings** (new fields) so PI generation resolves
  them. Wire into `install.py::seed_master_data()` and the `after_migrate` hook.

### 5. Whitelisted API — new `buildsuite_core/api/subcontractor_bill.py`
Mirror `api/subcontract.py`'s `call()`/serialize conventions:
`get_bill(name)`, `save_bill(payload)` (both modes; JSON child tables), `fetch_bill_lines`,
`get_wo_bill_context(work_order)` (WO + measured/previous + retention%), `submit_bill(name)`
(returns `{status, purchase_invoice}`), `cancel_bill(name)`, `delete_bill(name)`,
`list_tax_templates()` + `get_tax_template_rows(template)` (**dynamic**, from Purchase Taxes and
Charges Template — not hard-coded), `list_withholding_categories()`, `record_payment(name, …)`
(create+submit a **Payment Entry**, party_type Supplier, allocated to the PI),
`bill_payment_summary(name)` (read-through PI `outstanding_amount`/`status`).

### 6. Permissions
`SUBCONTRACT_BILL_ROLE_PERMS` is already wired in `permissions/setup.py`. No change beyond
confirming Accountant read + `_BILL_FULL_ROLES` submit; standard Payment Entry perms apply.

## Frontend (real Vue SPA — `buildsuite_core/frontend/src`)
- `data/subcontractApi.js` — add bill + payment wrappers (same `call()` pattern).
- **Views** (port from prototype, using `DeskPage`/`DeskList`/`StatusBadge`/`fmtINR`/`fmtDate`):
  - `SubcontractorBillsListView.vue` — `useDocTypeList("Subcontractor Bill", {pageLength:0})`.
  - `NewSubcontractorBillView.vue` — mode toggle (From Work Order / Direct); WO mode pulls
    read-only MB-derived lines via `fetch_bill_lines`; Direct mode = editable free-text lines.
  - `SubcontractorBillDetailView.vue` — summary strip, lines, **Taxes & Charges editor**
    (template picker → editable `taxes[]`), TDS/discount/retention/advance inputs, live
    **waterfall**, Submit (confirm → PI ref banner), Cancel, and a **Payment** panel
    (outstanding read-through + Record Payment).
- `router/index.js` — add `subcontractor-bills` list/new/`:id`/`:id/edit` routes.
- Tax templates + TDS categories fetched **dynamically** (no hard-coded GST list).
- `workspaces/SubcontractWorkspace.vue` — change the "RA Bills" shortcut from the Desk `href`
  to the Vue route; rename to **"Subcontractor Bills"**.
- `SubcontractorWorkOrderDetailView.vue` — "Raise Bill" → Vue route (RouterLink, not Desk).
- `cd frontend && yarn build` + `bench --site bs.local clear-cache`.

## Addendum — country-neutral tax-id fields on Subcontractor
Rename `gstin` → `tax_id` (label "Tax ID", description "e.g. GSTIN (India)") and `pan` →
`secondary_tax_id` (label "Secondary Tax ID", description "e.g. PAN (India)"); keep both as free
`Data`. Add a rename **patch** (`frappe.reload_doc` + `rename_field`) to migrate existing values.
On Supplier auto-create, map `tax_id`→Supplier `tax_id`/`gstin` and `secondary_tax_id`→`pan`
(only if those custom fields exist). Update the Subcontractor Vue form + `New/DetailView`
labels. (Exact field names to confirm — flagged for a quick check before writing the patch.)

## Tests (`buildsuite_core/tests/`)
- WO bill submit → PI created; retention posts as a Deduct row to Retention Payable; amounts
  match the waterfall. Idempotent re-submit. Cancel → PI cancelled. Direct-mode bill.
- Supplier auto-create path. `previously_billed_by_line` rollup (RA-2 sees RA-1 qty).
- Record Payment → PI `outstanding_amount` drops. Permission smoke (Accountant read, QS full).
- Update any existing `subcontractor_bill` tests for the new fields.

## Verification
1. `bench --site bs.local migrate` → doctype + child + custom field sync; seeds present.
2. Desk/Vue: new WO bill → fetch lines → pick "GST 18%" template → waterfall shows tax +
   retention → **Submit** → PI generated, retention Deduct row present, bill locked.
3. Second bill on the same WO → `previous_qty` reflects RA-1.
4. Direct bill with two free-text lines → submit → PI with those lines.
5. Record Payment → outstanding drops; Cancel a bill → PI cancelled.
6. `yarn build` clean; `make test` green (existing + new).
