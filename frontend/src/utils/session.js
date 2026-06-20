import { APP_ROUTE } from "./appRoute";

const DEFAULT_ROUTE = APP_ROUTE;
const DEFAULT_FRAPPE_HOST = "http://localhost:8001";
const ACCESS_API_URL = "/api/method/buildsuite_core.api.permission.get_access_context";
const DEFAULT_ACCESS_CONTEXT_MAX_AGE_MS = 30_000;

let accessContextPromise = null;
let accessContextValue = null;
let accessContextFetchedAt = 0;

export function getCookie(name) {
	const cookie = document.cookie.split("; ").find((entry) => entry.startsWith(`${name}=`));

	if (!cookie) return null;
	return decodeURIComponent(cookie.split("=").slice(1).join("="));
}

export function syncSessionFromCookie() {
	if (!window.session_user) {
		window.session_user = getCookie("user_id") || "Guest";
	}

	return window.session_user;
}

export function getSessionUser() {
	return window.session_user || syncSessionFromCookie();
}

export function isAuthenticated() {
	return getSessionUser() !== "Guest";
}

export function getRouteBase() {
	return window.default_route || DEFAULT_ROUTE;
}

export function getFrappeHost() {
	if (!import.meta.env.DEV) return "";
	return import.meta.env.VITE_FRAPPE_HOST || DEFAULT_FRAPPE_HOST;
}

export function getLoginUrl(path) {
	const base = getRouteBase();
	const rawPath = path || "/";
	const redirectPath = rawPath.startsWith(base)
		? rawPath
		: `${base}${rawPath.startsWith("/") ? rawPath : `/${rawPath}`}`;

	return `${getFrappeHost()}/login?redirect-to=${encodeURIComponent(redirectPath)}`;
}

// URL of the real Frappe/ERPNext desk. Same-origin in prod (`/app`); the dev
// frappe host in dev so the vite server doesn't try to serve `/app` itself.
export function getDeskUrl() {
	return `${getFrappeHost()}/app`;
}

// Log out of Frappe, then land on the login page. Best-effort POST to the
// logout endpoint (clears the session cookie) followed by a full-page redirect
// regardless of the response — we always want to leave the authenticated SPA.
export async function logout() {
	try {
		await fetch(`${getFrappeHost()}/api/method/logout`, {
			method: "POST",
			credentials: "include",
			headers: { "X-Frappe-CSRF-Token": window.csrf_token || "" },
		});
	} catch (e) {
		/* ignore — redirect anyway */
	}
	window.location.href = `${getFrappeHost()}/login`;
}

export function applyBootToWindow(boot) {
	if (!boot || typeof boot !== "object") return;

	Object.entries(boot).forEach(([key, value]) => {
		window[key] = value;
	});

	if (window.lang) {
		document.documentElement.lang = window.lang;
	}
	if (window.text_direction) {
		document.documentElement.dir = window.text_direction;
	}

	syncSessionFromCookie();
}

export function isAccessContextFresh(maxAgeMs = DEFAULT_ACCESS_CONTEXT_MAX_AGE_MS) {
	if (!accessContextValue) return false;
	return Date.now() - accessContextFetchedAt <= maxAgeMs;
}

export async function getAccessContext(options = {}) {
	const { force = false, maxAgeMs = DEFAULT_ACCESS_CONTEXT_MAX_AGE_MS } = options;

	if (!force && isAccessContextFresh(maxAgeMs)) {
		return accessContextValue;
	}

	if (accessContextPromise) {
		return accessContextPromise;
	}

	accessContextPromise = fetch(ACCESS_API_URL, {
		method: "GET",
		credentials: "include",
		headers: {
			Accept: "application/json",
			"X-Frappe-CSRF-Token": window.csrf_token || "",
		},
	})
		.then(async (response) => {
			if (!response.ok) {
				throw new Error(`Access check failed with status ${response.status}`);
			}

			const payload = await response.json();
			const context = payload?.message || payload;
			if (!context || typeof context !== "object") {
				return {
					allowed: false,
					user: getSessionUser(),
					roles: [],
					reason: "invalid_response",
				};
			}

			if (context.user) {
				window.session_user = context.user;
			}

			accessContextValue = context;
			accessContextFetchedAt = Date.now();
			return context;
		})
		.catch((error) => {
			console.warn("[buildsuite] Access context check failed", error);
			const fallback = {
				allowed: false,
				user: getSessionUser(),
				roles: [],
				reason: "access_check_failed",
			};

			accessContextValue = fallback;
			accessContextFetchedAt = Date.now();
			return fallback;
		})
		.finally(() => {
			accessContextPromise = null;
		});

	return accessContextPromise;
}

export function clearAccessContextCache() {
	accessContextPromise = null;
	accessContextValue = null;
	accessContextFetchedAt = 0;
}
