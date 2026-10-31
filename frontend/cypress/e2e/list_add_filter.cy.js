// "+ Add filter" on the hand-built lists. These lists sit directly on DeskList (not
// DocTypeListView) and used to render the button with nothing behind it. DeskList now owns the
// Frappe-style dynamic filter when given a doctype, and a server-paged list hands it a
// server-mode instance. Guards that every one of them opens a working editor, and that applying a
// filter narrows the rows (client intersect + server-paged) and removing it restores them.

const LISTS = [
	["Progress entries", "/progress-entries"],
	["BOQ", "/boq"],
	["Rate master", "/rate-master"],
	["Material consumption", "/material-consumption"],
	["Subcontractors", "/subcontractors"],
	["Subcontractor bills", "/subcontractor-bills"],
	["Machinery register", "/machinery"],
	["Machinery usage", "/machinery-usage"],
	["Petty cash", "/project-finance/petty-cash"],
	["Customers", "/customers"],
	["Suppliers", "/project-finance/suppliers"],
];

const openEditor = () => {
	cy.contains("button", "+ Add filter").should("be.visible").click();
	cy.contains("button", "Apply").should("be.visible");
};

// Filter on the standard ID field: Field -> "ID", value -> text, Apply. The editor opens with its
// first field preselected, so open the field picker from the editor's first control.
const applyIdFilter = (value) => {
	openEditor();
	cy.contains("button", "Apply").closest(".shadow-lg").find("button").first().click();
	cy.get('input[placeholder="Search fields…"]').type("ID");
	cy.contains("button span.truncate", /^ID$/).click();
	cy.get('input[placeholder="Value"]').type(value);
	cy.contains("button", "Apply").click();
};

// Filter on the Project link by the project's NAME. A record is identified by its ID (PROJ-1644)
// but people know it by name ("SC Demo — Riverside Residency"): the picker must search and show the
// name, and the applied chip must read as the name — on both DeskList and the generic list.
const applyProjectNameFilter = (fragment, name) => {
	openEditor();
	cy.contains("button", "Apply").closest(".shadow-lg").find("button").first().click();
	cy.get('input[placeholder="Search fields…"]').type("Project");
	cy.contains("button span.truncate", /^Project$/).click();
	// value picker: search by name, pick the option showing the name (not the ID)
	cy.contains("button", "Apply").closest(".shadow-lg").contains("button", "Select…").click();
	cy.get(".desk-link-picker-popover input").type(fragment);
	cy.get(".desk-link-picker-popover").contains(name).click();
	cy.contains("button", "Apply").click();
	cy.contains(`Project = ${name}`).should("be.visible");
	cy.contains("Project = PROJ-").should("not.exist");
};

describe("Add filter on the hand-built lists", () => {
	beforeEach(() => cy.login());

	LISTS.forEach(([label, path]) => {
		it(`${label}: Add filter opens the editor`, () => {
			cy.visitApp(path);
			cy.dt("desk-list").should("exist");
			openEditor();
			cy.contains("button", "Cancel").click();
			cy.contains("button", "Apply").should("not.exist");
		});
	});

	// Client-side list: filters are evaluated by Frappe and intersected with the loaded rows.
	it("Subcontractor bills: a filter narrows the rows and removing it restores them", () => {
		cy.visitApp("/subcontractor-bills");
		// Wait for real data — the table shows a "Loading…" placeholder row first.
		cy.dt("desk-list").contains("SB-2026-").should("be.visible");
		cy.dt("desk-list").find("tbody tr").its("length").as("before");
		applyIdFilter("NO-SUCH-BILL");
		cy.contains("ID = NO-SUCH-BILL").should("be.visible");
		cy.dt("desk-list").should("not.contain.text", "SB-2026-");
		cy.contains("ID = NO-SUCH-BILL").parent().find("button").click();
		cy.contains("ID = NO-SUCH-BILL").should("not.exist");
		cy.dt("desk-list").contains("SB-2026-").should("be.visible");
		cy.get("@before").then((n) =>
			cy.dt("desk-list").find("tbody tr").should("have.length", n)
		);
	});

	// Server-paged list: the filter rides with the API query and resets to page 1.
	it("Rate master: a filter is applied by the server and removing it restores the list", () => {
		cy.visitApp("/rate-master");
		cy.dt("desk-list").contains("button", "Add filter").should("exist");
		cy.dt("desk-list").find("tbody tr").its("length").should("be.gt", 1);
		cy.intercept("POST", "**/buildsuite_core.api.rate_master.list_rate_masters*").as("rates");
		applyIdFilter("NO-SUCH-RATE");
		cy.wait("@rates").its("request.body").should("have.property", "filters");
		cy.contains("ID = NO-SUCH-RATE").should("be.visible");
		cy.dt("desk-list").find("tbody tr").should("have.length", 1); // the empty-state row
		cy.contains("ID = NO-SUCH-RATE").parent().find("button").click();
		cy.dt("desk-list").find("tbody tr").its("length").should("be.gt", 1);
	});

	it("Subcontractor bills (DeskList): the Project filter searches and shows the project name", () => {
		cy.visitApp("/subcontractor-bills");
		cy.dt("desk-list").contains("SB-2026-").should("be.visible");
		applyProjectNameFilter("Riverside", "SC Demo — Riverside Residency");
		// only that project's bills remain
		cy.dt("desk-list").should("contain.text", "Riverside Residency");
		cy.dt("desk-list").should("not.contain.text", "Project Seed 2");
	});

	it("Tasks (generic DocTypeListView): the Project filter searches and shows the project name", () => {
		cy.visitApp("/tasks");
		cy.dt("desk-list").should("exist");
		applyProjectNameFilter("Riverside", "SC Demo — Riverside Residency");
	});
});
