// Smoke — the app boots against the real backend, login works, the serving route
// (/<app-route>) resolves, and each main list page renders its DeskList. Guards the
// harness (cy.login + cy.visitApp + the data-test hooks) before anything fancier.

describe('Smoke — boot + main list pages', () => {
  const LISTS = [
    '/projects',
    '/tasks',
    '/work-packages',
    '/stage-plannings',
    '/progress-entries',
  ]

  beforeEach(() => cy.login())

  LISTS.forEach((path) => {
    it(`loads ${path}`, () => {
      cy.visitApp(path)
      cy.dt('page-title').should('be.visible')
      cy.dt('desk-list').should('exist')
    })
  })
})
