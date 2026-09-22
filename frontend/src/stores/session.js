import { defineStore } from "pinia";
import { clearAccessContextCache, getAccessContext, syncSessionFromCookie } from "@/utils/session";

export const useSessionStore = defineStore("session", {
	state: () => ({
		initialized: false,
		user: "Guest",
		authenticated: false,
		// Site-level developer flag (from get_access_context → site_config.json). Gates
		// dev-only affordances like the role switcher.
		developerMode: false,
		access: {
			allowed: false,
			roles: [],
			persona: null,
			// Backend-derived per-resource caps (api.permission.get_resource_permissions),
			// keyed by the frontend resource key. usePermissions reads this — it's the single
			// source of truth for CRUD gating (replaces the old roles.js PERSONA_CAPS matrix).
			resourcePermissions: {},
			// The bespoke report routes this user may open (api.permission → report_access);
			// the router guard denies any other gated report route on a deep link.
			reportRoutes: [],
			reason: "guest",
		},
		lastCheckedAt: null,
	}),

	actions: {
		hydrateFromRuntime() {
			const user = syncSessionFromCookie();
			this.user = user;
			this.authenticated = user !== "Guest";

			if (!this.authenticated) {
				this.access = {
					allowed: false,
					roles: [],
					reason: "guest",
				};
				this.lastCheckedAt = Date.now();
			}

			return this.authenticated;
		},

		async refreshAccess(options = {}) {
			this.hydrateFromRuntime();

			if (!this.authenticated) {
				return this.access;
			}

			const context = await getAccessContext(options);
			this.user = context.user || this.user;
			this.authenticated = this.user !== "Guest";
			this.access = {
				allowed: Boolean(context.allowed),
				roles: Array.isArray(context.roles) ? context.roles : [],
				persona: context.persona || null,
				resourcePermissions: context.resource_permissions || {},
				reportRoutes: Array.isArray(context.report_routes) ? context.report_routes : [],
				reason: context.reason || (context.allowed ? "ok" : "missing_role"),
			};
			this.developerMode = Boolean(context.developer_mode);
			this.lastCheckedAt = Date.now();
			return this.access;
		},

		async bootstrapSession() {
			if (this.initialized) {
				return this.access;
			}

			await this.refreshAccess({ force: false });
			this.initialized = true;
			return this.access;
		},

		async ensureAccess(options = {}) {
			if (!this.initialized) {
				await this.bootstrapSession();
				return this.access;
			}

			return this.refreshAccess(options);
		},

		async recheckAccess() {
			clearAccessContextCache();
			return this.refreshAccess({ force: true });
		},

		resetSession() {
			clearAccessContextCache();
			this.initialized = false;
			this.user = "Guest";
			this.authenticated = false;
			this.access = {
				allowed: false,
				roles: [],
				reason: "guest",
			};
			this.lastCheckedAt = null;
		},
	},
});
