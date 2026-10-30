# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Seed the print assets shared across the modules: a Letter Head per company (brand logo +
subtext) and the Purchase Order Print Format (Jinja). The letter head carries the company branding
that every print format consumes; the document identity lives in each format's body. Idempotent.

A Subcontractor Work Order format was also seeded here once, but the active Work Order format is now
"BuildSuite Work Order" (buildsuite_core/print_formats.py), so the old one is retired — see
patches.retire_subcontractor_work_order_print_format."""

import frappe

LETTER_HEAD = "BuildSuite Standard"
PO_PRINT_FORMAT = "Purchase Order"

_LEGAL_SUFFIXES = {"pvt", "private", "ltd", "limited", "llp", "inc", "co", "and", "&"}


def company_monogram(company_name: str) -> str:
	"""Up to two initials for the logo placeholder, legal suffixes dropped so
	"Acme Commercial Pvt Ltd" → "AC" (not "ACPL") and non-letters stripped so
	"XCorp (Demo)" → "XD" (not "X("). Falls back to "BS"."""
	import re

	words = [
		re.sub(r"[^A-Za-z0-9]", "", w)
		for w in re.split(r"\s+", company_name or "")
		if w and w.lower() not in _LEGAL_SUFFIXES
	]
	initials = "".join(w[0].upper() for w in words if w)[:2]
	return initials or "BS"


def build_letter_head_html(company_name: str, logo: str | None = None, subtext: str | None = None) -> str:
	"""Build the Letter Head header HTML from a company's branding: the uploaded logo (or a
	brand-coloured monogram of the company's initials when there is none — an empty box reads
	as a missing image, a monogram reads as a letter head), the company name, and the free-text
	subtext (address / GSTIN / contact). Mirrors the prototype's shared LetterHead. Text is
	escaped; subtext newlines are honoured via white-space:pre-line."""
	from frappe.utils import escape_html

	font = "-apple-system, 'Segoe UI', Roboto, sans-serif"
	if logo:
		mark_html = (
			f'<img src="{escape_html(logo)}" alt="" '
			'style="height:48px; width:auto; object-fit:contain; flex-shrink:0;" />'
		)
	else:
		mark_html = (
			'<div style="height:48px; width:48px; border-radius:8px; background:#16A34A; '
			"color:#ffffff; display:flex; align-items:center; justify-content:center; "
			f'font-weight:600; font-size:18px; flex-shrink:0; font-family:{font};">'
			f"{escape_html(company_monogram(company_name))}</div>"
		)
	subtext_html = (
		'<div style="font-size:11px; color:#475569; margin-top:3px; white-space:pre-line; '
		'line-height:1.4;">'
		f"{escape_html(subtext)}</div>"
		if subtext
		else ""
	)
	return (
		'<div style="display:flex; align-items:center; gap:12px; padding:0 0 10px 0; '
		f'border-bottom:2px solid #0f172a; font-family:{font};">'
		f"{mark_html}"
		'<div style="min-width:0;">'
		'<div style="font-size:18px; font-weight:600; color:#0f172a; line-height:1.2;">'
		f"{escape_html(company_name)}</div>"
		f"{subtext_html}"
		"</div>"
		"</div>"
	)


def letter_head_name(company: str) -> str:
	"""The Letter Head name for a company. The default company keeps the historical
	"BuildSuite Standard" name (which stays is_default, the fallback for documents with no
	company); every other company gets its own "BuildSuite — <name>" head."""
	from buildsuite_core.utils.project import default_company

	if company == default_company():
		return LETTER_HEAD
	name = frappe.db.get_value("Company", company, "company_name") or company
	return f"BuildSuite — {name}"


def rebuild_letter_head(company: str | None = None) -> None:
	"""(Re)build a company's Letter Head from its branding (logo + subtext).

	One Letter Head per company so a print reflects the branding of the company that issued the
	document (resolved in api.printing.get_print_html). The default company's head is is_default
	— the fallback for documents with no company. Called on seed and whenever a Company is saved
	(hooks.py Company.on_update). Reads the branding fields defensively so it is safe
	before/without the custom fields (fresh install ordering)."""
	from buildsuite_core.utils.project import default_company

	company = company or default_company()
	if not company:
		return

	meta = frappe.get_meta("Company")
	name = frappe.db.get_value("Company", company, "company_name") or company
	logo = (
		frappe.db.get_value("Company", company, "custom_company_logo")
		if meta.has_field("custom_company_logo")
		else None
	)
	subtext = (
		frappe.db.get_value("Company", company, "custom_letter_head_subtext")
		if meta.has_field("custom_letter_head_subtext")
		else None
	)
	content = build_letter_head_html(name, logo, subtext)
	lh_name = letter_head_name(company)
	is_default = 1 if company == default_company() else 0

	if frappe.db.exists("Letter Head", lh_name):
		lh = frappe.get_doc("Letter Head", lh_name)
		lh.source = "HTML"
		lh.content = content
		lh.is_default = is_default
		lh.disabled = 0
		lh.save(ignore_permissions=True)
	else:
		frappe.get_doc(
			{
				"doctype": "Letter Head",
				"letter_head_name": lh_name,
				"source": "HTML",
				"content": content,
				"is_default": is_default,
				"disabled": 0,
			}
		).insert(ignore_permissions=True)


def rebuild_all_letter_heads() -> None:
	"""Rebuild every company's Letter Head — used on seed and by the backfill patch."""
	for company in frappe.get_all("Company", pluck="name"):
		rebuild_letter_head(company)


