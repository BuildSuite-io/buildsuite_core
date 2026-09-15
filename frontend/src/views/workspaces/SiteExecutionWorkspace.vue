<script setup>
// Site Execution workspace landing — Vue-styled per §12.4. M1 ships this as
// one of the 3 Vue surfaces (locked by Block-A decision 2). Greeting + role-
// filtered shortcuts grid, no Number Cards / Quick Lists / charts per §13.2.
//
// Architectural win: shortcuts are NOT hardcoded — they come from the backend
// registry (BuildSuite Workspace Shortcut, role-filtered server-side by
// get_workspace_shortcuts). A BSA at a customer org can reorder / hide / add
// shortcuts via /settings/workspace-structure without developer involvement.
//
// Session 35 — EXPLORATORY DESIGN VISUALISATION (additive, NOT M1 scope):
//   1. A prominent Project Dashboard tile rendered ABOVE the shortcuts grid,
//      gated to "owner" roles (Director / PM / Admin / Accountant / BSA).
//      Routes to /app/project-dashboard (Vue composite landing inside Desk).
//   2. A separate "Reports" group rendered BELOW the shortcuts grid with 5
//      hardcoded Frappe-style report tiles. Each tile routes to
//      /app/reports/:slug (a Desk-styled stub).
//
// Both additions are HARDCODED here — in production they would be configured
// via Workspace Structure Settings DocType records (tile_type discriminator,
// per-tile role visibility, dashboard / report references). The hardcoding
// is deliberate and clearly marked: these are visual mockups for stakeholder
// review of dashboard + report layout, not production architecture.

import { computed, ref, onMounted } from "vue";
import { RouterLink } from "vue-router";
import { useDataStore } from "@/stores";
import UserAvatar from "@/components/UserAvatar.vue";
import WorkspaceShortcut from "@/components/WorkspaceShortcut.vue";
import { getWorkspaceIconPath } from "@/utils/workspaceIcons";
import { getWorkspaceReports, getWorkspaceShortcuts } from "@/data/workspaceSettingApi";
import WorkspaceRecordsSection from "@/components/workspaces/WorkspaceRecordsSection.vue";

const store = useDataStore();

// Shortcuts come from the backend registry (BuildSuite Workspace Shortcut), role-filtered
// server-side. A BSA configures them at /settings/workspace-structure.
const shortcuts = ref([]);
const shortcutsLoaded = ref(false);

const today = computed(() => {
	const d = new Date();
	return d.toLocaleDateString("en-US", { weekday: "long", month: "short", day: "numeric" });
});

// --- Session 35 additive: Project Dashboard tile -------------------------
// "Owner" roles that should see the portfolio dashboard tile. Hardcoded
// here per the exploratory-visualisation framing; production would put this
// on the workspace tile's `roles` child-table column.
const OWNER_ROLES = ["director", "pm", "admin", "accountant", "bsa"];
const showProjectDashboard = computed(() => OWNER_ROLES.includes(store.role));

// --- Reports group --------------------------------------------------------
// Configured per workspace in Workspace Setting (label + destination + icon +
// description, in order). Each tile resolves to a Frappe report route, an in-app
// path, or a Desk URL (rt.external → open via href, else the SPA router).
const reportTiles = ref([]);
onMounted(async () => {
	try {
		reportTiles.value = await getWorkspaceReports("site-execution");
	} catch {
		reportTiles.value = [];
	}
	try {
		shortcuts.value = await getWorkspaceShortcuts("site-execution");
	} catch {
		shortcuts.value = [];
	} finally {
		shortcutsLoaded.value = true;
	}
});
</script>

