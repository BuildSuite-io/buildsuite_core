// Loaded automatically before every spec. Registers custom commands + plugins.
import './commands'
import 'cypress-file-upload'
import 'cypress-real-events/support'

// Frappe pages fire background list probes that reject when the logged-in
// persona lacks read on a doctype — e.g. ProjectsView querying the `Company`
// doctype for the multi-company filter when the user isn't a System Manager.
// These rejections are benign for the page (the list still renders from its own
// 200 response), but Cypress fails a test on ANY uncaught app exception. Swallow
// ONLY permission-style rejections so genuine app errors still fail the suite.
// Permission *enforcement* is asserted directly on API responses in the
// permission specs, not via these incidental uncaught rejections.
Cypress.on('uncaught:exception', (err) => {
  const msg = err?.message || ''
  if (/PermissionError|not permitted|insufficient permission|frappe\.client\.get_list/i.test(msg)) {
    return false // prevent Cypress from failing the test on benign perm noise
  }
  return undefined // everything else fails the test as normal
})
