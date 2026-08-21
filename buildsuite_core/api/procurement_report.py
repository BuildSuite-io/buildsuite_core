# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Real-data backends for the six bespoke Procurement report views. These answer the
procurement questions a construction contractor actually asks — what site has requested that
is not yet ordered, which deliveries are late, what is on the ground, whether purchase prices
track the QS estimate, the full purchase register, and where material was issued — computed
from the live records (Material Request / Purchase Order / Purchase Receipt / Material Issue /
Construction Rate Master), so every figure comes from a document.

One whitelisted endpoint per report. Each takes an optional `project` that narrows the report
to that project and its direct sub-projects; without it the report runs portfolio-wide. The
Vue view applies the lighter, in-reading filters (search, supplier, status, dates, the
one-click narrowings) over the rows returned here."""

import frappe
from frappe.utils import flt

from buildsuite_core.api.material_consumption import get_warehouse_from_project


def _scoped_projects(project):
	"""The project plus its direct sub-projects, or None for portfolio-wide — the same rollup
	rule the rest of the app follows for a parent project."""
	if not project or not isinstance(project, str):
		return None
	ids = {project}
	for child in frappe.get_all("Project", filters={"parent_project": project}, pluck="name"):
		ids.add(child)
	return ids


def _project_names(ids):
	"""{project: project_name} for the given ids, in one query."""
	ids = [i for i in set(ids) if i]
	if not ids:
		return {}
	return {
		p.name: p.project_name
		for p in frappe.get_all("Project", filters={"name": ["in", ids]}, fields=["name", "project_name"])
	}


def _item_meta(item_codes):
	"""{item_code: {item_name, uom, standard_rate}} for the given items, in one query."""
	item_codes = [i for i in set(item_codes) if i]
	if not item_codes:
		return {}
	return {
		it.name: {"item_name": it.item_name, "uom": it.stock_uom, "standard_rate": flt(it.standard_rate)}
		for it in frappe.get_all(
			"Item",
			filters={"name": ["in", item_codes]},
			fields=["name", "item_name", "stock_uom", "standard_rate"],
		)
	}


@frappe.whitelist()
def requests_to_order(project=None):
	"""Requests waiting to be ordered — submitted Purchase Material Requests not fully ordered
	(the gap between the request book and the order book). Value is the still-to-order portion,
	item count and dates let the view flag age and lateness."""
	scope = _scoped_projects(project)
	filters = {"docstatus": 1, "material_request_type": "Purchase", "per_ordered": ["<", 100]}
	if scope is not None:
		filters["project"] = ["in", list(scope)]
	mrs = frappe.get_all(
		"Material Request",
		filters=filters,
		fields=["name", "project", "transaction_date", "schedule_date", "status", "per_ordered"],
		order_by="schedule_date asc",
	)
	rollup = _item_rollup("Material Request Item", [m.name for m in mrs])
	names = _project_names([m.project for m in mrs])
	rows = []
	for m in mrs:
		agg = rollup.get(m.name, {"count": 0, "value": 0.0})
		rows.append(
			{
				"name": m.name,
				"project": m.project,
				"project_name": names.get(m.project) or m.project,
				"request_date": str(m.transaction_date) if m.transaction_date else None,
				"required_by": str(m.schedule_date) if m.schedule_date else None,
				"item_count": agg["count"],
				"value": agg["value"],
				"status": m.status,
			}
		)
	return rows


def _item_rollup(child_doctype, parents):
	"""{parent: {count, value}} — line count and still-to-order value (qty - ordered_qty) * rate
	across each request's items."""
	if not parents:
		return {}
	rows = frappe.db.sql(
		f"""SELECT parent, COUNT(*) AS cnt, IFNULL(SUM((qty - IFNULL(ordered_qty, 0)) * rate), 0) AS val
		FROM `tab{child_doctype}` WHERE parent IN %s GROUP BY parent""",
		(tuple(parents),),
		as_dict=True,
	)
	return {r.parent: {"count": r.cnt, "value": flt(r.val)} for r in rows}


