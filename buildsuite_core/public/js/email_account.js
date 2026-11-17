// Adds "Resend" to the Email Account service presets. Core's email_account.js loads first and
// defines frappe.email_defaults; the service handler there copies these onto the form.
frappe.email_defaults = frappe.email_defaults || {};
frappe.email_defaults["Resend"] = {
	enable_incoming: 0,
	enable_outgoing: 1,
	use_imap: 0,
	login_id_is_different: 1,
	login_id: "resend",
	smtp_server: "smtp.resend.com",
	// 2587, not 587: same relay, but not filtered by networks that block the standard SMTP ports.
	smtp_port: 2587,
	use_tls: 1,
	use_ssl_for_outgoing: 0,
	always_use_account_email_id_as_sender: 1,
};

frappe.ui.form.on("Email Account", {
	refresh(frm) {
		const resend = frm.doc.service === "Resend";
		frm.set_df_property("password", "label", resend ? __("API Key") : __("Password"));
	},
	service(frm) {
		frm.trigger("refresh");
	},
});

// Show this account's own webhook URL — each Resend account has its own endpoint and secret.
frappe.ui.form.on("Email Account", {
	refresh(frm) {
		const wrapper = frm.fields_dict.resend_help && frm.fields_dict.resend_help.$wrapper;
		if (!wrapper || frm.doc.service !== "Resend") return;
		const url = frm.is_new()
			? __("Save the account first to get its webhook URL.")
			: `${
					window.location.origin
			  }/api/method/buildsuite_core.api.resend.webhook?account=${encodeURIComponent(
					frm.doc.name
			  )}`;
		wrapper.find(".resend-webhook").remove();
		wrapper.append(
			`<p class="resend-webhook text-muted">${__("Webhook URL")} (${__(
				"add in Resend → Webhooks, events: all email.*"
			)}):<br><code>${frappe.utils.escape_html(url)}</code></p>`
		);
	},
});
