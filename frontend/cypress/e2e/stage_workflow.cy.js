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

  // SAW-011 — once Approved, the stage is locked: no Edit affordance and the
  // task add/remove control is replaced by a "locked" indicator.
  it('Approved stage is locked for editing', () => {
    cy.loginAs('pm')
    createDraftStage(Date.now() + 2)

    cy.dt('page-actions').contains('Submit for Approval').click()
    cy.contains('Pending Approval').should('be.visible')
    cy.dt('page-actions').contains('Approve').click()
    cy.contains('Approved').should('be.visible')

    cy.dt('page-actions').should('not.contain', 'Edit')
    cy.contains('button', 'Add/Remove Tasks').should('not.exist')
    cy.contains('Locked — stage is approved').should('be.visible')
  })

  // SAW-013 — every workflow transition is recorded in the Activity panel with
  // the actor + a human-readable label.
  it('records each transition in the Activity log', () => {
    cy.loginAs('pm')
    createDraftStage(Date.now() + 3)

    cy.dt('page-actions').contains('Submit for Approval').click()
    cy.contains('Pending Approval').should('be.visible')
    cy.dt('page-actions').contains('Approve').click()
    cy.contains('Approved').should('be.visible')

    cy.dt('stage-activity').within(() => {
      cy.contains(/Submitted for approval/i).should('be.visible')
      cy.contains(/Approved/i).should('be.visible')
    })
  })

  // SAW-006 — revising a Rejected stage clones it into a fresh Draft (the
  // original stays Rejected as an audit record); the clone opens in edit mode.
  it('Revise on a Rejected stage clones a new Draft', () => {
    cy.loginAs('pm')
    createDraftStage(Date.now() + 4)

    cy.dt('page-actions').contains('Submit for Approval').click()
    cy.contains('Pending Approval').should('be.visible')
    cy.dt('page-actions').contains('Reject').click()
    cy.dt('reject-reason-input').type('Cypress: revise flow')
    cy.dt('reject-submit').click()
    cy.contains('Rejected').should('be.visible')

    // Capture the rejected stage's path, then Revise and assert we land on a
    // different stage that is back in Draft.
    cy.location('pathname').then((rejectedPath) => {
      cy.dt('page-actions').contains('Revise').click()
      cy.location('pathname', { timeout: 30000 })
        .should('match', /\/stage-plannings\/.+/)
        .and('not.eq', rejectedPath)
      cy.contains('Draft').should('be.visible')
    })
  })
})
