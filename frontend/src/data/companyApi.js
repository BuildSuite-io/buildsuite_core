import { frappeRequest } from "frappe-ui-frappe-request";
import { parseFrappeError } from "@/utils/frappeError";

async function call(method, params) {
	try {
		return await frappeRequest({
			url: `buildsuite_core.api.company.${method}`,
			params: params || {},
		});
	} catch (err) {
		throw new Error(parseFrappeError(err).summary || "Request failed.");
	}
}

// The logged-in user's default company (User → user default → site default).
export const getActiveCompany = () => call("active_company");

// Every company for the SPA list + topbar switcher, mapped to `[{id, name, abbr, logo, is_default}]`.
export const listCompanies = () => call("list_companies");

// Set the working company server-side (persists it as the user's default Company). Returns the name.
export const setActiveCompanyRemote = (company) => call("set_active_company", { company });

// Company branding — logo + letter-head subtext for the default company. These drive the
// shared Letter Head that every print format renders, so editing them here re-brands all
// prints (server rebuilds the letter head on save).
export const getCompanyContext = () => call("company_context");
export const getCompanyProjects = (company) => call("company_projects", { company });
export const getCompanyBranding = (company) =>
	call("company_branding", company ? { company } : {});
export const updateCompanyBranding = (payload) => call("update_company_branding", payload);

// Upload the logo via Frappe's multipart upload_file endpoint. Public (is_private=0) so the
// image resolves in server-rendered PDFs. Returns the file_url to store on the company.
export async function uploadCompanyLogo(file) {
	const fd = new FormData();
	fd.append("file", file, file.name);
	fd.append("is_private", "0");
	fd.append("folder", "Home");
	// No Content-Type header — the browser sets the multipart boundary itself.
	const res = await fetch("/api/method/upload_file", {
		method: "POST",
		credentials: "include",
		headers: { "X-Frappe-CSRF-Token": window.csrf_token || "" },
		body: fd,
	});
	if (!res.ok) {
		let msg = "Upload failed.";
		try {
			const j = await res.json();
			if (j._server_messages) msg = JSON.parse(j._server_messages)[0];
		} catch {
			/* keep default */
		}
		throw new Error(msg);
	}
	const data = await res.json();
	return data?.message?.file_url || "";
}
