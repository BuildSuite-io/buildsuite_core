# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""Site-level customisations (SDK phase 4).

A "BuildSuite Customisation" record is a declaration stored as data, so a person (or an AI, or a
drag-and-drop editor) can customise a site without code. Each record has a `kind` and a JSON `config`
checked against that kind's schema here, in one place; the SPA turns the validated records into the
same registry entries an installed app would add (frontend/src/sdk/site.js).

Kinds
  List Column     {doctype, field, label?, align?}      a column on that DocType's lists
  Form Field      {doctype, fieldname, position?}       a control for a Custom Field on a bespoke form
  Workspace Tile  {workspace, label, to, description?}
  Notice          {slot, message, tone?}                a plain-text notice in a named slot

Only data: no HTML, no script, no external links. Unknown keys are rejected so a typo (or a model's
invention) fails loudly instead of silently doing nothing."""

import re

import frappe
from frappe import _
from frappe.model import default_fields

DOCTYPE = "BuildSuite Customisation"
ALIGN = ("left", "right", "center")
POSITION = ("top", "bottom")
TONE = ("info", "success", "warning")

_SLUG = re.compile(r"^[a-z0-9][a-z0-9-]{0,62}$")
_SLOT = re.compile(r"^(page\.[a-z0-9-]+|form\.[A-Za-z0-9][A-Za-z0-9 _-]*)\.(top|bottom)$")


def _fail(message, *args):
	frappe.throw(_(message).format(*args), frappe.ValidationError)


def _text(config, key, max_len, *, required=False, default=None):
	value = config.get(key)
	if value is None or value == "":
		if required:
			_fail("{0} is required.", key)
		return default
	if not isinstance(value, str):
		_fail("{0} must be text.", key)
	value = value.strip()
	if len(value) > max_len:
		_fail("{0} is longer than {1} characters.", key, max_len)
	return value


def _choice(config, key, options, default):
	value = config.get(key, default)
	if value not in options:
		_fail("{0} must be one of {1}.", key, ", ".join(options))
	return value


def _doctype(config):
	name = _text(config, "doctype", 140, required=True)
	if not frappe.db.exists("DocType", name):
		_fail("DocType {0} does not exist.", name)
	return name


def _only(config, allowed):
	extra = sorted(set(config) - set(allowed))
	if extra:
		_fail("Unknown setting(s): {0}. Allowed: {1}.", ", ".join(extra), ", ".join(allowed))


def _internal_path(value):
	"""A path inside the app: starts with one slash, no scheme, no protocol-relative form."""
	if not value.startswith("/") or value.startswith("//") or ":" in value.split("?")[0] or ".." in value:
		_fail("to must be a path inside the app, such as /projects.")
	return value


def _list_column(config):
	_only(config, ("doctype", "field", "label", "align"))
	doctype = _doctype(config)
	field = _text(config, "field", 140, required=True)
	meta = frappe.get_meta(doctype)
	df = meta.get_field(field)
	if not df and field not in default_fields:  # name, owner, creation, modified... are not DocFields
		_fail("{0} has no field {1}.", doctype, field)
	label = (df.label if df else None) or field.replace("_", " ").title()
	return {
		"doctype": doctype,
		"field": field,
		"label": _text(config, "label", 60, default=label),
		"align": _choice(config, "align", ALIGN, "left"),
	}


def _form_field(config):
	_only(config, ("doctype", "fieldname", "position"))
	doctype = _doctype(config)
	fieldname = _text(config, "fieldname", 140, required=True)
	# Only a Custom Field: a customisation must never reach a standard field of Core.
	if not frappe.db.exists("Custom Field", {"dt": doctype, "fieldname": fieldname}):
		_fail("{0} is not a Custom Field of {1}. Create the Custom Field first.", fieldname, doctype)
	return {
		"doctype": doctype,
		"fieldname": fieldname,
		"position": _choice(config, "position", POSITION, "bottom"),
	}


def _workspace_tile(config):
	_only(config, ("workspace", "label", "to", "description"))
	workspace = _text(config, "workspace", 63, required=True)
	if not _SLUG.match(workspace):
		_fail("workspace must be a slug such as site-execution.")
	return {
		"workspace": workspace,
		"label": _text(config, "label", 60, required=True),
		"to": _internal_path(_text(config, "to", 200, required=True)),
		"description": _text(config, "description", 200, default=""),
	}


def _notice(config):
	_only(config, ("slot", "message", "tone"))
	slot = _text(config, "slot", 140, required=True)
	if not _SLOT.match(slot):
		_fail("slot must look like page.<route name>.top or form.<DocType>.bottom.")
	return {
		"slot": slot,
		"message": _text(config, "message", 500, required=True),
		"tone": _choice(config, "tone", TONE, "info"),
	}


_CLEANERS = {
	"List Column": _list_column,
	"Form Field": _form_field,
	"Workspace Tile": _workspace_tile,
	"Notice": _notice,
}


def clean_config(kind, config) -> dict:
	"""The validated, normalised config of one record, or a ValidationError saying what is wrong."""
	cleaner = _CLEANERS.get(kind)
	if not cleaner:
		_fail("Unknown kind {0}.", kind)
	try:
		config = frappe.parse_json(config) if isinstance(config, str) else config
	except Exception:
		_fail("Config is not valid JSON.")
	if not isinstance(config, dict):
		_fail("Config must be a JSON object.")
	return cleaner(config)


def _field_description(doctype, fieldname):
	"""What the SPA needs to draw a control for the field, or None if it is gone."""
	df = frappe.get_meta(doctype).get_field(fieldname)
	if not df:
		return None
	return {
		"fieldname": df.fieldname,
		"label": df.label or df.fieldname,
		"fieldtype": df.fieldtype,
		"options": df.options,
		"reqd": int(df.reqd or 0),
		"description": df.description,
	}


def get_customisations() -> list[dict]:
	"""The enabled customisations, in creation order, for the boot payload. A record that no longer
	validates (a Custom Field was deleted, a DocType uninstalled) is skipped, never an error."""
	if not frappe.db.exists("DocType", DOCTYPE):
		return []
	out = []
	for row in frappe.get_all(
		DOCTYPE,
		filters={"enabled": 1},
		fields=["name", "kind", "config"],
		order_by="creation asc",
	):
		try:
			config = clean_config(row.kind, row.config)
			if row.kind == "Form Field":
				field = _field_description(config["doctype"], config["fieldname"])
				if not field:
					continue
				config["field"] = field
		except frappe.ValidationError:
			frappe.clear_last_message()
			continue
		out.append({"name": row.name, "kind": row.kind, "config": config})
	return out
