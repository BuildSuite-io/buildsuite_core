# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Seed the print assets for the Subcontract module: a default Letter Head (company
branding) and the Subcontractor Work Order Print Format (Jinja). Kept split per the
Frappe convention — the letter head carries generic branding, and the work-order
identity (number, date, status) lives in the print-format body. Idempotent."""

import base64

import frappe

LETTER_HEAD = "BuildSuite Standard"
WO_PRINT_FORMAT = "Subcontractor Work Order"
PO_PRINT_FORMAT = "Purchase Order"

# The one branding record every printed surface renders (docs + reports, via the
# frontend get_letter_head() endpoint and the server print engine). Editing this
# record later re-flows the new branding everywhere. GSTIN is fictional demo data.


def _logo_data_uri():
	"""Embed the logo as a data URI so it renders identically in the browser
	(report v-html + window.print) and in wkhtmltopdf server-PDF — no URL to resolve."""
	path = frappe.get_app_path("buildsuite_core", "public", "images", "buildsuite-logo.png")
	try:
		with open(path, "rb") as fh:
			return "data:image/png;base64," + base64.b64encode(fh.read()).decode("ascii")
	except OSError:
		return ""


def _letter_head_html():
	logo = _logo_data_uri()
	logo_el = (
		f'<img src="{logo}" alt="BuildSuite" style="width:48px; height:48px; border-radius:8px; object-fit:contain; flex-shrink:0;" />'
		if logo
		else '<div style="width:48px; height:48px; border:1px dashed #cbd5e1; border-radius:8px; display:flex; align-items:center; justify-content:center; font-size:9px; color:#94a3b8;">LOGO</div>'
	)
	return f"""
<div style="display:flex; align-items:center; gap:12px; padding:4px 0;">
	{logo_el}
	<div>
		<div style="font-size:18px; font-weight:600; color:#0f172a;">BuildSuite</div>
		<div style="font-size:11px; color:#64748b;">Registered office address, City &middot; GSTIN 1234567</div>
	</div>
