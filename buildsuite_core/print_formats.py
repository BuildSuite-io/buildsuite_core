# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Custom Frappe Print Formats for Sales Invoice + Subcontractor Work Order, reproducing the
prototype's document layouts, and seeded as each doctype's DEFAULT so the SPA's server-rendered
print view (ServerPrintDocument → meta.default_print_format) picks them up with no code change.

Jinja templates over `doc`; Frappe prepends the company Letter Head, so these author only the body.
CSS is scoped under `.bs-print` so it never leaks into the SPA it's injected into. Seeded (upsert)
on install/migrate so the format stays in step with this code."""

import frappe

MODULE = "BuildSuite Core"

_SHARED_CSS = """
.bs-print { color: #0f172a; font-size: 10pt; line-height: 1.4; }
.bs-print .muted { color: #64748b; }
.bs-print .small { font-size: 8.5pt; }
.bs-print .bold { font-weight: 600; }
.bs-print .r { text-align: right; }
.bs-print .l { text-align: left; }
.bs-print .nums { font-variant-numeric: tabular-nums; }
.bs-print .mono { font-family: monospace; font-size: 9pt; }
.bs-print .bs-label { font-size: 8pt; text-transform: uppercase; letter-spacing: 0.06em; color: #64748b; font-weight: 600; margin-bottom: 2px; }
.bs-print .bs-title-row { display: flex; align-items: flex-start; justify-content: space-between; padding-bottom: 10px; border-bottom: 2px solid #cbd5e1; margin-bottom: 16px; }
.bs-print .bs-doc-title { font-size: 16pt; font-weight: 700; letter-spacing: 0.04em; }
.bs-print .bs-doc-ref { text-align: right; font-size: 9pt; }
.bs-print .bs-marker { font-size: 8pt; font-weight: 700; text-transform: uppercase; letter-spacing: 0.1em; margin-top: 2px; }
.bs-print .bs-marker.draft { color: #b45309; }
.bs-print .bs-marker.cancelled { color: #b91c1c; }
.bs-print table.bs-lines { width: 100%; border-collapse: collapse; margin-bottom: 16px; }
.bs-print table.bs-lines th { font-size: 8pt; text-transform: uppercase; letter-spacing: 0.05em; color: #64748b; padding: 6px 8px; border-top: 1px solid #cbd5e1; border-bottom: 1px solid #cbd5e1; }
.bs-print table.bs-lines td { padding: 6px 8px; border-bottom: 1px solid #e2e8f0; vertical-align: top; }
.bs-print table.bs-lines.bordered { border: 1px solid #e2e8f0; border-radius: 8px; }
.bs-print table.bs-lines.bordered th { background: #f8fafc; border-top: none; }
.bs-print table.bs-lines tfoot td { border-top: 2px solid #cbd5e1; background: #f8fafc; font-weight: 600; padding: 7px 8px; }
.bs-print .foot-label { font-size: 8pt; text-transform: uppercase; letter-spacing: 0.05em; color: #334155; }
.bs-print .bs-totals-wrap { display: flex; justify-content: flex-end; margin-bottom: 24px; }
.bs-print .bs-totals { width: 300px; font-size: 9.5pt; }
.bs-print .bs-totals .row { display: flex; justify-content: space-between; padding: 2px 0; color: #475569; }
.bs-print .bs-totals .row.grand { border-top: 1px solid #cbd5e1; padding-top: 6px; margin-top: 4px; color: #0f172a; font-weight: 600; }
.bs-print .bs-totals .due { color: #b91c1c; font-weight: 600; }
.bs-print .bs-totals .paid { color: #15803d; font-weight: 600; }
.bs-print .bs-terms-text { font-size: 9pt; color: #475569; line-height: 1.5; white-space: pre-line; }
.bs-print .bs-sign { display: grid; grid-template-columns: 1fr 1fr; gap: 48px; margin-top: 8px; }
.bs-print .bs-sign .sig { border-top: 1px solid #94a3b8; padding-top: 6px; margin-top: 36px; font-size: 9pt; color: #475569; }
.bs-print .bs-footer { text-align: center; font-size: 8pt; color: #94a3b8; padding-top: 10px; border-top: 1px solid #e2e8f0; margin-top: 20px; }
/* A priced offer — quotation or tender — leads with the job it is for, so the title
   carries the page and the figures the reader checks first sit in a strip under it. */
.bs-print .bs-offer-title { background: #0f172a; color: #ffffff; padding: 18px 20px; border-radius: 6px 6px 0 0; font-size: 17pt; font-weight: 600; line-height: 1.25; }
.bs-print .bs-offer-title .ref { font-size: 8pt; text-transform: uppercase; letter-spacing: 0.18em; color: rgba(255,255,255,0.7); margin-bottom: 4px; }
.bs-print .bs-strip { display: flex; border: 1px solid #e2e8f0; border-top: none; border-radius: 0 0 6px 6px; margin-bottom: 20px; }
.bs-print .bs-strip > div { flex: 1; padding: 10px 18px; border-right: 1px solid #e2e8f0; }
.bs-print .bs-strip > div:last-child { border-right: none; }
.bs-print .bs-strip .val { font-weight: 600; font-size: 11pt; margin-top: 4px; }
.bs-print .bs-lh { flex: 1; min-width: 0; }
.bs-print .bs-lh > div { border-bottom: none !important; padding-bottom: 0 !important; }
"""

_INVOICE_CSS = _SHARED_CSS + """
.bs-print .bs-meta { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; margin-bottom: 20px; }
.bs-print .bs-meta .bs-name { font-size: 10.5pt; font-weight: 600; }
.bs-print table.bs-kv { width: 100%; font-size: 9pt; }
.bs-print table.bs-kv td { padding: 1px 0; color: #475569; }
.bs-print .bs-terms { margin-bottom: 28px; }
.bs-print .bs-sign .c.r { text-align: right; }
"""

_INVOICE_HTML = """
<div class="bs-print">
  <div class="bs-title-row">
    <div>
      <div class="bs-doc-title">TAX INVOICE</div>
      {% if doc.docstatus == 0 %}<div class="bs-marker draft">Draft — not posted</div>
      {% elif doc.docstatus == 2 %}<div class="bs-marker cancelled">Cancelled</div>{% endif %}
    </div>
    <div class="bs-doc-ref"><span class="mono">{{ doc.name }}</span></div>
  </div>

  <div class="bs-meta">
    <div>
      <div class="bs-label">Bill to</div>
      <div class="bs-name">{{ doc.customer_name or doc.customer }}</div>
      {% if doc.tax_id %}<div class="mono muted">GSTIN: {{ doc.tax_id }}</div>{% endif %}
    </div>
    <div>
      <table class="bs-kv">
        <tr><td>Invoice no.</td><td class="r mono">{{ doc.name }}</td></tr>
        <tr><td>Invoice date</td><td class="r">{{ frappe.utils.formatdate(doc.posting_date) }}</td></tr>
        {% if doc.due_date %}<tr><td>Due date</td><td class="r">{{ frappe.utils.formatdate(doc.due_date) }}</td></tr>{% endif %}
        {% if doc.project %}<tr><td>Project</td><td class="r">{{ frappe.db.get_value("Project", doc.project, "project_name") or doc.project }}</td></tr>{% endif %}
      </table>
    </div>
  </div>

  <table class="bs-lines">
    <thead><tr><th class="l" style="width:24px">#</th><th class="l">Description</th><th class="r" style="width:64px">Qty</th><th class="r" style="width:90px">Rate</th><th class="r" style="width:110px">Amount</th></tr></thead>
    <tbody>
      {% for item in doc.items %}
      <tr>
        <td class="muted">{{ loop.index }}</td>
        <td>{{ item.item_name or item.description }}</td>
        <td class="r nums muted">{{ item.get_formatted("qty") }}</td>
        <td class="r nums muted">{{ item.get_formatted("rate") }}</td>
        <td class="r nums">{{ item.get_formatted("amount") }}</td>
      </tr>
      {% endfor %}
    </tbody>
  </table>

  <div class="bs-totals-wrap">
    <div class="bs-totals">
      <div class="row"><span>Net total</span><span class="nums">{{ doc.get_formatted("net_total") }}</span></div>
      {% if doc.discount_amount %}<div class="row"><span>Discount</span><span class="nums">− {{ doc.get_formatted("discount_amount") }}</span></div>{% endif %}
      {% for tax in doc.taxes %}<div class="row"><span>{{ tax.description }}</span><span class="nums">{{ tax.get_formatted("tax_amount") }}</span></div>{% endfor %}
      <div class="row grand"><span>Invoice total</span><span class="nums">{{ doc.get_formatted("grand_total") }}</span></div>
      {% if doc.docstatus == 1 %}
      <div class="row"><span>Received</span><span class="nums">{{ frappe.utils.fmt_money(doc.grand_total - doc.outstanding_amount, currency=doc.currency) }}</span></div>
      <div class="row {{ 'due' if doc.outstanding_amount > 0.01 else 'paid' }}"><span>Balance due</span><span class="nums">{{ doc.get_formatted("outstanding_amount") }}</span></div>
      {% endif %}
    </div>
  </div>

  <div class="bs-terms">
    <div class="bs-label">Terms</div>
    {% if doc.terms %}<div class="bs-terms-text">{{ doc.terms }}</div>
    {% else %}<div class="bs-terms-text">Payment due by {{ frappe.utils.formatdate(doc.due_date) }}. Interest may be charged on overdue amounts as per contract. This is a computer-generated invoice.</div>{% endif %}
  </div>

  <div class="bs-sign">
    <div class="c"><div class="sig">Prepared by</div></div>
    <div class="c r"><div class="sig">For {{ doc.company }} — Authorised signatory</div></div>
  </div>
</div>
"""

_WO_CSS = _SHARED_CSS + """
.bs-print .bs-parties { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 20px; }
.bs-print .bs-party { border: 1px solid #e2e8f0; border-radius: 8px; padding: 14px; }
.bs-print .bs-party .bs-name { font-size: 10.5pt; font-weight: 600; }
.bs-print .bs-metastrip { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 20px; font-size: 9pt; }
.bs-print .bs-h2 { font-size: 9pt; font-weight: 600; text-transform: uppercase; letter-spacing: 0.06em; color: #334155; margin-bottom: 6px; }
.bs-print .bs-h3 { font-size: 9pt; font-weight: 600; text-transform: uppercase; letter-spacing: 0.06em; color: #334155; margin-bottom: 6px; }
.bs-print .bs-wo-footer { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin: 16px 0 24px; }
.bs-print .bs-wo-totals { border: 1px solid #e2e8f0; border-radius: 8px; padding: 14px; font-size: 9.5pt; height: fit-content; }
.bs-print .bs-wo-totals .row { display: flex; justify-content: space-between; padding: 3px 0; color: #475569; }
.bs-print .bs-wo-totals .row.grand { border-top: 1px solid #e2e8f0; padding-top: 6px; margin-top: 4px; color: #0f172a; font-weight: 600; }
.bs-print .bs-wo-totals .due { color: #b91c1c; }
.bs-print .bs-terms-list { font-size: 9pt; color: #475569; padding-left: 16px; line-height: 1.5; }
"""

_WO_HTML = """
<div class="bs-print">
  <div class="bs-title-row">
    <div><div class="bs-doc-title">WORK ORDER</div></div>
    <div class="bs-doc-ref"><span class="bold">{{ doc.name }}</span><br><span class="muted">{{ frappe.utils.formatdate(doc.date) }}</span></div>
  </div>

  {% set gstin = frappe.db.get_value("Supplier", doc.subcontractor, "tax_id") %}
  <div class="bs-parties">
    <div class="bs-party">
      <div class="bs-label">Issued by</div>
      <div class="bs-name">{{ doc.company }}</div>
    </div>
    <div class="bs-party">
      <div class="bs-label">To — Subcontractor</div>
      <div class="bs-name">{{ doc.subcontractor_name or doc.subcontractor }}</div>
      {% if gstin %}<div class="muted small" style="margin-top:4px">GSTIN: {{ gstin }}</div>{% endif %}
    </div>
  </div>

  {% set proj = frappe.db.get_value("Project", doc.project, ["project_name", "customer", "location"], as_dict=True) or {} %}
  <div class="bs-metastrip">
    <div><div class="bs-label">Against project</div><div class="bold">{{ proj.project_name or doc.project or "—" }}</div>{% if proj.location %}<div class="muted">{{ proj.location }}</div>{% endif %}</div>
    <div><div class="bs-label">Client</div><div class="bold">{{ proj.customer or "—" }}</div></div>
    <div><div class="bs-label">Delivery type</div><div class="bold">{{ doc.delivery_type or "—" }}</div></div>
    <div><div class="bs-label">Retention</div><div class="bold">{{ doc.retention_percent or 0 }}%</div></div>
  </div>

  <div class="bs-h2">Schedule of values</div>
  <table class="bs-lines bordered">
    <thead><tr><th class="l" style="width:24px">#</th><th class="l">Scope of work</th><th class="l">Cost code</th><th class="r" style="width:56px">Qty</th><th class="l" style="width:56px">UOM</th><th class="r" style="width:90px">Rate</th><th class="r" style="width:110px">Amount</th></tr></thead>
    <tbody>
      {% for line in doc.lines %}
      <tr>
        <td class="muted">{{ loop.index }}</td>
        <td>{{ line.scope }}</td>
        <td class="muted">{{ line.cost_code_label or "—" }}</td>
        <td class="r nums">{{ line.qty }}</td>
        <td>{{ line.uom }}</td>
        <td class="r nums">{{ line.get_formatted("rate") }}</td>
        <td class="r nums bold">{{ line.get_formatted("amount") }}</td>
      </tr>
      {% endfor %}
    </tbody>
    <tfoot><tr><td colspan="6" class="r foot-label">Total order value</td><td class="r nums bold">{{ doc.get_formatted("total_value") }}</td></tr></tfoot>
  </table>

  {% set currency = frappe.db.get_value("Company", doc.company, "default_currency") %}
  {% set retention = (doc.total_value or 0) * (doc.retention_percent or 0) / 100.0 %}
  <div class="bs-wo-footer">
    <div>
      <div class="bs-h3">Terms &amp; conditions</div>
      {% if doc.terms %}<div class="bs-terms-text">{{ doc.terms }}</div>
      {% else %}<ul class="bs-terms-list">
        <li>Progress billing is measurement-based: certified Measurement Books drive each subcontractor bill.</li>
        <li>Retention of {{ doc.retention_percent or 0 }}% is withheld on each bill, released after completion and defect-liability sign-off.</li>
      </ul>{% endif %}
    </div>
    <div class="bs-wo-totals">
      <div class="row"><span>Total order value</span><span class="nums">{{ doc.get_formatted("total_value") }}</span></div>
      <div class="row"><span>Retention ({{ doc.retention_percent or 0 }}%)</span><span class="nums due">− {{ frappe.utils.fmt_money(retention, currency=currency) }}</span></div>
      <div class="row grand"><span>Net of retention</span><span class="nums">{{ frappe.utils.fmt_money((doc.total_value or 0) - retention, currency=currency) }}</span></div>
    </div>
  </div>

  <div class="bs-sign">
    <div class="c"><div class="sig">For {{ doc.company }}</div><div class="muted small">Authorised signatory · Date</div></div>
    <div class="c"><div class="sig">For {{ doc.subcontractor_name or doc.subcontractor }}</div><div class="muted small">Accepted · Date</div></div>
  </div>
</div>
"""

# The customer's copy. It prints `rate` — what they are asked to pay. `price_list_rate` is our
# own cost and must never appear here.
_QUOTATION_HTML = """
<div class="bs-print">
  <div class="bs-title-row">
    <div class="bs-lh">{% if letter_head and not no_letterhead %}{{ letter_head }}{% endif %}</div>
    <div class="bs-doc-ref">
      <div class="bs-doc-title">QUOTATION</div>
      <div class="bold">{{ doc.name }}</div>
      <div class="muted">{{ frappe.utils.formatdate(doc.transaction_date) }}</div>
    </div>
  </div>

  <div class="bs-offer-title">{{ doc.title or doc.name }}</div>
  <div class="bs-strip">
    <div>
      <div class="bs-label">For</div>
      <div class="val">{{ doc.customer_name or doc.party_name }}</div>
      {% if doc.tax_id %}<div class="mono muted">{{ doc.tax_id }}</div>{% endif %}
    </div>
    <div>
      <div class="bs-label">Dated</div>
      <div class="val">{{ frappe.utils.formatdate(doc.transaction_date) }}</div>
    </div>
    <div>
      <div class="bs-label">Valid until</div>
      <div class="val">{{ frappe.utils.formatdate(doc.valid_till) if doc.valid_till else "&mdash;" }}</div>
    </div>
    <div>
      <div class="bs-label">Total</div>
      <div class="val">{{ doc.get_formatted("grand_total") }}</div>
    </div>
  </div>

  <div class="bs-label">Schedule of prices</div>
  <table class="bs-lines bordered">
    <thead><tr><th class="l" style="width:24px">#</th><th class="l">Description</th><th class="r" style="width:64px">Qty</th><th class="l" style="width:64px">Unit</th><th class="r" style="width:90px">Rate</th><th class="r" style="width:110px">Amount</th></tr></thead>
    <tbody>
      {% for item in doc.items %}
      <tr>
        <td class="muted">{{ loop.index }}</td>
        <td>{{ item.item_name or item.description }}</td>
        <td class="r nums muted">{{ item.get_formatted("qty") }}</td>
        <td class="muted">{{ item.uom or "" }}</td>
        <td class="r nums muted">{{ item.get_formatted("rate") }}</td>
        <td class="r nums">{{ item.get_formatted("amount") }}</td>
      </tr>
      {% endfor %}
    </tbody>
  </table>

  <div class="bs-totals-wrap">
    <div class="bs-totals">
      <div class="row"><span>Price</span><span class="nums">{{ doc.get_formatted("net_total") }}</span></div>
      {% for tax in doc.taxes %}
      <div class="row"><span>{{ tax.description }}</span><span class="nums">{{ tax.get_formatted("tax_amount") }}</span></div>
      {% endfor %}
      <div class="row grand"><span>Total</span><span class="nums">{{ doc.get_formatted("grand_total") }}</span></div>
    </div>
  </div>

  {% if doc.terms %}
  <div class="bs-label">Terms &amp; conditions</div>
  <div class="bs-terms-text">{{ doc.terms }}</div>
  {% endif %}

  <div class="bs-sign">
    <div class="c"><div class="sig">For {{ doc.company }}</div></div>
    <div class="c"><div class="sig">Accepted for {{ doc.customer_name or doc.party_name }}</div></div>
  </div>

  <div class="bs-footer">Generated using <span class="bold">BuildSuite</span></div>
</div>
"""

# The bid as the issuing body reads it. Lines print `sell_rate` — what we are bidding.
# `rate` is our cost, and `notes` is the internal note; neither leaves the building.
# BuildSuite Tenders carries no `company` field, so api.printing falls back to the is_default
# Letter Head rather than resolving one per company. Correct for a bid, just not per-company.
_TENDER_HTML = """
<div class="bs-print">
  <div class="bs-title-row">
    <div class="bs-lh">{% if letter_head and not no_letterhead %}{{ letter_head }}{% endif %}</div>
    <div class="bs-doc-ref">
      <div class="bs-doc-title">TENDER</div>
      <div class="bold">{{ doc.name }}</div>
      <div class="muted">{{ frappe.utils.formatdate(doc.date_issued) if doc.date_issued else "" }}</div>
    </div>
  </div>

  <div class="bs-offer-title">
    {% if doc.tender_reference %}<div class="ref">{{ doc.tender_reference }}</div>{% endif %}
    {{ doc.title or doc.name }}
  </div>
  <div class="bs-strip">
    <div>
      <div class="bs-label">Submitted to</div>
      <div class="val">{{ doc.issuing_body or "&mdash;" }}</div>
    </div>
    <div>
      <div class="bs-label">Submission deadline</div>
      <div class="val">{{ frappe.utils.formatdate(doc.submission_deadline) if doc.submission_deadline else "&mdash;" }}</div>
    </div>
    <div>
      <div class="bs-label">Envelope</div>
      <div class="val">{{ doc.envelope_structure or "&mdash;" }}</div>
    </div>
    <div>
      <div class="bs-label">Bid total</div>
      <div class="val">{{ doc.get_formatted("bid_value") }}</div>
    </div>
  </div>

  {% for s in doc.preamble_sections %}
    <div class="bs-label">{{ s.heading }}</div>
    <div class="bs-terms-text" style="margin-bottom:16px;">{{ s.text }}</div>
  {% endfor %}

  <div class="bs-label">Schedule of prices</div>
  <table class="bs-lines bordered">
    <thead><tr><th class="l" style="width:24px">#</th><th class="l">Description</th><th class="r" style="width:64px">Qty</th><th class="l" style="width:64px">Unit</th><th class="r" style="width:90px">Rate</th><th class="r" style="width:110px">Amount</th></tr></thead>
    <tbody>
      {% for item in doc.buildsuite_tenders_items %}
      <tr>
        <td class="muted">{{ loop.index }}</td>
        <td>{{ item.description }}</td>
        <td class="r nums muted">{{ item.get_formatted("qty") }}</td>
        <td class="muted">{{ item.unit or "" }}</td>
        <td class="r nums muted">{{ item.get_formatted("sell_rate") }}</td>
        <td class="r nums">{{ item.get_formatted("amount") }}</td>
      </tr>
      {% endfor %}
    </tbody>
  </table>

  <div class="bs-totals-wrap">
    <div class="bs-totals">
      <div class="row"><span>Price</span><span class="nums">{{ doc.get_formatted("bid_before_tax") }}</span></div>
      {% if doc.tax_percent %}<div class="row"><span>Tax @ {{ doc.tax_percent }}%</span><span class="nums">{{ doc.get_formatted("tax_amount") }}</span></div>{% endif %}
      <div class="row grand"><span>Bid total</span><span class="nums">{{ doc.get_formatted("bid_value") }}</span></div>
    </div>
  </div>

  {% if doc.emd_amount or doc.performance_guarantee_percent %}
  <div class="bs-label">Earnest money and guarantee</div>
  <div class="bs-terms-text" style="margin-bottom:16px;">
    {% if doc.emd_amount %}<div>Earnest money deposit: {{ doc.get_formatted("emd_amount") }}{% if doc.emd_instrument %} &mdash; {{ doc.emd_instrument }}{% endif %}{% if doc.emd_valid_until %}, valid to {{ frappe.utils.formatdate(doc.emd_valid_until) }}{% endif %}</div>{% endif %}
    {% if doc.performance_guarantee_percent %}<div>Performance guarantee: {{ doc.performance_guarantee_percent }}% of the contract value ({{ frappe.utils.fmt_money((doc.bid_before_tax or 0) * (doc.performance_guarantee_percent | float) / 100, currency=frappe.defaults.get_global_default("currency")) }}), to be furnished on award.</div>{% endif %}
  </div>
  {% endif %}

  {% for s in doc.terms_sections %}
    <div class="bs-label">{{ s.heading }}</div>
    <div class="bs-terms-text" style="margin-bottom:16px;">{{ s.text }}</div>
  {% endfor %}

  <div class="bs-sign">
    <div class="c"><div class="sig">For {{ frappe.defaults.get_user_default("Company") or "" }}</div></div>
    <div class="c"><div class="sig">Received for {{ doc.issuing_body or "" }}</div></div>
  </div>

  <div class="bs-footer">Generated using <span class="bold">BuildSuite</span></div>
</div>
"""

_FORMATS = (
	{"name": "BuildSuite Tax Invoice", "doc_type": "Sales Invoice", "html": _INVOICE_HTML, "css": _INVOICE_CSS},
	{"name": "BuildSuite Work Order", "doc_type": "Subcontractor Work Order", "html": _WO_HTML, "css": _WO_CSS},
	{"name": "BuildSuite Quotation", "doc_type": "Quotation", "html": _QUOTATION_HTML, "css": _SHARED_CSS},
	{"name": "BuildSuite Tender", "doc_type": "BuildSuite Tenders", "html": _TENDER_HTML, "css": _SHARED_CSS},
)


def seed_print_formats():
	"""Upsert the two custom print formats and set each as its doctype's default_print_format so the
	SPA's print view picks them up. Idempotent; keeps the format in step with this code on migrate."""
	for pf in _FORMATS:
		if not frappe.db.exists("DocType", pf["doc_type"]):
			continue
		if frappe.db.exists("Print Format", pf["name"]):
			doc = frappe.get_doc("Print Format", pf["name"])
		else:
			doc = frappe.new_doc("Print Format")
			doc.name = pf["name"]
		doc.update(
			{
				"doc_type": pf["doc_type"],
				"module": MODULE,
				"print_format_type": "Jinja",
				"custom_format": 1,
				"standard": "No",
				"disabled": 0,
				"html": pf["html"],
				"css": pf["css"],
			}
		)
		doc.flags.ignore_permissions = True
		doc.save()
		# Make it the doctype's default so ServerPrintDocument (meta.default_print_format) uses it.
		frappe.make_property_setter(
			{
				"doctype": pf["doc_type"],
				"doctype_or_field": "DocType",
				"property": "default_print_format",
				"value": pf["name"],
				"property_type": "Data",
			},
			is_system_generated=True,
		)
