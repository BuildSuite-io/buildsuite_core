// Expenses list: a "Status — Submitted first" sort in the existing sort list, and explicit Holder and
// Account filters. Expected values are derived from the live list_expenses API, so the spec doesn't
// depend on particular demo names.

// The status badge is the last cell of an expense row.
const statuses = ($rows) =>
	[...$rows].map((r) => r.querySelector("td:last-child")?.textContent.trim());

const countLine = (n) => new RegExp(`1-${n} of ${n} records`);

const pick = (testId, label) => {
	cy.dt(testId).find("button").first().click();
	cy.contains(
		"button span.truncate",
		new RegExp(`^${label.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}$`)
	).click();
};

describe("Expenses — sort by status and the Holder / Account filters", () => {
	let expenses;
	beforeEach(() => {
		cy.login();
		cy.request("/api/method/buildsuite_core.api.expense_entry.list_expenses")
			.its("body.message")
			.then((rows) => (expenses = rows));
		cy.visitApp("/project-finance/expenses");
		cy.contains("button", /^All Expenses/).click();
		cy.dt("list-count")
			.contains(/\d+-\d+ of \d+ records/)
			.should("be.visible");
	});

	it("'Status — Submitted first' is in the sort list and puts Submitted rows ahead of Draft", () => {
		cy.contains("select option", "Status — Submitted first").should("exist");
		cy.contains("select", "Entered — newest first").select("Status — Submitted first");
		// every Submitted entry precedes every Draft one across pages: with more Submitted than a page
		// holds, page 1 is all Submitted and the Drafts land on the next page
		const submitted = expenses.filter((e) => e.status === "Submitted").length;
		const drafts = expenses.filter((e) => e.status === "Draft").length;
		expect(submitted, "needs Submitted rows").to.be.greaterThan(0);
		expect(drafts, "needs Draft rows").to.be.greaterThan(0);
		// page 1 holds only Submitted rows (there are more of them than a page) ...
		cy.get("tbody tr").should(($rows) => {
			expect($rows.length, "rows").to.be.greaterThan(0);
			expect(statuses($rows), "page 1 statuses").to.satisfy((st) =>
				st.every((x) => x === "Submitted")
			);
		});
		// ... and the Drafts follow on the next page
		cy.dt("pager-next").click();
		cy.get("tbody tr").should(($rows) => {
			const st = statuses($rows);
			expect(st, "page 2 statuses").to.include("Draft");
			// Submitted still precedes Draft within the page
			expect(st.lastIndexOf("Submitted"), "Submitted before Draft").to.be.lessThan(
				st.indexOf("Draft")
			);
		});
	});

	it("the Holder filter narrows to one holder", () => {
		const holder = expenses[0];
		const expected = expenses.filter((e) => e.employee === holder.employee).length;
		pick("filter-holder", holder.employee_name);
		cy.contains(countLine(expected)).should("be.visible");
		cy.get("tbody tr").each(($tr) => expect($tr.text()).to.include(holder.employee_name));
	});

	it("the Account filter narrows to one expense account", () => {
		const account = expenses.find((e) => e.expense_account).expense_account;
		const expected = expenses.filter((e) => e.expense_account === account).length;
		pick("filter-account", account);
		cy.contains(countLine(expected)).should("be.visible");
		cy.get("tbody tr").each(($tr) => expect($tr.text()).to.include(account));
	});

	it("Clear filters resets Holder and Account", () => {
		pick("filter-holder", expenses[0].employee_name);
		cy.contains("button", "Clear filters").click();
		cy.contains(new RegExp(`1-\\d+ of ${expenses.length} records`)).should("be.visible");
	});

	it("'Submitted first' orders the entries within a status by last modified, as Desk does", () => {
		const submitted = expenses
			.filter((e) => e.status === "Submitted")
			.sort((a, b) => b.modified.localeCompare(a.modified) || b.name.localeCompare(a.name));
		expect(submitted.length, "needs Submitted rows").to.be.greaterThan(1);
		cy.contains("select", "Entered — newest first").select("Status — Submitted first");
		cy.get("tbody tr")
			.first()
			.should("contain.text", submitted[0].description || submitted[0].name);
	});

	it("the search finds an entry by its amount, typed with or without separators", () => {
		const target = expenses.find((e) => Number(e.amount) >= 1000);
		expect(target, "needs an entry of 1,000 or more").to.exist;
		const digits = String(Number(target.amount));
		const expected = expenses.filter((e) =>
			[String(Number(e.amount)), Number(e.amount).toFixed(2)].some((s) => s.includes(digits))
		).length;
		cy.get("input[placeholder*='amount']").type(digits);
		cy.contains(countLine(expected)).should("be.visible");
		cy.get("input[placeholder*='amount']")
			.clear()
			.type(Number(target.amount).toLocaleString("en-IN"));
		cy.get("tbody tr").should("have.length.greaterThan", 0);
		cy.get("tbody tr").should("contain.text", target.description || target.name);
	});
});
