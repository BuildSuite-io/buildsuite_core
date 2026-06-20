<script setup>
// Settings hub — tile grid grouped by area. Admin-only tiles hide entirely
// from non-admin roles. Only a subset have working CRUD pages today; the
// rest are visible placeholders for the eventual sub-sections.

import { computed } from "vue";
import { useRouter } from "vue-router";
import { useDataStore } from "@/stores";
import DeskPage from "@/components/desk/DeskPage.vue";
import UserAvatar from "@/components/UserAvatar.vue";
import { getWorkspaceIconPath } from "@/utils/workspaceIcons";

const store = useDataStore();
const router = useRouter();

const breadcrumbs = [{ label: "BuildSuite Core", to: "/" }, { label: "Settings" }];

const isAdmin = computed(() => store.isAdmin);
const isBSA = computed(() => store.isBSA);

// Tile groups. `adminOnly: true` filters the tile out for non-admin roles.
// `bsaOnly: true` filters out for non-BSA. `stub: true` renders the tile in
// muted style and disables navigation.
const groups = computed(() => [
	{
		title: "Organisation",
		tiles: [
			{
				slug: "companies",
				icon: "building-2",
				label: "Company",
				desc: "Companies, addresses, fiscal year per entity.",
				to: "/settings/companies",
				count: store.companies.length,
				countLabel: store.companies.length === 1 ? "company" : "companies",
			},
			{
				slug: "users",
				icon: "users",
				label: "Users",
				desc: "People who can log in. Role assignment and enabled status.",
				to: "/settings/users",
				count: store.team.length,
				countLabel: "users",
				adminOnly: true,
			},
			{
				slug: "roles",
				icon: "shield",
				label: "Roles & Permissions",
				desc: "Role definitions, workspace visibility and record-level permissions.",
				adminOnly: true,
				stub: true,
			},
			{
				slug: "naming",
				icon: "tag",
				label: "Naming Series",
				desc: "ID prefixes for Project, Task, BOQ, SCO etc.",
				adminOnly: true,
				stub: true,
			},
		],
	},
	{
		title: "BuildSuite product settings",
		tiles: [
			{
				slug: "core",
				icon: "puzzle",
				label: "BuildSuite Core Settings",
				desc: "Org-wide BuildSuite toggles — company segregation, default project type, default company.",
				to: "/settings/core",
				adminOnly: true,
			},
			{
				slug: "site-execution-settings",
				icon: "site-execution",
				label: "Site Execution Settings",
				desc: "Module defaults for Projects, Work Packages, Tasks, Progress Entries and Stage Planning.",
				to: "/settings/site-execution",
				adminOnly: true,
			},
			{
				slug: "workspace-structure",
				icon: "layout-grid",
				label: "Workspace Structure",
				desc: "Configure workspaces and per-role shortcut grids.",
				to: "/settings/workspace-structure",
				bsaOnly: true,
			},
			{
				slug: "project-types",
				icon: "tag",
				label: "Project Types",
				desc: "Configurable list of project types. Per-type Work Package label and default template picker.",
				to: "/settings/project-types",
				adminOnly: true,
			},
		],
	},
	{
		title: "System",
		adminOnly: true,
		tiles: [
			{
				slug: "general",
				icon: "settings",
				label: "General Settings",
				desc: "Date format, currency, time zone, default company, fiscal year.",
				adminOnly: true,
				stub: true,
			},
			{
				slug: "email",
				icon: "mail",
				label: "Email & Notifications",
				desc: "SMTP, notification rules, email templates, recipients.",
				adminOnly: true,
				stub: true,
			},
			{
				slug: "workflows",
				icon: "refresh-ccw",
				label: "Workflows",
				desc: "Approval chains for BOQ, SCO, Petty Cash and RA Bills.",
				adminOnly: true,
				stub: true,
			},
			{
				slug: "custom-fields",
				icon: "wrench",
				label: "Custom Fields",
				desc: "Add fields to existing DocTypes.",
				adminOnly: true,
				stub: true,
			},
			{
				slug: "print",
				icon: "file",
				label: "Print Templates",
				desc: "Letter heads, print formats per DocType, page sizes.",
				adminOnly: true,
				stub: true,
			},
			{
				slug: "integrations",
				icon: "plug",
				label: "Integrations",
				desc: "API keys, webhooks, OAuth apps and social login providers.",
				adminOnly: true,
				stub: true,
			},
		],
	},
	{
		title: "Data & Diagnostics",
		tiles: [
			{
				slug: "data",
				icon: "database",
				label: "Data Tools",
				desc: "Export the dataset, reset to defaults, inspect local storage.",
				to: "/settings/data",
			},
			{
				slug: "audit",
				icon: "clipboard-list",
				label: "Audit Log",
				desc: "Recent user actions across the system — who changed what when.",
				adminOnly: true,
				stub: true,
			},
		],
	},
]);