@frappe.whitelist()
def delivery_followup(project=None):
	"""Delivery follow-up — submitted Purchase Orders not fully received, with how much has
	landed (per_received) and the value still due. The view sorts the chase list and flags the
	overdue ones off `required_by`."""
	scope = _scoped_projects(project)
	filters = {"docstatus": 1, "per_received": ["<", 100]}
	if scope is not None:
		filters["project"] = ["in", list(scope)]
	pos = frappe.get_all(
		"Purchase Order",
		filters=filters,
		fields=[
			"name",
			"supplier",
			"supplier_name",
			"project",
			"schedule_date",
			"per_received",
			"grand_total",
		],
		order_by="schedule_date asc",
	)
	names = _project_names([p.project for p in pos])
	rows = []
	for p in pos:
		pct = flt(p.per_received)
		rows.append(
			{
				"name": p.name,
				"supplier": p.supplier_name or p.supplier,
				"project": p.project,
				"project_name": names.get(p.project) or p.project,
				"required_by": str(p.schedule_date) if p.schedule_date else None,
				"pct": round(pct),
				"pending_value": round(flt(p.grand_total) * (100 - pct) / 100),
			}
		)
	return rows


@frappe.whitelist()
def site_stock(project=None):
	"""Material at site — received minus consumed, per item, at each project store. Received
	counts posted Purchase Receipts; consumed counts posted Material Issues. A cancelled
	receipt never entered stock."""
	scope = _scoped_projects(project)

	def _scoped(sql, alias):
		if scope is None:
			return sql, ()
		return sql + f" AND {alias}.project IN %s", (tuple(scope),)

	recv_sql, recv_params = _scoped(
		"""SELECT pr.project AS project, pri.item_code AS item_code, IFNULL(SUM(pri.received_qty), 0) AS qty
		FROM `tabPurchase Receipt Item` pri JOIN `tabPurchase Receipt` pr ON pr.name = pri.parent
		WHERE pr.docstatus = 1""",
		"pr",
	)
	received = frappe.db.sql(recv_sql + " GROUP BY pr.project, pri.item_code", recv_params, as_dict=True)

	cons_sql, cons_params = _scoped(
		"""SELECT se.project AS project, sed.item_code AS item_code, IFNULL(SUM(sed.qty), 0) AS qty
		FROM `tabStock Entry Detail` sed JOIN `tabStock Entry` se ON se.name = sed.parent
		WHERE se.docstatus = 1 AND se.stock_entry_type = 'Material Issue'""",
		"se",
	)
	consumed = frappe.db.sql(cons_sql + " GROUP BY se.project, sed.item_code", cons_params, as_dict=True)

	merged = {}
	for r in received:
		merged.setdefault((r.project, r.item_code), {"received": 0.0, "consumed": 0.0})["received"] += flt(
			r.qty
		)
	for r in consumed:
		merged.setdefault((r.project, r.item_code), {"received": 0.0, "consumed": 0.0})["consumed"] += flt(
			r.qty
		)

	names = _project_names([k[0] for k in merged])
	meta = _item_meta([k[1] for k in merged])
	rows = []
	for (proj, item_code), v in merged.items():
		info = meta.get(item_code, {})
		rows.append(
			{
				"project": proj,
				"project_name": names.get(proj) or proj or "No project store",
				"item": info.get("item_name") or item_code,
				"received": flt(v["received"]),
				"consumed": flt(v["consumed"]),
				"available": flt(v["received"] - v["consumed"]),
				"uom": info.get("uom") or "",
			}
		)
	return rows