</div>
"""

# Jinja/HTML body for the Subcontractor Work Order. The letter head is prepended by
# the print engine; this template is the document body only.
_WO_PRINT_HTML = """
<style>
	.wo-print { font-family: -apple-system, "Segoe UI", Roboto, sans-serif; color:#1e293b; font-size:12px; }
	.wo-print .muted { color:#64748b; }
	.wo-print .label { font-size:10px; text-transform:uppercase; letter-spacing:0.06em; color:#64748b; }
	.wo-print .right { text-align:right; }
	.wo-title-row { display:flex; justify-content:space-between; align-items:flex-start;
		border-bottom:2px solid #cbd5e1; padding-bottom:12px; margin-bottom:16px; }
	.wo-title { font-size:20px; font-weight:700; letter-spacing:1px; }
	.parties { display:flex; gap:16px; margin-bottom:16px; }
	.party { flex:1; border:1px solid #e2e8f0; border-radius:8px; padding:12px; }
	.meta { display:flex; gap:16px; margin-bottom:16px; }
	.meta > div { flex:1; }
	table.sov { width:100%; border-collapse:collapse; font-size:11px; margin-bottom:16px; }
	table.sov th, table.sov td { border:1px solid #e2e8f0; padding:6px 8px; vertical-align:top; }
	table.sov thead th { background:#f8fafc; text-transform:uppercase; font-size:9px;
		letter-spacing:0.06em; color:#64748b; text-align:left; }
	.totals { width:280px; margin-left:auto; border:1px solid #e2e8f0; border-radius:8px; padding:12px; font-size:11px; }
	.totals .row { display:flex; justify-content:space-between; padding:3px 0; }
	h3.sec { font-size:11px; text-transform:uppercase; letter-spacing:0.06em; color:#334155; margin:16px 0 6px; }
	.terms { font-size:11px; color:#475569; margin-bottom:20px; white-space:pre-line; }
	.sign { display:flex; gap:32px; margin-top:24px; }
	.sign > div { flex:1; }
	.sign .line { border-top:1px solid #94a3b8; padding-top:6px; margin-top:40px; font-size:11px; }
	.footer { text-align:center; font-size:9px; color:#94a3b8; border-top:1px solid #f1f5f9; padding-top:8px; margin-top:16px; }
</style>

{% set sub = frappe.db.get_value("Supplier", doc.subcontractor, ["custom_trade", "tax_id"], as_dict=True) if doc.subcontractor else None %}
{% set proj = frappe.db.get_value("Project", doc.project, ["project_name", "custom_project_id", "customer", "location"], as_dict=True) if doc.project else None %}
{% set currency = frappe.db.get_value("Company", doc.company, "default_currency") if doc.company else None %}
{% set retention = (doc.total_value or 0) * (doc.retention_percent or 0) / 100.0 %}

<div class="wo-print">
	<div class="wo-title-row">
		<div>
			<div class="wo-title">WORK ORDER</div>
			<div class="muted" style="font-size:11px;">{{ doc.name }}</div>
		</div>
		<div class="right">
			<div class="muted">{{ frappe.utils.format_date(doc.date) }}</div>
			<div style="margin-top:2px; font-weight:600;">{{ {0: "Draft", 1: "Submitted", 2: "Cancelled"}.get(doc.docstatus, "Draft") }}</div>
		</div>
	</div>

	<div class="parties">
		<div class="party">
			<div class="label">Issued by</div>
			<div style="font-weight:600; margin-top:4px;">{{ doc.company or "&mdash;" }}</div>
		</div>
		<div class="party">
			<div class="label">To &mdash; Subcontractor</div>
			<div style="font-weight:600; margin-top:4px;">{{ doc.subcontractor_name or doc.subcontractor }}</div>
			{% if sub %}
				{% if sub.custom_trade %}<div class="muted">{{ sub.custom_trade }}</div>{% endif %}
				{% if sub.tax_id %}<div class="muted">Tax ID: {{ sub.tax_id }}</div>{% endif %}
			{% endif %}
		</div>
	</div>

	<div class="meta">
		<div>
			<div class="label">Against project</div>
			<div style="font-weight:500;">{{ proj.project_name if proj else doc.project }}</div>
			{% if proj and proj.custom_project_id %}<div class="muted">{{ proj.custom_project_id }}</div>{% endif %}
		</div>
		<div><div class="label">Client</div><div style="font-weight:500;">{{ proj.customer if proj and proj.customer else "&mdash;" }}</div></div>
		<div><div class="label">Delivery type</div><div style="font-weight:500;">{{ doc.delivery_type or "&mdash;" }}</div></div>
		<div><div class="label">Retention</div><div style="font-weight:500;">{{ doc.retention_percent or 0 }}%</div></div>
	</div>

	<h3 class="sec">Schedule of values</h3>
	<table class="sov">
		<thead>
			<tr>
				<th style="width:24px;">#</th>
				<th>Scope of work</th>
				<th>Cost code</th>
				<th class="right">Qty</th>
				<th>UOM</th>
				<th class="right">Rate</th>
				<th class="right">Amount</th>
			</tr>
		</thead>
		<tbody>
			{% for line in doc.lines %}
			<tr>
				<td class="muted">{{ loop.index }}</td>
				<td>{{ line.scope }}</td>
				<td class="muted">{{ line.cost_code_label or "" }}</td>
				<td class="right">{{ line.qty }}</td>
				<td>{{ line.uom or "" }}</td>
				<td class="right">{{ frappe.utils.fmt_money(line.rate, currency=currency) }}</td>
				<td class="right" style="font-weight:500;">{{ frappe.utils.fmt_money(line.amount, currency=currency) }}</td>
			</tr>
			{% endfor %}
		</tbody>
		<tfoot>
			<tr>
				<td colspan="6" class="right" style="background:#f8fafc; font-weight:600; text-transform:uppercase; font-size:9px;">Total order value</td>
				<td class="right" style="background:#f8fafc; font-weight:600;">{{ frappe.utils.fmt_money(doc.total_value, currency=currency) }}</td>
			</tr>
		</tfoot>
	</table>

	<div class="totals">
		<div class="row"><span class="muted">Total order value</span><span>{{ frappe.utils.fmt_money(doc.total_value, currency=currency) }}</span></div>
		<div class="row"><span class="muted">Retention ({{ doc.retention_percent or 0 }}%)</span><span>&minus; {{ frappe.utils.fmt_money(retention, currency=currency) }}</span></div>
		<div class="row" style="border-top:1px solid #e2e8f0; margin-top:4px; padding-top:6px; font-weight:600;">
			<span>Net of retention</span><span>{{ frappe.utils.fmt_money((doc.total_value or 0) - retention, currency=currency) }}</span>
		</div>
	</div>

	{% if doc.terms %}
	<h3 class="sec">Terms &amp; conditions</h3>
	<div class="terms">{{ doc.terms }}</div>
	{% endif %}

	<div class="sign">
		<div><div class="line">For {{ doc.company or "&mdash;" }}</div><div class="muted" style="font-size:9px;">Authorised signatory &middot; Date</div></div>
		<div><div class="line">For {{ doc.subcontractor_name or doc.subcontractor }}</div><div class="muted" style="font-size:9px;">Accepted &middot; Date</div></div>
	</div>

	<div class="footer">{{ doc.name }} &middot; Generated {{ frappe.utils.format_date(frappe.utils.nowdate()) }}</div>
</div>
"""


# Jinja/HTML body for the Purchase Order (S234 in the prototype). The letter head is
# prepended by the print engine (company branding); this is the document body only.
# ERPNext Purchase Order fields — header-level `project` is set by save_purchase_order.
_PO_PRINT_HTML = """
<style>
	.po-print { font-family: -apple-system, "Segoe UI", Roboto, sans-serif; color:#1e293b; font-size:12px; }
	.po-print .muted { color:#64748b; }
	.po-print .label { font-size:10px; text-transform:uppercase; letter-spacing:0.06em; color:#64748b; }
	.po-print .right { text-align:right; }
	.po-title-row { display:flex; justify-content:space-between; align-items:flex-start;
		border-bottom:2px solid #cbd5e1; padding-bottom:12px; margin-bottom:16px; }
	.po-title { font-size:20px; font-weight:700; letter-spacing:1px; }
	.parties { display:flex; gap:16px; margin-bottom:16px; }
	.party { flex:1; border:1px solid #e2e8f0; border-radius:8px; padding:12px; }
	.meta { display:flex; gap:16px; margin-bottom:16px; }
	.meta > div { flex:1; }
	table.items { width:100%; border-collapse:collapse; font-size:11px; margin-bottom:16px; }
	table.items th, table.items td { border:1px solid #e2e8f0; padding:6px 8px; vertical-align:top; }
	table.items thead th { background:#f8fafc; text-transform:uppercase; font-size:9px;
		letter-spacing:0.06em; color:#64748b; text-align:left; }
	h3.sec { font-size:11px; text-transform:uppercase; letter-spacing:0.06em; color:#334155; margin:16px 0 6px; }
	.terms { font-size:11px; color:#475569; margin-bottom:20px; }
	.terms ul { margin:0; padding-left:16px; }
	.terms li { margin-bottom:4px; }
	.sign { display:flex; gap:32px; margin-top:24px; }
	.sign > div { flex:1; }
	.sign .line { border-top:1px solid #94a3b8; padding-top:6px; margin-top:40px; font-size:11px; }
	.footer { text-align:center; font-size:9px; color:#94a3b8; border-top:1px solid #f1f5f9; padding-top:8px; margin-top:16px; }
</style>

{% set sup = frappe.db.get_value("Supplier", doc.supplier, ["supplier_primary_contact", "mobile_no", "email_id", "tax_id"], as_dict=True) if doc.supplier else None %}
{% set proj = frappe.db.get_value("Project", doc.project, ["project_name", "custom_project_id", "location"], as_dict=True) if doc.project else None %}
{% set currency = frappe.db.get_value("Company", doc.company, "default_currency") if doc.company else None %}

<div class="po-print">
	<div class="po-title-row">
		<div>
			<div class="po-title">PURCHASE ORDER</div>
			<div class="muted" style="font-size:11px;">{{ doc.name }}</div>
		</div>
		<div class="right">
			<div class="muted">{{ frappe.utils.format_date(doc.transaction_date) }}</div>
		</div>
	</div>

	<div class="parties">
		<div class="party">
			<div class="label">Ordered by</div>
			<div style="font-weight:600; margin-top:4px;">{{ doc.company or "&mdash;" }}</div>
		</div>
		<div class="party">
			<div class="label">To &mdash; Supplier</div>
			<div style="font-weight:600; margin-top:4px;">{{ doc.supplier_name or doc.supplier }}</div>
			{% if sup %}
				{% if sup.supplier_primary_contact %}<div class="muted">Attn: {{ sup.supplier_primary_contact }}</div>{% endif %}
				{% if sup.mobile_no or sup.email_id %}<div class="muted">{{ sup.mobile_no or "" }}{% if sup.mobile_no and sup.email_id %} &middot; {% endif %}{{ sup.email_id or "" }}</div>{% endif %}
				{% if sup.tax_id %}<div class="muted">Tax ID: {{ sup.tax_id }}</div>{% endif %}
			{% endif %}
		</div>
	</div>

	<div class="meta">
		<div>
			<div class="label">Deliver to project</div>
			<div style="font-weight:500;">{{ proj.project_name if proj else doc.project or "&mdash;" }}</div>
			{% if proj and proj.custom_project_id %}<div class="muted">{{ proj.custom_project_id }}{% if proj.location %} &middot; {{ proj.location }}{% endif %}</div>{% endif %}
		</div>
		<div><div class="label">Required by</div><div style="font-weight:500;">{{ frappe.utils.format_date(doc.schedule_date) if doc.schedule_date else "&mdash;" }}</div></div>
		<div><div class="label">Order date</div><div style="font-weight:500;">{{ frappe.utils.format_date(doc.transaction_date) }}</div></div>
	</div>

	<h3 class="sec">Order items</h3>
	<table class="items">
		<thead>
			<tr>
				<th style="width:24px;">#</th>
				<th>Item</th>
				<th class="right">Qty</th>
				<th>UOM</th>
				<th class="right">Rate</th>
				<th class="right">Amount</th>
			</tr>
		</thead>
		<tbody>
			{% for line in doc.items %}
			<tr>
				<td class="muted">{{ loop.index }}</td>
				<td>
					{{ line.item_name or line.item_code }}
					{% if line.description and line.description != line.item_name %}<div class="muted" style="font-size:10px; margin-top:2px;">{{ line.description }}</div>{% endif %}
				</td>
				<td class="right">{{ line.qty }}</td>
				<td>{{ line.uom or "" }}</td>
				<td class="right">{{ frappe.utils.fmt_money(line.rate, currency=currency) }}</td>
				<td class="right" style="font-weight:500;">{{ frappe.utils.fmt_money(line.amount, currency=currency) }}</td>
			</tr>
			{% endfor %}
		</tbody>
		<tfoot>
			<tr>
				<td colspan="5" class="right" style="background:#f8fafc; font-weight:600; text-transform:uppercase; font-size:9px;">Total order value</td>
				<td class="right" style="background:#f8fafc; font-weight:600;">{{ frappe.utils.fmt_money(doc.grand_total, currency=currency) }}</td>
			</tr>
		</tfoot>
	</table>

	<h3 class="sec">Terms &amp; conditions</h3>
	<div class="terms">
		{% if doc.terms %}
			{{ doc.terms }}
		{% else %}
		<ul>
			<li>Deliver to the project site named above{% if doc.schedule_date %} on or before {{ frappe.utils.format_date(doc.schedule_date) }}{% endif %}. Part deliveries are accepted against this order.</li>
			<li>Each delivery must carry a challan quoting this PO number; quantities are confirmed at site on receipt.</li>
			<li>Material not conforming to the ordered specification may be rejected at site at the supplier's cost.</li>
			<li>Invoices must reference this PO and the site-acknowledged receipt quantities.</li>
		</ul>
		{% endif %}
	</div>

	<div class="sign">
		<div><div class="line">For {{ doc.company or "&mdash;" }}</div><div class="muted" style="font-size:9px;">Authorised signatory &middot; Date</div></div>
		<div><div class="line">For {{ doc.supplier_name or doc.supplier }}</div><div class="muted" style="font-size:9px;">Acknowledged &middot; Date</div></div>
	</div>

	<div class="footer">{{ doc.name }} &middot; Generated {{ frappe.utils.format_date(frappe.utils.nowdate()) }}</div>
</div>
"""


def seed_print_assets():
	_seed_letter_head()
	_seed_wo_print_format()
	_seed_po_print_format()


def _seed_letter_head():
	html = _letter_head_html()
	if frappe.db.exists("Letter Head", LETTER_HEAD):
		# Keep the branding in sync on migrate (logo + GSTIN now populated).
		frappe.db.set_value("Letter Head", LETTER_HEAD, "content", html)
		return
	frappe.get_doc(
		{
			"doctype": "Letter Head",
			"letter_head_name": LETTER_HEAD,
			"source": "HTML",
			"content": html,
			"is_default": 1,
			"disabled": 0,
		}
	).insert(ignore_permissions=True)


def _seed_wo_print_format():
	if frappe.db.exists("Print Format", WO_PRINT_FORMAT):
		# Keep the body in sync on migrate (e.g. WO status now derives from docstatus).
		frappe.db.set_value("Print Format", WO_PRINT_FORMAT, "html", _WO_PRINT_HTML)
		return
	frappe.get_doc(
		{
			"doctype": "Print Format",
			"name": WO_PRINT_FORMAT,
			"doc_type": "Subcontractor Work Order",
			"module": "BuildSuite Core",
			"print_format_type": "Jinja",
			"custom_format": 1,
			"html": _WO_PRINT_HTML,
			"disabled": 0,
		}
	).insert(ignore_permissions=True)


def _seed_po_print_format():
	if frappe.db.exists("Print Format", PO_PRINT_FORMAT):
		# Keep the body in sync on migrate.
		frappe.db.set_value("Print Format", PO_PRINT_FORMAT, "html", _PO_PRINT_HTML)
		return
	frappe.get_doc(
		{
			"doctype": "Print Format",
			"name": PO_PRINT_FORMAT,
			"doc_type": "Purchase Order",
			"module": "BuildSuite Core",
			"print_format_type": "Jinja",
			"custom_format": 1,
			"html": _PO_PRINT_HTML,
			"disabled": 0,
		}
	).insert(ignore_permissions=True)