// Filter groups + tiles by role. Hide whole groups if every tile inside is
// admin-only and the user isn't admin.
const visibleGroups = computed(() =>
	groups.value
		.map((g) => ({
			...g,
			tiles: g.tiles.filter((t) => {
				if (t.bsaOnly && !isBSA.value) return false;
				if (t.adminOnly && !isAdmin.value) return false;
				return true;
			}),
		}))
		.filter((g) => g.tiles.length)
);

function onTileClick(tile) {
	if (tile.stub || !tile.to) return;
	router.push(tile.to);
}
</script>

<template>
	<DeskPage
		title="Settings"
		subtitle="Organisation, system, data and diagnostics"
		:breadcrumbs="breadcrumbs"
	>
		<!-- PRM-005 — Settings is restricted to System Manager + BuildSuite Administrator. -->
		<div
			v-if="!isAdmin"
			class="px-3 py-2 bg-warning-50 border border-warning-100 text-xs text-warning-700 dark:bg-ink-800 dark:border-ink-700"
			style="border-radius: 6px"
		>
			Settings is restricted to administrators.
		</div>
		<template v-else>
			<!-- Signed-in chip — shows which role/company is active -->
			<div
				class="flex items-center gap-3 mb-5 p-3 border border-ink-200 bg-ink-50"
				style="border-radius: 6px"
			>
				<UserAvatar :user-id="store.user?.id" size="sm" />
				<div class="flex-1 min-w-0">
					<div class="text-sm text-ink-900">
						Signed in as <span class="font-medium">{{ store.user?.name }}</span> · role
						<span class="font-medium text-ink-700">{{ store.currentRole?.name }}</span>
						<span v-if="store.isMultiCompany && store.currentCompany">
							· acting on
							<span class="font-medium text-ink-700">{{
								store.currentCompany.shortName
							}}</span></span
						>
					</div>
				</div>
			</div>

			<div v-for="group in visibleGroups" :key="group.title" class="mb-6">
				<h2 class="text-[11px] font-semibold uppercase tracking-wider text-ink-700 mb-2">
					{{ group.title }}
				</h2>
				<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2">
					<div
						v-for="tile in group.tiles"
						:key="tile.slug"
						class="border border-ink-200 bg-white p-3"
						:class="
							tile.stub
								? 'opacity-90'
								: 'hover:border-brand-400 hover:bg-brand-50 cursor-pointer'
						"
						style="border-radius: 6px"
						@click="onTileClick(tile)"
					>
						<div class="flex items-start gap-3">
							<div
								class="w-9 h-9 rounded-lg bg-ink-50 text-ink-600 flex items-center justify-center flex-shrink-0"
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
									v-html="getWorkspaceIconPath(tile.icon)"
								/>
							</div>
							<div class="flex-1 min-w-0">
								<div class="flex items-center gap-2 flex-wrap">
									<div class="text-sm font-medium text-ink-900">
										{{ tile.label }}
									</div>
									<span
										v-if="!tile.stub && tile.count !== undefined"
										class="ml-auto text-[10px] text-ink-500 tabular-nums"
										>{{ tile.count }} {{ tile.countLabel }}</span
									>
								</div>
								<div class="text-[11px] text-ink-600 mt-0.5 leading-snug">
									{{ tile.desc }}
								</div>
							</div>
						</div>
					</div>
				</div>
			</div>
		</template>
	</DeskPage>
</template>
