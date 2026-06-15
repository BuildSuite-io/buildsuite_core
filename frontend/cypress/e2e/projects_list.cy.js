// Projects list — search narrows the DeskList, and a row click opens the detail.
// Read-only against seeded backend data; no records created.

describe('Projects list', () => {
  beforeEach(() => {
    cy.login()
    cy.visitApp('/projects')
    cy.dt('desk-list').should('exist')
  })

  it('row click opens the project detail', () => {
    cy.dt('desk-list').find('[data-test-row]').first().click()
    cy.location('pathname').should('match', /\/projects\/.+/)
    cy.dt('page-title').should('be.visible')
  })

  it('search with no match empties the list', () => {
    cy.dt('desk-list').find('[data-test-row]').its('length').should('be.gte', 1)
    cy.dt('list-search').type('zzz-cypress-no-such-project-xyz')
    cy.dt('desk-list').find('[data-test-row]').should('have.length', 0)
  })
})
