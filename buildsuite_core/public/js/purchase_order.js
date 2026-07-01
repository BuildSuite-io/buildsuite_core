frappe.ui.form.on('Purchase Order', {
    onload: function (frm) {
        ['schedule_date'].forEach(field => {
          frappe.ui.form.on('Purchase Order', {
            [field]: function (frm) {
              if (!frm.doc.items) return;
              frm.doc.items.forEach(row => {
                row[field] = frm.doc[field];
              });
        
              frm.refresh_field('items');
            }
          });
        });
    },
    schedule_date:function(frm){
    ['schedule_date'].forEach(field => {
          frappe.ui.form.on('Purchase Order', {
            [field]: function (frm) {
              if (!frm.doc.items) return;
              frm.doc.items.forEach(row => {
                row[field] = frm.doc[field];
              });
        
              frm.refresh_field('items');
            }
          });
        });
    },
    project:function(frm){
        if (frm.doc.project){
            if(frm.doc.items){
                frm.doc.items.forEach(item => {
                    frappe.model.set_value(item.doctype, item.name, 'project', frm.doc.project);
                    
                });
                frm.refresh_field('items');

            }
            frappe.call({
                method: "buildsuite_core.utils.stock_entry.get_warehouse_from_project",
                args: {
                    project: frm.doc.project,
                },
                freeze: true,
                callback: function (r) {
                    if (r.message) {
                        if(frm.doc.items){
                            frm.doc.items.forEach(item => {
                               frappe.model.set_value(item.doctype, item.name, 'warehouse', r.message);
                            });
                            frm.refresh_field('items');

                        }
                        frm.set_value("set_warehouse",r.message)
                    }
                }
            })
		}else{
            frm.set_value("set_warehouse",null)
        }
	},
    refresh(frm){
        frm.set_query('warehouse', 'items', function () {
			return {
					filters: { 'project': frm.doc.project,'is_group':0}
				}
		});
        frm.set_query('set_warehouse',  function () {
            return {
                filters: { 'project': frm.doc.project,'is_group':0}
            }
        })
        frm.set_query('item_tax_template', 'items', function (doc, cdt, cdn) {
            var item = frappe.get_doc(cdt, cdn);

            if(!item.item_code) {
                return doc.company ? {filters: {company: doc.company, custom_purpose:"Sales"}} : {};
            } else {
                let filters = {
                    'item_code': item.item_code,
                    'valid_from': ["<=", doc.transaction_date || doc.bill_date || doc.posting_date],
                    'item_group': item.item_group,
                    'custom_purpose':"Purchase",
                }

                if (doc.tax_category)
                    filters['tax_category'] = doc.tax_category;
                if (doc.company)
                    filters['company'] = doc.company;
                return {
                    query: "buildsuite_core.utils.purchase_order.get_tax_template",
                    filters: filters
                }
            }
		});
		render_banner(frm);
	},
	before_submit(frm) {
		if (frm.__rm_handled) return; // already decided this submit; let it through
		if (!above_threshold_lines(frm).length) return;
		frappe.validated = false;
		show_rate_master_dialog(frm);
	},
});

frappe.ui.form.on("Purchase Order Item", {
    amount: function (frm, cdt, cdn) {
        let item = locals[cdt][cdn];
        if (item.qty && item.amount) {
            item.__manual_amount = true;
            frappe.model.set_value(cdt, cdn, "rate", flt(item.amount / item.qty, precision("rate", item)));
            frappe.model.set_value(cdt, cdn, "custom_amout", item.amount);
        }
    },
	rate: render_banner,
	item_code: render_banner,
	items_remove: render_banner,
});

// ---------------------------------------------------------------------------
// Rate Master sync: warn on submit when a PO line's rate is above the linked
// Construction Rate Master, and offer to update the master.
// ---------------------------------------------------------------------------
const RM_THRESHOLD_PCT = 5; // TODO: move to BuildSuite Core Settings.
const esc = frappe.utils.escape_html;

function above_threshold_lines(frm) {
	const limit = 1 + RM_THRESHOLD_PCT / 100;
	return (frm.doc.items || []).filter(
		(row) =>
			row.custom_rate_master &&
			flt(row.custom_rate_master_rate) > 0 &&
			flt(row.rate) > flt(row.custom_rate_master_rate) * limit
	);
}

// Several PO lines can share one Rate Master — keep just the highest-rate line
// per master, so each master shows once.
function dialog_rows(frm) {
	const by_rm = {};
	for (const row of above_threshold_lines(frm)) {
		const code = row.custom_rate_master;
		const best = by_rm[code];
		if (!best || flt(row.rate) > flt(best.new_rate)) {
			const old_rate = flt(row.custom_rate_master_rate);
			const new_rate = flt(row.rate);
			by_rm[code] = {
				rm_code: code,
				rm: row.custom_rate_master_name || code,
				items: row.item_code,
				old_rate: old_rate,
				new_rate: new_rate,
				delta: old_rate
					? `${(((new_rate - old_rate) / old_rate) * 100).toFixed(1)}%`
					: "—",
			};
		}
	}
	return Object.values(by_rm);
}