<template>
	<div class="bg-white min-h-full">
		<div class="max-w-6xl mx-auto px-6 py-8">
			<!-- Title strip — workspace name as the heading; date eyebrow only -->
			<div class="mb-6">
				<div class="text-xs text-ink-500 mb-1">{{ today }}</div>
				<h1 class="text-2xl font-semibold text-ink-900">Site Execution</h1>
			</div>

			<!-- BSA hint banner — only visible to BSA (the audience who can reconfigure) -->
			<div
				v-if="store.isBSA"
				class="mb-5 px-3 py-2 bg-brand-50 border border-brand-100 text-[11px] text-brand-700 flex items-center justify-between"
				style="border-radius: 6px"
			>
				<span
					>Customize shortcuts shown on this workspace — reorder, hide per role, or add
					new ones.</span
				>
				<RouterLink
					to="/settings/workspace-structure"
					class="font-medium hover:underline whitespace-nowrap ml-3"
				>
					Configure →
				</RouterLink>
			</div>

			<!-- Session 35 additive — Project Dashboard tile (owner-gated, hardcoded) -->
			<RouterLink
				v-if="showProjectDashboard"
				to="/project-dashboard"
				class="mb-5 block bg-brand-50 border border-brand-200 hover:border-brand-400 hover:shadow-sm p-4 transition-all group"
				style="border-radius: 8px"
			>
				<div class="flex items-start gap-4">
					<div
						class="w-10 h-10 rounded-lg bg-white/80 text-brand-700 flex items-center justify-center flex-shrink-0"
					>
						<svg
							class="w-5 h-5"
							viewBox="0 0 24 24"
							fill="none"
							stroke="currentColor"
							stroke-width="1.8"
							stroke-linecap="round"
							stroke-linejoin="round"
							aria-hidden="true"
							v-html="getWorkspaceIconPath('chart-line')"
						/>
					</div>
					<div class="flex-1 min-w-0">
						<div class="flex items-center gap-2">
							<div
								class="text-base font-semibold text-ink-900 group-hover:text-brand-700 transition-colors dark:text-[#F5F5F5]"
							>
								Project Dashboard
							</div>
							<span
								class="text-[9px] px-1.5 py-0.5 bg-brand-100 text-brand-700 font-medium uppercase tracking-wider"
								style="border-radius: 2px"
								>Owner view</span
							>
						</div>
						<div class="text-xs text-brand-700 mt-1 leading-snug">
							Portfolio health, top risks, and high-value approvals at a glance.
						</div>
					</div>
					<svg
						class="w-5 h-5 text-brand-400 group-hover:text-brand-600 transition-colors"
						viewBox="0 0 24 24"
						fill="none"
						stroke="currentColor"
						stroke-width="1.8"
						stroke-linecap="round"
						stroke-linejoin="round"
						aria-hidden="true"
					>
						<path d="m9 6 6 6-6 6" />
					</svg>
				</div>
			</RouterLink>

			<!-- Shortcuts grid — role-filtered by the backend registry. Tiles use the
           shared <WorkspaceShortcut> component so every workspace landing renders
           the same tile shape. -->
			<div
				v-if="shortcuts.length"
				class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3"
			>
				<!-- Per the prototype (S50), DocType shortcut tiles render WITHOUT a
				     description — only the Reports group below carries subtext. -->
				<WorkspaceShortcut
					v-for="sc in shortcuts"
					:key="sc.route"
					:to="sc.route"
					:icon="sc.icon"
					:label="sc.label"
				/>
			</div>

			<!-- No shortcuts (none configured, or none visible to this user) -->
			<div
				v-else-if="shortcutsLoaded"
				class="bg-white border border-ink-200 px-4 py-6 text-center"
				style="border-radius: 8px"
			>
				<div class="text-sm text-ink-500 mb-1">
					No Site Execution shortcuts available.
				</div>
				<RouterLink
					v-if="store.isBSA"
					to="/settings/workspace-structure"
					class="text-xs text-brand-700 hover:underline"
				>
					Configure shortcuts →
				</RouterLink>
			</div>

			<WorkspaceRecordsSection workspace="site-execution" />

			<!-- Reports group — configured in Site Execution Settings (report + icon
           + description, in order). Each tile opens the report's desk route. -->
			<div v-if="reportTiles.length" class="mt-8">
				<h2 class="text-[11px] font-semibold uppercase tracking-wider text-ink-700 mb-2">
					Reports
				</h2>
				<div class="border-t border-ink-200 mb-3"></div>
				<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
					<WorkspaceShortcut
						v-for="(rt, i) in reportTiles"
						:key="i"
						:to="rt.external ? null : rt.route"
						:href="rt.external ? rt.route : null"
						:icon="rt.icon"
						:label="rt.label"
						:description="rt.description"
					>
						<template #badge>
							<span
								class="text-[9px] px-1 py-0.5 bg-ink-100 text-ink-600 font-medium uppercase tracking-wider"
								style="border-radius: 2px"
								>Report</span
							>
						</template>
					</WorkspaceShortcut>
				</div>
			</div>
		</div>
	</div>
</template>
