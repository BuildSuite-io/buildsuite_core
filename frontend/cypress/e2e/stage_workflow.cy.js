// The Stage Planning approval workflow end-to-end against the real Frappe Workflow
// (apply_workflow + reject_stage_planning). Creates a fresh Draft stage per run via
// the 2-step wizard so the spec is repeatable, then drives the transitions.
//
// NOTE: the wizard's project picker + task-picker step and the workflow action
// buttons are driven via the stable hooks (pick-project, field-stage-name,
// page-actions text, reject-* ). Verify the wizard step transitions against the
// running app on first run (the StageTaskPicker "Create Stage" step may require a
// task selection depending on validation).

function createDraftStage(stamp) {
  cy.visitApp('/stage-plannings')
  cy.dt('page-actions').contains('New').click()
  cy.location('pathname').should('include', '/stage-plannings/new')

  // Step 1 — details
  cy.dt('field-stage-name').type(`Cypress Stage ${stamp}`)
  cy.fillLink('pick-project', 'PROJ')          // first project match
  cy.contains('button', /Next/i).click()

  // Step 2 — task picker (create with whatever's allowed)
  cy.contains('button', /Create Stage/i).click()

  cy.location('pathname', { timeout: 30000 }).should('match', /\/stage-plannings\/.+/)
}

describe('Stage Planning approval workflow', () => {
  it('Draft -> Submit -> Approve', () => {
    cy.loginAs('pm')                 // PM can submit + approve (self-approval allowed)
    createDraftStage(Date.now())

    // Submit + Approve apply the workflow directly on click (no confirm dialog) —
    // the new state badge is the gate.
    cy.dt('page-actions').contains('Submit for Approval').click()
    cy.contains('Pending Approval').should('be.visible')

    cy.dt('page-actions').contains('Approve').click()
    cy.contains('Approved').should('be.visible')
  })

  it('Draft -> Submit -> Reject (with reason)', () => {
    cy.loginAs('pm')
    createDraftStage(Date.now() + 1)

    cy.dt('page-actions').contains('Submit for Approval').click()
    cy.contains('Pending Approval').should('be.visible')

    // Reject opens a reason modal (not a confirm dialog).
    cy.dt('page-actions').contains('Reject').click()
    cy.dt('reject-reason-input').type('Cypress: scope unclear, returning for rework')
    cy.dt('reject-submit').click()
    cy.contains('Rejected').should('be.visible')
  })
})
