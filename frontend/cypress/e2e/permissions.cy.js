// Permission gating — the UI affordances follow the logged-in persona (the
// usePermissions / PERSONA_CAPS layer). Estimator is read-only on Project; admin
// has full CRUD. The authoritative backend enforcement is separate (proven by the
// permissions/*.py hooks + the on-load probe earlier).
//
// Requires the persona test users (bench execute
// buildsuite_core.api.cypress_setup.ensure_cypress_users).

describe('Permission gating follows persona', () => {
  it('estimator sees Projects read-only (no + New)', () => {
    cy.loginAs('estimator')
    cy.visitApp('/projects')
    cy.dt('page-title').should('be.visible')             // can read the list
    cy.dt('page-actions').should('not.contain', 'New')   // but no create affordance
  })

  it('admin sees the + New affordance on Projects', () => {
    cy.loginAs('admin')
    cy.visitApp('/projects')
    cy.dt('page-actions').contains('New').should('be.visible')
  })
})