# Jinja/HTML body for the Purchase Order (S234 in the prototype). The letter head is
# prepended by the print engine (company branding); this is the document body only.
# ERPNext Purchase Order fields — header-level `project` is set by save_purchase_order.
_PO_PRINT_HTML = """
<style>
	.po-print { font-family: -apple-system, "Segoe UI", Roboto, sans-serif; color:#1e293b; font-size:12px; }
	.po-print .muted { color:#64748b; }
	.po-print .label { font-size:10px; text-transform:uppercase; letter-spacing:0.06em; color:#64748b; }
	.po-print .right { text-align:right; }
	.po-title-row { display:flex; justify-content:space-between; align-items:flex-start; gap:24px;
		border-bottom:2px solid #cbd5e1; padding-bottom:12px; margin-bottom:16px; }
	.po-title { font-size:20px; font-weight:700; letter-spacing:1px; }
	/* Letter head sits on the LEFT of the title row (brand left, PO title right) — matching the
	   .bs-print formats. The head carries its own bottom rule, so drop it inside the title row. */
	.po-lh { flex:1; min-width:0; }
	.po-lh > div { border-bottom:none !important; padding-bottom:0 !important; }
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
		<div class="po-lh">{% if letter_head and not no_letterhead %}{{ letter_head }}{% endif %}</div>
		<div class="right">
			<div class="po-title">PURCHASE ORDER</div>
			<div class="muted" style="font-size:11px; margin-top:4px;">{{ doc.name }}</div>
			<div class="muted" style="margin-top:2px;">{{ frappe.utils.format_date(doc.transaction_date) }}</div>
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
	_seed_po_print_format()
	# Make the seeded format the doctype default so the SPA print view (which reads
	# meta.default_print_format) shows it out of the box. Only when nothing is set —
	# never clobber an admin's Desk choice (Customize Form → Default Print Format).
	_set_default_print_format("Purchase Order", PO_PRINT_FORMAT)


def _set_default_print_format(doctype: str, print_format: str) -> None:
	"""Make the seeded BuildSuite format the doctype's default so the SPA print view (which reads
	meta.default_print_format) uses it. Set it even when another default is already in place —
	matching how buildsuite_core.print_formats seeds the .bs-print formats. The previous
	only-if-empty guard left a site whose Purchase Order already had some other default (e.g.
	ERPNext's "Standard") stuck on that format even though the BuildSuite one was seeded, so its
	print view never used it."""
	if frappe.get_meta(doctype).default_print_format == print_format:
		return  # already the default — skip a redundant property-setter write
	frappe.make_property_setter(
		{
			"doctype": doctype,
			"doctype_or_field": "DocType",
			"property": "default_print_format",
			"value": print_format,
			"property_type": "Data",
		},
		is_system_generated=True,
	)
	frappe.clear_cache(doctype=doctype)


def _seed_letter_head():
	# Build a letter head per company from its branding (logo + subtext). On a fresh site with
	# no branding yet this yields a clean monogram + name-only header; each is rebuilt whenever
	# that company is saved (hooks.py Company.on_update → rebuild_letter_head).
	rebuild_all_letter_heads()


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
