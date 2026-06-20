// PTT-005 — re-seeding Stage Planning from the Project Type template on an
// existing project that was created WITHOUT auto-seeded stages.
//
// project_create.cy.js covers the create-time auto-seed path. This spec covers
// the empty-state "+ Seed from <type> template" button: create a Commercial
// project with "Seed default stages" unchecked → the Stage Planning tab is empty
// → click the seed button → stages appear (backend seed_stages_from_template).
//
// NOTE: real-backend e2e — needs the built frontend served by Frappe + the
// Commercial Project Template seeded. Verify selectors on first run.

describe('Re-seed Stage Planning from template', () => {
  it('seeds stages on an empty project via the empty-state button', () => {
    const stamp = Date.now()
    cy.login()
    cy.visitApp('/projects')

    cy.dt('page-actions').contains('New').click()
    cy.location('pathname').should('include', '/projects/new')

    cy.dt('field-name').type(`Cypress Reseed ${stamp}`)
    cy.dt('field-code').type(`CYR-${stamp}`)
    cy.fillLink('pick-project-type', 'Commercial')
    cy.fillLink('pick-company')

    // Opt OUT of create-time seeding so the project lands with zero stages.
    cy.contains('label', 'Seed default stages').find('input[type="checkbox"]').uncheck()

    cy.dt('save-btn').click()
    cy.location('pathname', { timeout: 30000 }).should('match', /\/projects\/.+/)

    // Stage Planning tab is empty — the seed button + preview are shown.
    cy.contains('button', 'Stage Planning').click()
    cy.contains('No stages planned yet.').should('be.visible')
    cy.contains('button', /Seed from Commercial template/i).click()

    // Confirm the "seed N stages" dialog, then the seeded stages render.
    cy.confirmAccept()
    cy.contains('Foundation', { timeout: 30000 }).should('be.visible')
  })
})
