const DEFAULT_ROUTE = '/buildsuite_core'
const DEFAULT_FRAPPE_HOST = 'http://localhost:8001'

export function getCookie(name) {
  const cookie = document.cookie
    .split('; ')
    .find((entry) => entry.startsWith(`${name}=`))

  if (!cookie) return null
  return decodeURIComponent(cookie.split('=').slice(1).join('='))
}

export function syncSessionFromCookie() {
  if (!window.session_user) {
    window.session_user = getCookie('user_id') || 'Guest'
  }

  return window.session_user
}

export function getSessionUser() {
  return window.session_user || syncSessionFromCookie()
}

export function isAuthenticated() {
  return getSessionUser() !== 'Guest'
}

export function getRouteBase() {
  return window.default_route || DEFAULT_ROUTE
}

export function getFrappeHost() {
  if (!import.meta.env.DEV) return ''
  return import.meta.env.VITE_FRAPPE_HOST || DEFAULT_FRAPPE_HOST
}

export function getLoginUrl(path) {
  const base = getRouteBase()
  const rawPath = path || '/'
  const redirectPath = rawPath.startsWith(base)
    ? rawPath
    : `${base}${rawPath.startsWith('/') ? rawPath : `/${rawPath}`}`

  return `${getFrappeHost()}/login?redirect-to=${encodeURIComponent(redirectPath)}`
}

export function applyBootToWindow(boot) {
  if (!boot || typeof boot !== 'object') return

  Object.entries(boot).forEach(([key, value]) => {
    window[key] = value
  })

  if (window.lang) {
    document.documentElement.lang = window.lang
  }
  if (window.text_direction) {
    document.documentElement.dir = window.text_direction
  }

  syncSessionFromCookie()
}
