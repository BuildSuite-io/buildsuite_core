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

  // PRM-005 — Settings is restricted to System Manager + BuildSuite Administrator.
  it('estimator hitting Settings sees the restricted notice', () => {
    cy.loginAs('estimator')
    cy.visitApp('/settings')
    cy.contains('Settings is restricted to administrators.').should('be.visible')
  })

  it('admin sees the Settings hub (not restricted)', () => {
    cy.loginAs('admin')
    cy.visitApp('/settings')
    cy.contains('Settings is restricted to administrators.').should('not.exist')
  })

  // PRM-014 — Procurement Officer has no Stage Planning / Task Progress Entry
  // access; the lists render a restricted notice instead of the data.
  it('procurement is blocked from the Stage Planning + TPE lists', () => {
    cy.loginAs('procurement')

    cy.visitApp('/stage-plannings')
    cy.contains("You don't have access to Stage Planning.").should('be.visible')

    cy.visitApp('/progress-entries')
    cy.contains("You don't have access to Task Progress Entries.").should('be.visible')
  })
})
