import { createApp } from "vue";
import { createPinia } from "pinia";
import { setConfig } from "frappe-ui-config";
import { frappeRequest } from "frappe-ui-frappe-request";
import App from "./App.vue";
import router from "./router";
import "./style.css";
import { applyBootToWindow, syncSessionFromCookie } from "./utils/session";
import { useSessionStore } from "./stores/session";
import { useDataStore } from "./stores";
import { DEV_BOOT_METHOD } from "./utils/appRoute";

const DEV_BOOT_URL = `/api/method/${DEV_BOOT_METHOD}`;

async function hydrateDevBoot() {
	if (!import.meta.env.DEV) return;

	try {
		const response = await fetch(DEV_BOOT_URL, {
			method: "POST",
			credentials: "include",
			headers: {
				"Content-Type": "application/json",
				"X-Frappe-CSRF-Token": window.csrf_token || "",
			},
		});

		if (!response.ok) {
			throw new Error(`Boot fetch failed with status ${response.status}`);
		}

		const payload = await response.json();
		const boot = payload?.message || payload;
		applyBootToWindow(boot);
	} catch (error) {
		console.warn("[buildsuite] Failed to hydrate dev boot context", error);
	}
}

async function mountApp() {
	syncSessionFromCookie();
	await hydrateDevBoot();

	const app = createApp(App);
	const pinia = createPinia();

	setConfig("resourceFetcher", frappeRequest);

	app.use(pinia);

	const sessionStore = useSessionStore(pinia);
	await sessionStore.bootstrapSession();

	// Load the REAL Company DocType before mount so the switcher / pickers have the
	// company list + resolved active company on first paint. Guarded — a failure
	// (e.g. backend unreachable) must not block mount; the store falls back to the
	// seed companies in hydrate().
	const dataStore = useDataStore(pinia);
	try {
		await dataStore.loadCompanies();
	} catch (error) {
		console.warn("[buildsuite] Failed to load companies", error);
	}

	app.use(router);
	app.mount("#app");
}

mountApp();