function render_banner(frm) {
	const field = frm.get_field("custom_rate_master_banner");
	if (!field) return;

	// one entry per Rate Master (deduped), same as the dialog
	const rows = frm.doc.docstatus === 0 ? dialog_rows(frm) : [];
	if (!rows.length) {
		field.$wrapper.empty();
		return;
	}

	const items = rows
		.map(
			(r) =>
				`<li>• <b>${esc(r.rm)}</b> (${esc(r.rm_code)}) · ${format_currency(
					r.old_rate
				)} → ` +
				`<b style="color:var(--orange-600);">${format_currency(r.new_rate)}</b></li>`
		)
		.join("");

	field.$wrapper.html(`
		<div style="padding:12px 16px;border:1px solid var(--yellow-200);background:var(--yellow-50);border-radius:8px;">
			<b>⚠ On Submit: ${rows.length} Rate Master update(s) will be proposed</b>
			<ul style="margin:6px 0 0;padding-left:0;list-style:none;">${items}</ul>
			<div style="margin-top:8px;font-size:11px;color:var(--text-muted);font-style:italic;">
				Rates above ${RM_THRESHOLD_PCT}% of the Rate Master rate trigger the prompt at submit.
				Updating affects future estimates only.
			</div>
		</div>
	`);
}

function show_rate_master_dialog(frm) {
	const d = new frappe.ui.Dialog({
		title: __("Update Rate Master rates?"),
		size: "large",
		fields: [
			{ fieldtype: "HTML", fieldname: "intro" },
			{
				fieldtype: "Table",
				fieldname: "rows",
				cannot_add_rows: 1,
				cannot_delete_rows: 1,
				in_place_edit: 1,
				fields: [
					{
						fieldname: "rm_code",
						fieldtype: "Data",
						label: __("RM Code"),
						hidden: 1,
					},
					{
						fieldname: "rm",
						fieldtype: "Data",
						label: __("Rate Master"),
						read_only: 1,
						in_list_view: 1,
					},
					{
						fieldname: "items",
						fieldtype: "Data",
						label: __("Items in PO"),
						read_only: 1,
						in_list_view: 1,
					},
					{
						fieldname: "old_rate",
						fieldtype: "Currency",
						label: __("Old rate"),
						read_only: 1,
						in_list_view: 1,
					},
					{
						fieldname: "new_rate",
						fieldtype: "Currency",
						label: __("New rate"),
						in_list_view: 1,
					},
					{
						fieldname: "delta",
						fieldtype: "Data",
						label: "Δ",
						read_only: 1,
						in_list_view: 1,
					},
				],
			},
		],
		primary_action_label: __("Update rates"),
		primary_action() {
			const selected = d.fields_dict.rows.grid.get_selected_children();
			if (!selected.length) {
				frappe.msgprint(__("Tick at least one row to update."));
				return;
			}

			// checked rows, each carries a clean { rate_master, new_rate } for the server
			const updates = selected.map((r) => ({
				rate_master: r.rm_code,
				new_rate: flt(r.new_rate),
			}));

			d.hide();
			frm.__rm_handled = true;

			// submit first — rates change only if the PO actually goes through,
			// and the submitted PO can be linked in the rate history.
			frm.save("Submit")
				.then(() =>
					frappe.call({
						method: "buildsuite_core.api.rate_master.update_rates_from_po",
						args: {
							purchase_order: frm.doc.name,
							supplier: frm.doc.supplier,
							updates,
						},
						freeze: true,
						freeze_message: __("Updating Rate Masters…"),
					})
				)
				.then((r) => {
					const changed = (r && r.message) || [];
					if (changed.length) {
						frappe.show_alert({
							message: __("Updated {0} Rate Master(s).", [changed.length]),
							indicator: "green",
						});
					}
				})
				.catch(() => {
					// submit failed → let the user retry the whole flow (dialog + update)
					frm.__rm_handled = false;
				});
		},
		secondary_action_label: __("Skip"),
		secondary_action() {
			d.hide();
		},
	});

	d.fields_dict.intro.$wrapper.html(`
		<div style="padding:10px 12px;border:1px solid var(--border-color);background:var(--bg-light-gray);border-radius:6px;font-size:12px;">
			<b>${__("What this does")}</b>
			<ul style="margin:6px 0 0;padding-left:16px;">
				<li>${__("Updates the current Rate Master rate for each ticked row to the new value.")}</li>
				<li>${__("Records an audit row (old → new, source PO, user) in the rate history.")}</li>
				<li>${__("Affects future estimates only — existing BOQs keep their snapshot rates.")}</li>
				<li>${__("Untick a row to skip it; edit New rate if you don't want the full PO rate.")}</li>
			</ul>
		</div>
	`);

	d.fields_dict.rows.df.data = dialog_rows(frm);

	d.fields_dict.rows.grid.refresh();

	d.show();
}
