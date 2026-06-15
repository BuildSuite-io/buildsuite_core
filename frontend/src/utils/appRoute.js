// Single source of truth for the Frappe website route the SPA is served under.
//
// The whole frontend derives its base path from APP_ROUTE_NAME — the Vue Router
// base (router/index.js), the session route base + login redirect (session.js),
// and the dev-boot method path (main.js). Change this ONE token and the entire
// frontend follows.
//
// The backend route lives in buildsuite_core/hooks.py (`APP_ROUTE`) + the
// www/<route>.{py,html} page. Keep both sides in sync — the
// `bench change-app-route <new>` command rewrites this token AND the backend
// (hooks constant, www file rename) in one shot.

export const APP_ROUTE_NAME = 'core'

// Leading-slash form, e.g. '/client' — used as the router base and route prefix.
export const APP_ROUTE = `/${APP_ROUTE_NAME}`

// The whitelisted dev-boot method lives in www/<route>.py, so its dotted path
// tracks the route name (e.g. buildsuite_core.www.client.get_context_for_dev).
export const DEV_BOOT_METHOD = `buildsuite_core.www.${APP_ROUTE_NAME}.get_context_for_dev`

/**
 * Build a full path that INCLUDES the app base — for window.location, external
 * redirects, or absolute links. (RouterLink / router.push use bare paths; the
 * router prepends the base automatically, so you don't need this for them.)
 */
export function appUrl(path = '') {
  if (!path) return APP_ROUTE
  return `${APP_ROUTE}${path.startsWith('/') ? path : `/${path}`}`
}
