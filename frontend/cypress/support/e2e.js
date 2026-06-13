// Loaded automatically before every spec. Registers custom commands + plugins.
import './commands'
import 'cypress-file-upload'
import 'cypress-real-events/support'

// NOTE: deliberately NO global uncaught:exception handler. The suite stays strict
// — an unhandled rejection from the app (e.g. a doctype get_list 403 because a
// persona is missing a DocPerm) fails the test loudly, so permission gaps surface
// immediately instead of being silently swallowed. (This is how the missing
// Company/Customer read perm was caught.) Fix the permission at the source in
// buildsuite_core.permissions.setup, don't mask it here.
