// Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
// For license information, please see license.txt

const SYNC_FIELDS = ['status', 'overtime_hours', 'comments'];

frappe.ui.form.on("Field Attendance", {
    onload(frm) {
        if (!frm.doc.date) {
            frm.set_value('date', frappe.datetime.get_today());
        }
        set_employee_query(frm);
    },

    refresh(frm) {
        add_bulk_select_button(frm);
    },

    project(frm) {
        frm.clear_custom_buttons();
        add_bulk_select_button(frm);
    },

    // Registered once at module level, not inside onload
    status(frm) { copy_to_rows(frm, 'status'); },
    overtime_hours(frm) { copy_to_rows(frm, 'overtime_hours'); },
    comments(frm) { copy_to_rows(frm, 'comments'); },
});


function copy_to_rows(frm, field) {
    (frm.doc.employee_list || []).forEach(row => {
        row[field] = frm.doc[field];
    });
    frm.refresh_field('employee_list');
}


function add_bulk_select_button(frm) {
    if (!frm.doc.project || frm.doc.docstatus !== 0) return;

    frm.add_custom_button(__('Bulk Select'), function () {
        frappe.call({
            method: 'buildsuite_core.buildsuite_core.doctype.field_attendance.field_attendance.get_employees',
            args: {
                date: frm.doc.date,
                project: frm.doc.project
            },
            callback: function (r) {
                show_bulk_select_dialog(frm, r.message || []);
            }
        });
    });
}


function set_employee_query(frm) {
    frm.fields_dict['employee_list'].grid.get_field('employee').get_query = function (doc, cdt, cdn) {
        const selected_employees = [];

        (doc.employee_list || []).forEach(row => {
            if (row.employee && row.name !== cdn) {
                selected_employees.push(row.employee);
            }
        });

        const hrms_installed = Boolean(frappe.boot.versions && frappe.boot.versions.hrms);

        const labour_filter = hrms_installed
            ? ['Employee', 'employment_type', '=', 'Labour']
            : ['Employee', 'is_labour', '=', 1];

        return {
            filters: [
                labour_filter,
                ['Employee', 'status', '=', 'Active'],
                ['Employee', 'name', 'not in', selected_employees]
            ]
        };
    };
}


function show_bulk_select_dialog(frm, employees) {
    let selected = {};                                   // all unselected by default
    const valid_ids = new Set(employees.map(e => e.name));

    const d = new frappe.ui.Dialog({
        title: __('Bulk Select Employees'),
        size: 'large',
        fields: [
            {
                label: __('Project'),
                fieldname: 'project',
                fieldtype: 'Data',
                default: frm.doc.project_name || frm.doc.project,
                read_only: 1
            },
            {
                label: __('Date'),
                fieldname: 'date',
                fieldtype: 'Date',
                default: frm.doc.date,
                read_only: 1
            },
            {
                label: __('Search Employee'),
                fieldname: 'search',
                fieldtype: 'Data'
            },
            { fieldtype: 'HTML', fieldname: 'employee_html' }
        ],
        primary_action_label: __('Add to Table'),
        primary_action() {
            const employee_names = Object.keys(selected);
            if (!employee_names.length) {
                frappe.msgprint(__('Please select at least one employee.'));
                return;
            }

            const existing = (frm.doc.employee_list || []).map(row => row.employee);

            employee_names.forEach(emp_id => {
                if (existing.includes(emp_id)) return;

                const emp = employees.find(e => e.name === emp_id);
                const row = frm.add_child('employee_list');
                row.employee = emp_id;
                row.employee_name = emp ? emp.employee_name : '';

                // copy parent defaults down
                row.status = frm.doc.status || '';
                row.overtime_hours = frm.doc.overtime_hours || 0;
                row.comments = frm.doc.comments || '';
            });

            frm.refresh_field('employee_list');
            frm.dirty();
            d.hide();
        }
    });

    const current_filter = () => (d.get_value('search') || '').toLowerCase();

    const rerender = () => {
        d.fields_dict.employee_html.$wrapper.html(
            render_employee_checkboxes(employees, current_filter(), selected)
        );
    };

    // Only keep ids that are actually offered in this dialog
    const set_selection = (ids) => {
        selected = {};
        ids.filter(id => valid_ids.has(id)).forEach(id => selected[id] = true);
        rerender();
    };

    d.show();
    rerender();

    // live filtering on keystroke (Data onchange only fires on blur)
    d.fields_dict.search.$input.on('keyup', frappe.utils.debounce(rerender, 150));

    d.fields_dict.employee_html.$wrapper.on('change', 'input[type=checkbox]', function () {
        const emp_id = $(this).data('emp');
        if (this.checked) selected[emp_id] = true;
        else delete selected[emp_id];
    });

    const btn_style = 'margin:10px 0 15px; background-color:#fff; color:#000; border:1px solid #ccc; flex:1;';
    const $buttons = $(`
        <div style="display:flex; gap:10px;">
            <button class="btn btn-sm" data-action="select-all"      style="${btn_style}">${__('Select All')}</button>
            <button class="btn btn-sm" data-action="select-assigned" style="${btn_style}">${__('Select Assigned Employees')}</button>
            <button class="btn btn-sm" data-action="same-as-last"    style="${btn_style}">${__('Same As Last Day')}</button>
            <button class="btn btn-sm" data-action="unselect-all"    style="${btn_style}">${__('Unselect All')}</button>
        </div>
    `);
    d.fields_dict.employee_html.$wrapper.before($buttons);

    $buttons.on('click', 'button', function (e) {
        e.preventDefault();
        const action = $(this).data('action');

        if (action === 'select-all') {
            // respect the active search filter
            filter_employees(employees, current_filter())
                .forEach(emp => selected[emp.name] = true);
            rerender();

        } else if (action === 'unselect-all') {
            selected = {};
            rerender();

        } else if (action === 'same-as-last') {
            frappe.call({
                method: 'buildsuite_core.buildsuite_core.doctype.field_attendance.field_attendance.get_last_day_attendance',
                args: { project: frm.doc.project, current_date: frm.doc.date },
                callback: (r) => set_selection((r.message || []).map(row => row.employee))
            });

        } else if (action === 'select-assigned') {
            frappe.call({
                method: 'buildsuite_core.buildsuite_core.doctype.field_attendance.field_attendance.get_assigned_employees',
                args: { project: frm.doc.project },
                callback: (r) => set_selection(r.message || [])
            });
        }
    });
}


function filter_employees(list, filter) {
    filter = (filter || '').toLowerCase();
    if (!filter) return list;

    return list.filter(emp =>
        (emp.employee_name || '').toLowerCase().includes(filter) ||
        (emp.name || '').toLowerCase().includes(filter)
    );
}


function render_employee_checkboxes(list, filter, selected) {
    const filtered = filter_employees(list, filter);

    if (!filtered.length) {
        return `<div class="text-muted">${__('No employees found.')}</div>`;
    }

    let html = '<div style="display:flex; flex-wrap:wrap; gap:10px;">';

    filtered.forEach(emp => {
        const checked = selected[emp.name] ? 'checked' : '';
        const emp_name = frappe.utils.escape_html(emp.employee_name || '');
        const emp_id = frappe.utils.escape_html(emp.name);

        html += `
            <div style="flex:0 0 48%; display:flex; align-items:center; gap:20px;">
                <input type="checkbox" data-emp="${emp_id}" ${checked}>
                <label style="margin:0; user-select:none;">
                    ${emp_name}<br>
                    ${emp_id}
                </label>
            </div>
        `;
    });

    return html + '</div>';
}