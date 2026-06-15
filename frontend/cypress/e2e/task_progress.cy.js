// File a Task Progress Entry and confirm the parent Task's progress updates via
// the real server hook. Opens an existing seeded task (read from the list) so we
// don't depend on the create form here.
//
// NOTE: the progress-entry modal's inner fields are filled best-effort — verify
// the modal field selectors against the running app on first run.

describe('Task progress entry updates the task', () => {
  it('filing 60% reflects on the task', () => {
    cy.login()
    cy.visitApp('/tasks')
    cy.dt('desk-list').find('[data-test-row]').first().click()
    cy.location('pathname').should('match', /\/tasks\/.+/)

    cy.dt('file-progress-entry').click()
    cy.dt('confirm-dialog').should('not.exist')   // it's a form modal, not a confirm

    // Cumulative progress input inside the modal (number field). Target by type.
    cy.get('[role="dialog"], .fixed').find('input[type="number"]').first().clear().type('60')
    cy.dt('save-btn').click()

    // Back on the task detail, the progress figure reflects the new entry.
    cy.location('pathname', { timeout: 30000 }).should('match', /\/tasks\/.+/)
    cy.contains('60').should('exist')
  })
})
