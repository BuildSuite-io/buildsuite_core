from datetime import datetime

import frappe
from frappe import _
from frappe.model.docstatus import DocStatus
from frappe.model.workflow import (
	WorkflowTransitionError,
	get_transitions,
	get_workflow,
	has_approval_access,
)
from frappe.utils import cint


@frappe.whitelist()
def apply_workflow(doc, action):
	"""Allow workflow action on the current doc"""
	doc = frappe.get_doc(frappe.parse_json(doc))
	doc.load_from_db()
	workflow = get_workflow(doc.doctype)
	transitions = get_transitions(doc, workflow)
	user = frappe.session.user
	new_state = None
	old_state = None
	# find the transition
	transition = None
	for t in transitions:
		new_state = t.next_state
		old_state = t.state
		if t.action == action:
			transition = t

	if not transition:
		frappe.throw(_("Not a valid Workflow Action"), WorkflowTransitionError)

	if not has_approval_access(user, doc, transition):
		frappe.throw(_("Self approval is not allowed"))

	# update workflow state field
	doc.set(workflow.workflow_state_field, transition.next_state)

	# find settings for the next state
	next_state = next(d for d in workflow.states if d.state == transition.next_state)

	# update any additional field
	if next_state.update_field:
		doc.set(next_state.update_field, next_state.update_value)

	new_docstatus = cint(next_state.doc_status)
	if doc.docstatus.is_draft() and new_docstatus == DocStatus.draft():
		doc.save()
	elif doc.docstatus.is_draft() and new_docstatus == DocStatus.submitted():
		doc.submit()
	elif doc.docstatus.is_submitted() and new_docstatus == DocStatus.submitted():
		doc.save()
	elif doc.docstatus.is_submitted() and new_docstatus == DocStatus.cancelled():
		doc.cancel()
	else:
		frappe.throw(_("Illegal Document Status for {0}").format(next_state.state))

	doc.add_comment("Workflow", _(next_state.state))
	create_workflow_log(doc, old_state, new_state, user, workflow)
	return doc


def create_workflow_log(doc, old_state, new_state, user, workflow):
    # The Pending Approval Log doctype is optional — skip logging (rather than
    # break the workflow transition) when it isn't installed on the site.
    if not frappe.db.table_exists("Pending Approval Log"):
        return
    now = datetime.now()
    transitions = get_transitions(doc, workflow)

    # Get the next state from transitions
    next_state = None
    for t in transitions:
        next_state = t.next_state
        break  # Exit loop on first match

    # Check if an existing approval log entry exists for the old state
    existing_log = frappe.db.get_value(
        "Pending Approval Log",
        {'reference_doctype': doc.doctype, 'reference_name': doc.name, 'action': old_state},
        'name'
    )

    if existing_log:
        frappe.db.set_value("Pending Approval Log", existing_log, 'approved', 1)

    # Create new Pending Approval Log only if next state is valid
    if next_state != "Cancelled":
        try:
            pending_approval_log = frappe.get_doc({
                "doctype": "Pending Approval Log",
                "reference_doctype": doc.doctype,
                "reference_name": doc.name,
                "action": new_state,
                "timestamp": now,
                "performed_by": user
            })
            pending_approval_log.owner = user  # Explicitly set owner
            pending_approval_log.insert(ignore_permissions=True, ignore_links=True, ignore_mandatory=True)
            frappe.db.commit()
        except Exception as e:
            frappe.log_error(f"Error creating Pending Approval Log: {str(e)}", "Approval Log Error")


def delete_workflow_log(doc, method):
    if doc.doctype != "Pending Approval Log" or doc.doctype!="Workflow":
        # workflow = get_workflow(doc.doctype)
        
        # if not workflow:
        #     return None
        if frappe.db.exists("Pending Approval Log", {'reference_doctype': doc.doctype, 'reference_name': doc.name}):
            frappe.db.delete("Pending Approval Log", filters={'reference_doctype': doc.doctype, 'reference_name': doc.name})
            frappe.db.commit()


def update_account(doc, method):
    if doc.account_name=="Cost of Goods Sold":
        doc.account_name = "Material Cost"
        

def apply_patches():
    import frappe.model.workflow
    frappe.model.workflow.apply_workflow = apply_workflow