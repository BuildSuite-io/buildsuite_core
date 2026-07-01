def get_property_setters():
	return [
		{
			"name": "Project-status-options",
			"doctype_or_field": "DocField",
			"doctype": "Project",
			"fieldname": "status",
			"property": "options",
			"value": "Open\nWorking\nCompleted\nOn Hold\nCancelled",
			"property_type": "Text",
		},
		{
			"doctype_or_field": "DocField",
			"doctype": "Task",
			"fieldname": "status",
			"property": "hidden",
			"value": "1",
			"property_type": "Check",
		},
		{
			"doctype_or_field": "DocField",
			"doctype": "Task",
			"fieldname": "status",
			"property": "in_list_view",
			"value": "0",
			"property_type": "Check",
		},
		{
			"doctype_or_field": "DocField",
			"doctype": "Task",
			"fieldname": "status",
			"property": "in_standard_filter",
			"value": "0",
			"property_type": "Check",
		},
		# Scheduling type now lives on the native `type` Link (-> Task Type). Default it
		# to "Activity" and surface it as a standard filter (parity with the removed
		# custom task_type Select).
		{
			"doctype_or_field": "DocField",
			"doctype": "Task",
			"fieldname": "type",
			"property": "default",
			"value": "Activity",
			"property_type": "Text",
		},
		{
			"doctype_or_field": "DocField",
			"doctype": "Task",
			"fieldname": "type",
			"property": "in_standard_filter",
			"value": "1",
			"property_type": "Check",
		},
    {
            "doctype": "Stock Entry",
            "fieldname": "project",
            "property": "reqd",
            "property_type": "Check",
            "value": "1"
        },
        {
            "doctype_or_field":"DocType",
            "doctype": "Stock Entry",
            "fieldname": None,
            "property": "field_order",
            "property_type": "Data",
            "value": "[\"stock_entry_details_tab\", \"company\", \"naming_series\", \"stock_entry_type\", \"purpose\", \"col2\", \"set_posting_time\", \"posting_date\", \"posting_time\", \"reference_section\", \"add_to_transit\", \"apply_putaway_rule\", \"inspection_required\", \"column_break_jabv\", \"work_order\", \"subcontracting_order\", \"outgoing_stock_entry\", \"source_stock_entry\", \"custom_section_break_o8nvm\", \"project\", \"bom_info_section\", \"from_bom\", \"use_multi_level_bom\", \"bom_no\", \"cb1\", \"fg_completed_qty\", \"get_items\", \"section_break_7qsm\", \"process_loss_percentage\", \"column_break_e92r\", \"process_loss_qty\", \"section_break_jwgn\", \"from_warehouse\", \"source_warehouse_address\", \"source_address_display\", \"cb0\", \"to_warehouse\", \"target_warehouse_address\", \"target_address_display\", \"sb0\", \"scan_barcode\", \"column_break_menu\", \"last_scanned_warehouse\", \"items_section\", \"items\", \"get_stock_and_rate\", \"section_break_19\", \"total_outgoing_value\", \"column_break_22\", \"total_incoming_value\", \"value_difference\", \"additional_costs_section\", \"additional_costs\", \"total_additional_costs\", \"supplier_info_tab\", \"contact_section\", \"supplier\", \"supplier_name\", \"supplier_address\", \"address_display\", \"accounting_dimensions_section\", \"column_break_wgvc\", \"cost_center\", \"other_info_tab\", \"printing_settings\", \"select_print_heading\", \"print_settings_col_break\", \"letter_head\", \"reference_details_section\", \"delivery_note_no\", \"sales_invoice_no\", \"job_card\", \"pick_list\", \"column_break_qpvo\", \"asset_repair\", \"purchase_receipt_no\", \"purchase_order\", \"subcontracting_inward_order\", \"is_additional_transfer_entry\", \"more_info\", \"is_opening\", \"remarks\", \"col5\", \"per_transferred\", \"total_amount\", \"amended_from\", \"credit_note\", \"is_return\", \"tab_connections\"]"
        },
        {
            "doctype": "Stock Entry",
            "fieldname": "bom_info_section",
            "property": "depends_on",
            "property_type": "Data",
            "value": "eval:doc.stock_entry_type&&doc.purpose== \"Material Receipt\""
        },
        {
            "doctype": "Stock Entry",
            "fieldname": "section_break_jwgn",
            "property": "depends_on",
            "property_type": "Data",
            "value": "eval:doc.stock_entry_type"
        },
        {
            "doctype": "Stock Entry",
            "fieldname": "additional_costs_section",
            "property": "depends_on",
            "property_type": "Data",
            "value": "eval:doc.stock_entry_type"
        },
        {
            "doctype": "Stock Entry",
            "fieldname": "sb0",
            "property": "depends_on",
            "property_type": "Data",
            "value": "eval:doc.stock_entry_type"
        },
        {
            "doctype": "Stock Entry",
            "fieldname": "more_info",
            "property": "depends_on",
            "property_type": "Data",
            "value": "eval:doc.stock_entry_type"
        },
        {
            "doctype": "Stock Entry",
            "fieldname": "printing_settings",
            "property": "depends_on",
            "property_type": "Data",
            "value": "eval:doc.stock_entry_type"
        },
        {
            "doctype": "Stock Entry",
            "fieldname": "section_break_19",
            "property": "depends_on",
            "property_type": "Data",
            "value": "eval:doc.stock_entry_type"
        },
        {
            "doctype": "Stock Entry",
            "fieldname": "items_section",
            "property": "depends_on",
            "property_type": "Data",
            "value": "eval:doc.stock_entry_type"
        },
        {
            "doctype": "Stock Entry",
            "fieldname": "accounting_dimensions_section",
            "property": "hidden",
            "property_type": "Check",
            "value": "1"
        },
        {
            "doctype": "Stock Entry",
            "fieldname": "scan_barcode",
            "property": "hidden",
            "property_type": "Check",
            "value": "1"
        },
        {
            "doctype": "Stock Entry",
            "fieldname": "add_to_transit",
            "property": "hidden",
            "property_type": "Check",
            "value": "1"
        },
        {
            "doctype": "Stock Entry",
            "fieldname": "apply_putaway_rule",
            "property": "hidden",
            "property_type": "Check",
            "value": "1"
        },

        {
            "doctype": "Stock Entry Detail",
            "fieldname": "uom",
            "property": "in_list_view",
            "property_type": "Check",
            "value": "1"
        },
        {
            "doctype": "Stock Entry Detail",
            "fieldname": "t_warehouse",
            "property": "in_list_view",
            "property_type": "Check",
            "value": "0"
        },
        {
            "doctype": "Stock Entry Detail",
            "fieldname": "s_warehouse",
            "property": "in_list_view",
            "property_type": "Check",
            "value": "0"
        },
        {
            "doctype": "Material Request",
            "fieldname": "naming_series",
            "property": "hidden",
            "property_type": "Check",
            "value": "1"
        },
        {
            "doctype": "Material Request",
            "fieldname": "naming_series",
            "property": "reqd",
            "property_type": "Check",
            "value": "0"
        },
        {
            "doctype": "Material Request",
            "fieldname": "set_from_warehouse",
            "property": "hidden",
            "property_type": "Check",
            "value": "1"
        },
        {
            "doctype": "Material Request",
            "fieldname": "set_warehouse",
            "property": "hidden",
            "property_type": "Check",
            "value": "1"
        },
        {
            "doctype": "Material Request",
            "fieldname": "set_warehouse",
            "property": "in_list_view",
            "property_type": "Check",
            "value": "0"
        },
        {
            "doctype": "Material Request",
            "fieldname": "scan_barcode",
            "property": "hidden",
            "property_type": "Check",
            "value": "1"
        },

        {
            "doctype": "Material Request Item",
            "fieldname": "description",
            "property": "reqd",
            "property_type": "Check",
            "value": 0
        },
        {
            "doctype": "Material Request Item",
            "fieldname": "description",
            "property": "in_list_view",
            "property_type": "Check",
            "value": 1
        },
        {
            "doctype": "Purchase Order",
            "fieldname": "project",
            "property": "reqd",
            "property_type": "Check",
            "value": "1"
        },
        {
            "doctype": "Purchase Order",
            "fieldname": "naming_series",
            "property": "hidden",
            "property_type": "Check",
            "value": "1"
        },
        {
            "doctype": "Purchase Order",
            "fieldname": "naming_series",
            "property": "reqd",
            "property_type": "Check",
            "value": "0"
        },
        {
            "doctype": "Purchase Order",
            "fieldname": "currency_and_price_list",
            "property": "hidden",
            "property_type": "Check",
            "value": "1"
        },
        {
            "doctype": "Purchase Invoice",
            "fieldname": "naming_series",
            "property": "hidden",
            "property_type": "Check",
            "value": "1"
        },
        {
            "doctype": "Purchase Invoice",
            "fieldname": "incoterm",
            "property": "hidden",
            "property_type": "Check",
            "value": "1"
        },
        {
            "doctype": "Purchase Invoice",
            "fieldname": "shipping_rule",
            "property": "hidden",
            "property_type": "Check",
            "value": "1"
        },
        {
            "doctype": "Purchase Invoice",
            "fieldname": "update_stock",
            "property": "hidden",
            "property_type": "Check",
            "value": "1"
        },
        {
            "doctype": "Purchase Invoice",
            "fieldname": "currency_and_price_list",
            "property": "hidden",
            "property_type": "Check",
            "value": "1"
        },
        {
            "doctype": "Purchase Invoice",
            "fieldname": "scan_barcode",
            "property": "hidden",
            "property_type": "Check",
            "value": "1"
        },
        {
            "doctype_or_field":"DocType",
            "doctype": "Purchase Invoice",
            "fieldname": None,
            "property": "field_order",
            "property_type": "Data",
            "value": "[\"naming_series\", \"supplier\", \"supplier_name\", \"tax_id\", \"company\", \"column_break_6\", \"posting_date\", \"posting_time\", \"set_posting_time\", \"due_date\", \"column_break1\", \"is_paid\", \"is_return\", \"return_against\", \"update_outstanding_for_self\", \"update_billed_amount_in_purchase_order\", \"update_billed_amount_in_purchase_receipt\", \"apply_tds\", \"amended_from\", \"supplier_invoice_details\", \"bill_no\", \"column_break_15\", \"bill_date\", \"accounting_dimensions_section\", \"cost_center\", \"dimension_col_break\", \"currency_and_price_list\", \"currency\", \"conversion_rate\", \"use_transaction_date_exchange_rate\", \"column_break2\", \"buying_price_list\", \"price_list_currency\", \"plc_conversion_rate\", \"ignore_pricing_rule\", \"sec_warehouse\", \"project\", \"scan_barcode\", \"last_scanned_warehouse\", \"col_break_warehouse\", \"update_stock\", \"set_warehouse\", \"set_from_warehouse\", \"is_subcontracted\", \"rejected_warehouse\", \"supplier_warehouse\", \"items_section\", \"items\", \"section_break_26\", \"total_qty\", \"total_net_weight\", \"column_break_50\", \"base_total\", \"base_net_total\", \"claimed_landed_cost_amount\", \"column_break_28\", \"total\", \"net_total\", \"taxes_section\", \"tax_category\", \"taxes_and_charges\", \"column_break_58\", \"shipping_rule\", \"column_break_49\", \"incoterm\", \"named_place\", \"section_break_51\", \"taxes\", \"totals\", \"base_taxes_and_charges_added\", \"base_taxes_and_charges_deducted\", \"base_total_taxes_and_charges\", \"column_break_40\", \"taxes_and_charges_added\", \"taxes_and_charges_deducted\", \"total_taxes_and_charges\", \"totals_section\", \"use_company_roundoff_cost_center\", \"grand_total\", \"in_words\", \"column_break8\", \"disable_rounded_total\", \"rounding_adjustment\", \"rounded_total\", \"base_totals_section\", \"base_grand_total\", \"base_in_words\", \"column_break_hcca\", \"base_rounding_adjustment\", \"base_rounded_total\", \"section_break_ttrv\", \"total_advance\", \"column_break_peap\", \"outstanding_amount\", \"section_tax_withholding_entry\", \"tax_withholding_group\", \"ignore_tax_withholding_threshold\", \"override_tax_withholding_entries\", \"tax_withholding_entries\", \"section_break_44\", \"apply_discount_on\", \"base_discount_amount\", \"column_break_46\", \"additional_discount_percentage\", \"discount_amount\", \"sec_tax_breakup\", \"other_charges_calculation\", \"item_wise_tax_details\", \"pricing_rule_details\", \"pricing_rules\", \"raw_materials_supplied\", \"supplied_items\", \"payments_tab\", \"payments_section\", \"mode_of_payment\", \"base_paid_amount\", \"clearance_date\", \"col_br_payments\", \"cash_bank_account\", \"paid_amount\", \"advances_section\", \"allocate_advances_automatically\", \"only_include_allocated_payments\", \"get_advances\", \"advances\", \"write_off\", \"write_off_amount\", \"base_write_off_amount\", \"column_break_61\", \"write_off_account\", \"write_off_cost_center\", \"address_and_contact_tab\", \"section_addresses\", \"supplier_address\", \"address_display\", \"col_break_address\", \"contact_person\", \"contact_display\", \"contact_mobile\", \"contact_email\", \"company_shipping_address_section\", \"dispatch_address\", \"dispatch_address_display\", \"column_break_126\", \"shipping_address\", \"shipping_address_display\", \"company_billing_address_section\", \"billing_address\", \"column_break_130\", \"billing_address_display\", \"terms_tab\", \"payment_schedule_section\", \"payment_terms_template\", \"ignore_default_payment_terms_template\", \"payment_schedule\", \"terms_section_break\", \"tc_name\", \"terms\", \"more_info_tab\", \"status_section\", \"status\", \"column_break_177\", \"per_received\", \"accounting_details_section\", \"credit_to\", \"party_account_currency\", \"is_opening\", \"against_expense_account\", \"column_break_63\", \"unrealized_profit_loss_account\", \"subscription_section\", \"subscription\", \"column_break_114\", \"from_date\", \"to_date\", \"automation_section\", \"auto_repeat\", \"update_auto_repeat_reference\", \"printing_settings\", \"letter_head\", \"group_same_items\", \"column_break_112\", \"select_print_heading\", \"language\", \"sb_14\", \"on_hold\", \"release_date\", \"cb_17\", \"hold_comment\", \"additional_info_section\", \"is_internal_supplier\", \"title\", \"represents_company\", \"supplier_group\", \"sender\", \"column_break_147\", \"inter_company_invoice_reference\", \"remarks\", \"connections_tab\"]"
        },
        {
            "doctype": "Purchase Invoice Item",
            "fieldname": "uom",
            "property": "in_list_view",
            "property_type": "Check",
            "value": "1"
        },
        {
            "doctype": "Purchase Receipt",
            "fieldname": "project",
            "property": "reqd",
            "property_type": "Check",
            "value": "1"
        },
        {
            "doctype": "Purchase Receipt",
            "fieldname": "naming_series",
            "property": "hidden",
            "property_type": "Check",
            "value": "1"
        },
        {
            "doctype": "Purchase Receipt",
            "fieldname": "naming_series",
            "property": "reqd",
            "property_type": "Check",
            "value": "0"
        },
        {
            "doctype": "Purchase Receipt",
            "fieldname": "incoterm",
            "property": "hidden",
            "property_type": "Check",
            "value": "1"
        },
        {
            "doctype": "Purchase Receipt",
            "fieldname": "shipping_rule",
            "property": "hidden",
            "property_type": "Check",
            "value": "1"
        },
        {
            "doctype": "Purchase Receipt",
            "fieldname": "currency_and_price_list",
            "property": "hidden",
            "property_type": "Check",
            "value": "1"
        },
        {
            "doctype": "Purchase Receipt",
            "fieldname": "apply_putaway_rule",
            "property": "hidden",
            "property_type": "Check",
            "value": "1"
        },
        {
            "doctype": "Purchase Receipt",
            "fieldname": "scan_barcode",
            "property": "hidden",
            "property_type": "Check",
            "value": "1"
        },
        {
            "doctype_or_field":"DocType",
            "doctype": "Purchase Receipt",
            "fieldname": None,
            "property": "field_order",
            "property_type": "Data",
            "value": "[\"supplier_section\", \"column_break0\", \"naming_series\", \"supplier\", \"supplier_name\", \"supplier_delivery_note\", \"subcontracting_receipt\", \"column_break1\", \"posting_date\", \"posting_time\", \"set_posting_time\", \"column_break_12\", \"company\", \"apply_putaway_rule\", \"is_return\", \"return_against\", \"accounting_dimensions_section\", \"cost_center\", \"dimension_col_break\", \"currency_and_price_list\", \"currency\", \"conversion_rate\", \"column_break2\", \"buying_price_list\", \"price_list_currency\", \"plc_conversion_rate\", \"ignore_pricing_rule\", \"sec_warehouse\", \"project\", \"scan_barcode\", \"last_scanned_warehouse\", \"column_break_31\", \"set_warehouse\", \"set_from_warehouse\", \"col_break_warehouse\", \"rejected_warehouse\", \"is_subcontracted\", \"supplier_warehouse\", \"items_section\", \"items\", \"section_break0\", \"total_qty\", \"total_net_weight\", \"column_break_43\", \"base_total\", \"base_net_total\", \"column_break_27\", \"total\", \"net_total\", \"taxes_charges_section\", \"tax_category\", \"taxes_and_charges\", \"shipping_col\", \"shipping_rule\", \"column_break_53\", \"incoterm\", \"named_place\", \"taxes_section\", \"taxes\", \"totals\", \"base_taxes_and_charges_added\", \"base_taxes_and_charges_deducted\", \"base_total_taxes_and_charges\", \"column_break3\", \"taxes_and_charges_added\", \"taxes_and_charges_deducted\", \"total_taxes_and_charges\", \"totals_section\", \"grand_total\", \"in_words\", \"column_break_50\", \"disable_rounded_total\", \"rounding_adjustment\", \"rounded_total\", \"base_totals_section\", \"base_grand_total\", \"base_in_words\", \"column_break_ugyv\", \"base_rounding_adjustment\", \"base_rounded_total\", \"section_break_42\", \"apply_discount_on\", \"base_discount_amount\", \"column_break_44\", \"additional_discount_percentage\", \"discount_amount\", \"sec_tax_breakup\", \"other_charges_calculation\", \"item_wise_tax_details\", \"pricing_rule_details\", \"pricing_rules\", \"raw_material_details\", \"get_current_stock\", \"supplied_items\", \"address_and_contact_tab\", \"section_addresses\", \"supplier_address\", \"address_display\", \"col_break_address\", \"contact_person\", \"contact_display\", \"contact_mobile\", \"contact_email\", \"section_break_98\", \"dispatch_address\", \"dispatch_address_display\", \"column_break_100\", \"shipping_address\", \"shipping_address_display\", \"billing_address_section\", \"billing_address\", \"column_break_104\", \"billing_address_display\", \"terms_tab\", \"tc_name\", \"terms\", \"more_info_tab\", \"status_section\", \"status\", \"column_break4\", \"per_billed\", \"per_returned\", \"subscription_detail\", \"auto_repeat\", \"printing_settings\", \"letter_head\", \"group_same_items\", \"column_break_97\", \"select_print_heading\", \"language\", \"transporter_info\", \"transporter_name\", \"column_break5\", \"lr_no\", \"lr_date\", \"additional_info_section\", \"instructions\", \"is_internal_supplier\", \"represents_company\", \"title\", \"inter_company_reference\", \"column_break_131\", \"remarks\", \"range\", \"amended_from\", \"other_details\", \"connections_tab\"]" 
        },
        {
            "doctype": "Purchase Receipt Item",
            "fieldname": "uom",
            "property": "in_list_view",
            "property_type": "Check",
            "value": "1"
        },
	]
