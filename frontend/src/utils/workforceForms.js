// Client-side validation for the Workforce forms, shared by each entity's New
// and Detail screens. A courtesy only — the server owns the real rules. Each
// returns a { fieldname: message } map for useFormErrors().

// Frappe docstatus -> label, for the attendance list and detail views.
export const DOCSTATUS_LABELS = { 0: "Draft", 1: "Submitted", 2: "Cancelled" };

// Mirrors the Select on Field Attendance and Field Attendance Employee.
// Note: "Overtime Only" and "Half Day" + overtime save fine as drafts but the
// controller cannot submit them today — see api/field_attendance.py.
export const ATTENDANCE_STATUSES = ["Present", "Half Day", "Absent", "Overtime Only"];

export function validateFieldAttendance(form) {
	const errors = {};
	if (!form.project) errors.project = "Project is required.";
	if (!form.date) errors.date = "Date is required.";
	if (!form.employee_list?.length) {
		errors.employee_list = "Add at least one employee (use Bulk select).";
	} else if (form.employee_list.some((r) => !r.employee)) {
		errors.employee_list = "Every row needs a worker.";
	}
	return errors;
}

export function validateCrew(form) {
	const errors = {};
	if (!form.crew_name?.trim()) errors.crew_name = "Crew name is required.";
	if (!form.company) errors.company = "Company is required.";
	return errors;
}

export function validateFieldEmployee(form) {
	const errors = {};
	if (!form.first_name?.trim()) errors.first_name = "First name is required.";
	if (!form.gender) errors.gender = "Gender is required.";
	if (!form.date_of_birth) errors.date_of_birth = "Date of birth is required.";
	if (!form.date_of_joining) errors.date_of_joining = "Date of joining is required.";
	if (!form.company) errors.company = "Company is required.";
	// `custom_wage` is mandatory while `is_labour` is set, which it always is here.
	if (!form.custom_wage) errors.custom_wage = "Daily wage is required.";

	// Checked on its own, not chained to the wage rule — a blank wage used to
	// hide this error entirely.
	if (form.date_of_birth && form.date_of_joining && form.date_of_birth > form.date_of_joining) {
		errors.date_of_birth = "Date of birth must be on or before the joining date.";
	}

	return errors;
}
