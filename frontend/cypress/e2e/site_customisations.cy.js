// Site-level customisations (SDK phase 4): records of "BuildSuite Customisation" turn into list
// columns, form fields, workspace tiles and notices with no code and no installed app.

const DT = "BuildSuite Customisation";

describe("Site-level customisations", () => {
	const created = []; // [url] to delete afterwards

	function api(method, url, body) {
		return cy
			.window()
			.its("csrf_token")
			.then((token) =>
				cy.request({
					method,
					url,
					headers: { "X-Frappe-CSRF-Token": token },
					body,
					failOnStatusCode: false,
				})
			);
	}

	function customise(title, kind, config, extra = {}) {
		return api("POST", `/api/resource/${DT}`, {
			title,
			kind,
			config: JSON.stringify(config),
			...extra,
		}).then((res) => {
			expect(res.status, JSON.stringify(res.body).slice(0, 300)).to.eq(200);
			created.push(`/api/resource/${DT}/${encodeURIComponent(title)}`);
		});
	}

	beforeEach(() => {
		cy.login();
		cy.visitApp("/"); // a loaded page, for the CSRF token
	});

	afterEach(() => {
		cy.visitApp("/");
		created.splice(0).forEach((url) => api("DELETE", url));
	});

	it("a notice shows in its slot, as text and never as HTML", () => {
		const t = `site notice ${Date.now()}`;
		customise(t, "Notice", {
			slot: "page.app-home.top",
			message: "Closed Friday <b>early</b>",
			tone: "warning",
		});
		cy.visitApp("/");
		cy.get("[data-test=site-notice]")
			.should("contain.text", "Closed Friday <b>early</b>")
			.find("b")
			.should("not.exist");
	});

	it("a disabled customisation does nothing", () => {
		const t = `site off ${Date.now()}`;
		customise(
			t,
			"Notice",
			{ slot: "page.app-home.top", message: "Should not appear" },
			{ enabled: 0 }
		);
		cy.visitApp("/");
		cy.get("[data-test=demo-home-notice]").should("be.visible"); // the page has loaded
		cy.contains("Should not appear").should("not.exist");
	});

	it("a list column shows on that DocType's lists", () => {
		const t = `site column ${Date.now()}`;
		customise(t, "List Column", {
			doctype: "Project",
			field: "creation",
			label: "Created (site)",
		});
		cy.visitApp("/projects");
		cy.get('[data-test="desk-list"] thead').contains("th", "Created (site)");
	});

	it("a workspace tile shows on the workspace", () => {
		const t = `site tile ${Date.now()}`;
		customise(t, "Workspace Tile", {
			workspace: "sales",
			label: "Site tile",
			to: "/projects",
			description: "Added with no code",
		});
		cy.visitApp("/sales");
		cy.contains("a", "Site tile").click();
		cy.location("pathname").should("include", "/projects");
	});

	it("an invalid record is refused by the server", () => {
		api("POST", `/api/resource/${DT}`, {
			title: `site bad ${Date.now()}`,
			kind: "Workspace Tile",
			config: JSON.stringify({ workspace: "sales", label: "x", to: "https://evil.example" }),
		})
			.its("status")
			.should("eq", 417);
	});

	it("a Custom Field gets a control on a bespoke form with no code, and its value is saved", () => {
		const stamp = Date.now();
		const cf = "Estimate Template-site_note";
		api("POST", "/api/resource/Custom Field", {
			dt: "Estimate Template",
			fieldname: "site_note",
			fieldtype: "Data",
			label: "Site note",
		}).then((res) => {
			expect(res.status, JSON.stringify(res.body).slice(0, 300)).to.eq(200);
			created.push(`/api/resource/Custom Field/${encodeURIComponent(cf)}`);
		});
		// Registered after the custom field, so the afterEach deletes the customisation first.
		customise(`site field ${stamp}`, "Form Field", {
			doctype: "Estimate Template",
			fieldname: "site_note",
			position: "top",
		});
		cy.visitApp("/estimate-template/new");
		cy.get('input[placeholder="ET-..."]').type(`ET-SITE-${stamp}`);
		cy.contains("label", /^\s*Name/)
			.parent()
			.find("input")
			.type(`Site Template ${stamp}`);
		cy.get("[data-test=site-field-site_note] input")
			.should("be.visible")
			.type("From the site layer");
		cy.dt("save-btn").click();
		cy.location("pathname", { timeout: 30000 }).should(
			"match",
			/\/estimate-template\/(?!new)[^/]+$/
		);
		cy.location("pathname").then((path) => {
			const id = decodeURIComponent(path.split("/").pop());
			cy.request(`/api/resource/Estimate Template/${encodeURIComponent(id)}`).then((res) => {
				expect(res.body.data.site_note).to.equal("From the site layer");
			});
		});
	});
});
