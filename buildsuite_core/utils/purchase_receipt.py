import frappe


def create_remarks(self, metthod=None):
    # Get values from fields
    remarks = None
    full_name = frappe.db.get_value("User", frappe.session.user, 'full_name')
        
        # Get the old remark before saving
    old_remark = self.get_doc_before_save().remarks if self.get_doc_before_save() else None

    if self.remarks != old_remark:

        if not self.remarks:  # If remark is empty
            self.remarks = create_remarks(self)
        else:
            self.remarks = f"{self.remarks} - Updated by {full_name}"

    elif old_remark and "Updated by" in old_remark:
        self.remarks = old_remark
    else:
        supplier = self.supplier or "N/A"
        items = ", ".join([item.item_name for item in self.items]) if self.items else "N/A"
        total_qty = self.total_qty or "N/A"
        net_total = self.net_total or "N/A"
        project_name = frappe.db.get_value("Project", self.project, "project_name") or ""
        set_warehouse = self.set_warehouse or "N/A"
        rejected_warehouse = self.rejected_warehouse or "N/A"

        # Prepare project information if present
        project_info = f" for the project '{project_name}'" if project_name else ""

        # Construct the remarks
        remarks = (
            f"Purchase Receipt from supplier '{supplier}' with a total quantity of {total_qty} "
            f"and a net total of {net_total}. Items received: {items}."
            f" Stored in warehouse '{set_warehouse}'."
        )
        
        # Add rejected warehouse information if applicable
        if rejected_warehouse != "N/A":
            remarks += f" Rejected items are stored in '{rejected_warehouse}'."

        # Add project information if present
        if project_name:
            remarks += f" This receipt is associated with{project_info}."
        self.remarks = remarks

    return remarks
