// Create a Commercial project through the UI and verify the backend
// template-seeding hook populated its Stage Planning tab.
//
// NOTE: this exercises link-picker popovers + the after_insert seeding hook —
// verify selectors against the running app on first run and adjust if frappe-ui's
// Autocomplete popover markup differs from cy.fillLink's assumptions.

describe('Create project from template', () => {
  it('seeds Stage Planning from the Commercial template', () => {
    const stamp = Date.now()
    cy.login()
    cy.visitApp('/projects')

    cy.dt('page-actions').contains('New').click()
    cy.location('pathname').should('include', '/projects/new')

    cy.dt('field-name').type(`Cypress Project ${stamp}`)
    cy.dt('field-code').type(`CYP-${stamp}`)
    cy.fillLink('pick-project-type', 'Commercial')

    cy.dt('save-btn').click()

    // Lands on the new project's detail page.
    cy.location('pathname', { timeout: 30000 }).should('match', /\/projects\/.+/)
    cy.dt('page-title').should('contain', `Cypress Project ${stamp}`)

    // The seed_from_template_on_insert hook created stages for the Commercial type.
    cy.contains('button', 'Stage Planning').click()
    cy.contains('Foundation').should('be.visible')
  })
})