@frappe.whitelist()
def rate_check(project=None):
	"""Purchase rate vs estimate — the latest order line per item that carries a Rate Master
	code, against the Rate Master's current QS rate. Lines without a code are counted as
	`unlinked` rather than silently dropped."""
	scope = _scoped_projects(project)
	where = "po.docstatus = 1"
	params = []
	if scope is not None:
		where += " AND po.project IN %s"
		params.append(tuple(scope))
	lines = frappe.db.sql(
		f"""SELECT poi.item_code, poi.item_name, poi.uom, poi.rate, poi.custom_rate_master AS code,
			po.supplier_name AS supplier, po.supplier AS supplier_id, po.name AS po, po.transaction_date AS order_date
		FROM `tabPurchase Order Item` poi JOIN `tabPurchase Order` po ON po.name = poi.parent
		WHERE {where}""",
		tuple(params),
		as_dict=True,
	)
	latest = {}
	unlinked = 0
	for ln in lines:
		if not ln.code:
			unlinked += 1
			continue
		prev = latest.get(ln.item_code)
		if not prev or (str(ln.order_date) or "") > (str(prev["order_date"]) or ""):
			latest[ln.item_code] = ln

	# Current QS rate + unit from the Rate Master, resolved once for the codes in play.
	codes = list({ln.code for ln in latest.values()})
	rm = {}
	if codes:
		rm = {
			r.name: r
			for r in frappe.get_all(
				"Construction Rate Master",
				filters={"name": ["in", codes]},
				fields=["name", "rate_code", "current_rate", "uom"],
			)
		}
	rows = []
	for ln in latest.values():
		master = rm.get(ln.code)
		est = flt(master.current_rate) if master else 0.0
		rows.append(
			{
				"item": ln.item_name or ln.item_code,
				"code": master.rate_code if master else ln.code,
				"rate": flt(ln.rate),
				"estimate": est,
				"unit": (master.uom if master else None) or ln.uom,
				"supplier": ln.supplier or ln.supplier_id,
				"po": ln.po,
				"order_date": str(ln.order_date) if ln.order_date else None,
				"variance": ((flt(ln.rate) - est) / est * 100) if est else None,
			}
		)
	rows.sort(key=lambda r: (r["variance"] if r["variance"] is not None else -999), reverse=True)
	return {"rows": rows, "unlinked": unlinked}


@frappe.whitelist()
def purchase_register(project=None):
	"""Purchase register — every purchase order line (order not cancelled): date, order,
	supplier, item, quantity, rate and amount, so last-paid is one search away."""
	scope = _scoped_projects(project)
	where = "po.docstatus < 2"
	params = []
	if scope is not None:
		where += " AND po.project IN %s"
		params.append(tuple(scope))
	lines = frappe.db.sql(
		f"""SELECT po.name AS po, po.transaction_date AS date, po.supplier_name AS supplier,
			po.supplier AS supplier_id, po.project AS project, poi.item_code, poi.item_name,
			poi.qty, poi.uom, poi.rate, poi.amount
		FROM `tabPurchase Order Item` poi JOIN `tabPurchase Order` po ON po.name = poi.parent
		WHERE {where}
		ORDER BY po.transaction_date DESC, po.name DESC""",
		tuple(params),
		as_dict=True,
	)
	names = _project_names([ln.project for ln in lines])
	return [
		{
			"po": ln.po,
			"date": str(ln.date) if ln.date else None,
			"supplier": ln.supplier or ln.supplier_id,
			"project": ln.project,
			"project_name": names.get(ln.project) or ln.project,
			"item": ln.item_name or ln.item_code,
			"qty": flt(ln.qty),
			"uom": ln.uom,
			"rate": flt(ln.rate),
			"amount": flt(ln.amount) or flt(ln.qty) * flt(ln.rate),
		}
		for ln in lines
	]


@frappe.whitelist()
def consumption_by_cost_code(project=None):
	"""Consumption by cost code — material issued to site (posted Material Issues), one row per
	issue line with the cost code it was booked against, its date, and a value at the item
	master's standard rate (a list price, not the actual issue cost — issue valuation needs
	stock rates, which aren't modelled). The view date-filters then groups by cost code + item."""
	scope = _scoped_projects(project)
	where = "se.docstatus = 1 AND se.stock_entry_type = 'Material Issue'"
	params = []
	if scope is not None:
		where += " AND se.project IN %s"
		params.append(tuple(scope))
	lines = frappe.db.sql(
		f"""SELECT se.project AS project, se.posting_date AS date, se.custom_cost_code_label AS code,
			sed.item_code, sed.item_name, sed.qty, sed.uom
		FROM `tabStock Entry Detail` sed JOIN `tabStock Entry` se ON se.name = sed.parent
		WHERE {where}""",
		tuple(params),
		as_dict=True,
	)
	meta = _item_meta([ln.item_code for ln in lines])
	names = _project_names([ln.project for ln in lines])
	rows = []
	for ln in lines:
		info = meta.get(ln.item_code, {})
		qty = flt(ln.qty)
		rows.append(
			{
				"project": ln.project,
				"project_name": names.get(ln.project) or ln.project,
				"date": str(ln.date) if ln.date else None,
				"code": ln.code or "Not coded",
				"item": ln.item_name or info.get("item_name") or ln.item_code,
				"uom": ln.uom or info.get("uom") or "",
				"qty": qty,
				"value": qty * info.get("standard_rate", 0.0),
			}
		)
	return rows
