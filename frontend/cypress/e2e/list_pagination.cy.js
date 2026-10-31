// One pagination rule for every list: the pager appears only once there is more than the smallest
// page size (10) of rows — whether the list pages on the client (DeskList, the bespoke tables) or on
// the server (DocTypeListView). Server-paged lists used to show it from the first row. Payments and
// Bank & Cash Accounts had no pager at all; Companies is now a DocTypeListView.

const PAGER = "Rows per page";
const search = (text) => cy.dt("list-search").first().clear().type(text);

describe("Pagination is consistent across lists", () => {
	beforeEach(() => cy.login());

	it("Companies (server-paged): pager past 10 rows, gone when a search leaves few", () => {
		cy.visitApp("/settings/companies");
		cy.dt("desk-list").contains("tbody tr", /\S/).should("be.visible");
		cy.contains(PAGER).should("be.visible");
		search("XCorp");
		cy.dt("desk-list").contains("XCorp").should("be.visible");
		cy.contains(PAGER).should("not.exist");
	});

	it("BOQ (server-paged): the pager also drops away when the result is small", () => {
		cy.visitApp("/boq");
		cy.dt("desk-list").contains("BOQ-").should("be.visible");
		cy.contains(PAGER).should("be.visible");
		search("BOQ-00178");
		cy.dt("desk-list").contains("BOQ-00178").should("be.visible");
		cy.contains(PAGER).should("not.exist");
	});

	it("Payments: paged past 10, and a narrowing filter drops the pager", () => {
		cy.visitApp("/project-finance/payments");
		cy.dt("pager-next").should("be.visible");
		cy.contains(PAGER).should("be.visible");
		cy.contains(/Showing\s+1–10 of/).should("be.visible");
		cy.dt("pager-next").click();
		cy.contains(/Showing\s+11–/).should("be.visible");
		// a search that leaves <= 10 rows: no pager
		cy.get('input[placeholder^="Search type, party"]').type("zzzz-no-match-zzzz");
		cy.contains(PAGER).should("not.exist");
	});

	it("Bank & Cash Accounts: no pager for a short list, paged once past 10", () => {
		// the working company's real accounts are few: no pager
		cy.visitApp("/settings/finance-accounts");
		cy.contains("Opening balance").should("be.visible");
		cy.contains(PAGER).should("not.exist");

		// a company with many accounts: stub 25 and the pager appears
		const accounts = Array.from({ length: 25 }, (_, i) => ({
			id: `ACC-${i + 1}`,
			name: `Account ${String(i + 1).padStart(2, "0")}`,
			type: i % 2 ? "Cash" : "Bank",
			account_no: "",
			opening_balance: 0,
			current_balance: i * 100,
		}));
		cy.intercept("POST", "**/buildsuite_core.api.finance_account.list_finance_accounts*", {
			body: { message: accounts },
		}).as("accounts");
		cy.visitApp("/settings/finance-accounts");
		cy.wait("@accounts");
		cy.contains("Account 01").should("be.visible");
		cy.contains(/Showing\s+1–10 of\s+25/).should("be.visible");
		cy.contains("Account 11").should("not.exist");
		cy.dt("pager-next").click();
		cy.contains(/Showing\s+11–20 of\s+25/).should("be.visible");
		cy.contains("Account 11").should("be.visible");
	});
});
