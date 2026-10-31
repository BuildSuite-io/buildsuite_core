// Progress entries, BOQ and Petty cash now run on the generic DocTypeListView (server paging, sort
// and the Add-filter editor) instead of hand-built DeskLists. Guards what those screens did by
// hand: KPI strips from server counts, name-based search (linked records are found by their NAME,
// not just their ID), the list-specific chips, and server-side paging.

const apiGet = (method, params) =>
	cy.request({ url: `/api/method/${method}`, qs: params }).its("body.message");

const jsonParams = (o) =>
	Object.fromEntries(
		Object.entries(o).map(([k, v]) => [k, typeof v === "string" ? v : JSON.stringify(v)])
	);

describe("Progress entries on DocTypeListView", () => {
	beforeEach(() => cy.login());

	it("shows KPIs and rows from the server", () => {
		cy.visitApp("/progress-entries");
		cy.contains("Total entries").parent().should("not.contain.text", "—");
		cy.dt("desk-list").contains("TPE-").should("be.visible");
		cy.contains("button", "+ Add filter").should("be.visible");
	});

	it("finds an entry by the NAME of its task, not just the task ID", () => {
		apiGet(
			"frappe.client.get_list",
			jsonParams({
				doctype: "Task Progress Entry",
				fields: ["name", "task"],
				limit_page_length: 1,
			})
		).then(([entry]) => {
			apiGet("frappe.client.get_value", {
				doctype: "Task",
				filters: entry.task,
				fieldname: "subject",
			}).then(({ subject }) => {
				cy.visitApp("/progress-entries");
				cy.dt("desk-list").contains("TPE-").should("be.visible");
				cy.dt("desk-list")
					.find('input[data-test="list-search"]')
					.type(subject.slice(0, 12));
				cy.dt("desk-list").contains(entry.name).should("be.visible");
			});
		});
	});

	it("the blockers-only toggle narrows the list on the server", () => {
		cy.visitApp("/progress-entries");
		cy.dt("desk-list").contains("TPE-").should("be.visible");
		cy.contains("button", "Blockers only").click();
		cy.contains("Blockers").should("be.visible");
		// retries until the filtered refetch lands: every remaining row carries a blocker flag
		cy.dt("desk-list").should(($list) => {
			const rows = $list.find("tbody tr").filter((_, tr) => tr.textContent.includes("TPE-"));
			expect(rows.length, "rows").to.be.greaterThan(0);
			rows.each((_, tr) => expect(tr.textContent).to.include("Blocker"));
		});
	});
});

describe("BOQ on DocTypeListView", () => {
	beforeEach(() => cy.login());

	it("shows the KPI strip and rows from the server", () => {
		cy.visitApp("/boq");
		cy.contains("Approved").parent().should("not.contain.text", "—");
		cy.dt("desk-list").contains("BOQ-").should("be.visible");
		cy.contains("button", "+ Add filter").should("be.visible");
	});

	it("finds a BOQ by its project's NAME", () => {
		apiGet(
			"frappe.client.get_list",
			jsonParams({
				doctype: "BOQ",
				fields: ["name", "project"],
				filters: [["project", "is", "set"]],
				limit_page_length: 1,
			})
		).then(([boq]) => {
			apiGet("frappe.client.get_value", {
				doctype: "Project",
				filters: boq.project,
				fieldname: "project_name",
			}).then(({ project_name }) => {
				cy.visitApp("/boq");
				cy.dt("desk-list").contains("BOQ-").should("be.visible");
				cy.dt("desk-list")
					.find('input[data-test="list-search"]')
					.type(project_name.slice(0, 10));
				cy.dt("desk-list").contains(boq.name).should("be.visible");
			});
		});
	});

	it("finds an estimate by its customer's NAME", () => {
		apiGet(
			"frappe.client.get_list",
			jsonParams({
				doctype: "BOQ",
				fields: ["name", "customer"],
				filters: [
					["project", "is", "not set"],
					["customer", "is", "set"],
				],
				limit_page_length: 1,
			})
		).then((rows) => {
			if (!rows.length) return; // no priced-for-a-customer estimate on this site
			const [est] = rows;
			apiGet("frappe.client.get_value", {
				doctype: "Customer",
				filters: est.customer,
				fieldname: "customer_name",
			}).then(({ customer_name }) => {
				cy.visitApp("/boq");
				cy.dt("desk-list").contains("BOQ-").should("be.visible");
				cy.dt("desk-list")
					.find('input[data-test="list-search"]')
					.type(customer_name.slice(0, 8));
				cy.dt("desk-list").contains(est.name).should("be.visible");
			});
		});
	});

	it("the scope filter narrows to estimates on the server", () => {
		cy.visitApp("/boq");
		cy.dt("desk-list").contains("BOQ-").should("be.visible");
		cy.get("select").first().select("Estimates only");
		// retries until the filtered refetch lands: every remaining row is an estimate
		cy.dt("desk-list").should(($list) => {
			const rows = $list.find("tbody tr").filter((_, tr) => tr.textContent.includes("BOQ-"));
			expect(rows.length, "rows").to.be.greaterThan(0);
			rows.each((_, tr) => expect(tr.textContent).to.include("Estimate"));
		});
	});
});

describe("Petty cash on DocTypeListView", () => {
	beforeEach(() => cy.login());

	const openAllTab = () => {
		cy.visitApp("/project-finance/petty-cash");
		cy.contains("button", /^All Requests/).click();
		cy.dt("desk-list").contains("PCR-").should("be.visible");
	};

	it("the All Requests tab badge is the server count and the rows come from the server", () => {
		apiGet("frappe.client.get_count", jsonParams({ doctype: "Petty Cash Request" })).then(
			(total) => {
				cy.visitApp("/project-finance/petty-cash");
				cy.contains("button", new RegExp(`^All Requests\\s*\\(${total}\\)`)).click();
				cy.dt("desk-list").contains("PCR-").should("be.visible");
				cy.contains("button", "+ Add filter").should("be.visible");
			}
		);
	});

	it("finds a request by its holder's NAME, not just their user ID", () => {
		apiGet(
			"frappe.client.get_list",
			jsonParams({
				doctype: "Petty Cash Request",
				fields: ["name", "requested_by"],
				filters: [["requested_by", "!=", "Administrator"]],
				limit_page_length: 1,
			})
		).then(([req]) => {
			apiGet("frappe.client.get_value", {
				doctype: "User",
				filters: req.requested_by,
				fieldname: "full_name",
			}).then(({ full_name }) => {
				openAllTab();
				cy.dt("desk-list")
					.find('input[data-test="list-search"]')
					.type(full_name.slice(0, 6));
				cy.dt("desk-list").contains(req.name).should("be.visible");
			});
		});
	});

	it("the status chip narrows the list on the server", () => {
		openAllTab();
		cy.get("select").contains("Disbursed").parent().select("Disbursed");
		cy.dt("desk-list").should(($list) => {
			const rows = $list.find("tbody tr").filter((_, tr) => tr.textContent.includes("PCR-"));
			expect(rows.length, "rows").to.be.greaterThan(0);
			rows.each((_, tr) => expect(tr.textContent).to.include("Disbursed"));
		});
	});
});
