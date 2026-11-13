<script setup>
// Settings hub — tile grid grouped by area. Admin-only tiles hide entirely from non-admin roles.
//
// Trimmed to the settings the product needs now (the prototype's S446 cleanup). Gone: the "Soon"
// stubs for things Frappe already provides (General, Email, Workflows, Custom Fields, Print
// Templates, Integrations, Naming Series, Audit Log, Roles & Permissions) — Frappe Desk is where
// those live, and the footer says so.

import { computed, ref, onMounted } from "vue";
import { useRouter } from "vue-router";
import { useDataStore } from "@/stores";
import { listBuildsuiteUsers } from "@/data/usersApi";
import DeskPage from "@/components/desk/DeskPage.vue";
import UserAvatar from "@/components/UserAvatar.vue";
import WorkspaceIcon from "@/components/WorkspaceIcon.vue";
import { __ } from "@/utils/translate";
import { listSettingsPages } from "@/data/settingsPagesApi";
import { settingsTilesList } from "@/sdk/registry";

const store = useDataStore();
const router = useRouter();

const breadcrumbs = [{ label: __("BuildSuite Core"), to: "/" }, { label: __("Settings") }];

const isAdmin = computed(() => store.isAdmin);
const isBSA = computed(() => store.isBSA);

const userCount = ref(undefined);
// Settings pages installed apps declare (each a Single DocType), shown as tiles of their own.
const appPages = ref([]);
onMounted(async () => {
	if (isAdmin.value) userCount.value = (await listBuildsuiteUsers()).length;
	try {
		appPages.value = (await listSettingsPages()) || [];
	} catch {
		appPages.value = []; // the hub still works without them
	}
});

// Tiles from installed apps: declared pages (hook) and tiles an extension registered (sdk), grouped
// by their own group name, after Core's groups. Settings is admin-only, so they are too.
const extensionGroups = computed(() => {
	const byGroup = {};
	const add = (group, tile) =>
		(byGroup[group] ||= []).push({ icon: "settings", adminOnly: true, ...tile });
	for (const p of appPages.value) {
		add(p.group, {
			icon: p.icon || "settings",
			label: p.label,
			desc: p.description,
			to: `/settings/doc/${encodeURIComponent(p.doctype)}`,
		});
	}
	for (const t of settingsTilesList()) {
		add(t.group, {
			icon: t.icon || "settings",
			label: t.label,
			desc: t.description || "",
			to: t.to,
		});
	}
	return Object.entries(byGroup).map(([title, tiles]) => ({ title, tiles }));
});

// Tile groups. `adminOnly: true` filters the tile out for non-admin roles; `bsaOnly: true` for
// non-BSA; `rolesAny` shows it to an admin or anyone holding one of the listed roles.
const groups = computed(() => [
	{
		title: __("Organisation"),
		tiles: [
			{
				slug: "companies",
				icon: "building-2",
				label: __("Company"),
				desc: __("Companies, letterheads and the brand colour each one shows."),
				to: "/settings/companies",
				count: store.companies.length,
				countLabel: store.companies.length === 1 ? __("company") : __("companies"),
			},
			{
				slug: "users",
				icon: "users",
				label: __("Users"),
				desc: __("People who can log in. Role assignment and enabled status."),
				to: "/settings/users",
				count: userCount.value,
				countLabel: __("users"),
				adminOnly: true,
			},
			{
				slug: "personas",
				icon: "shield",
				label: __("Personas"),
				desc: __("Job roles users pick from, each mapping to the Frappe roles it grants."),
				to: "/settings/personas",
				adminOnly: true,
			},
		],
	},
	{
		title: __("BuildSuite product settings"),
		tiles: [
			{
				slug: "core",
				icon: "puzzle",
				label: __("BuildSuite Core Settings"),
				desc: __(
					"Org-wide toggles: company segregation, default company, project naming, accounting defaults and app setup."
				),
				to: "/settings/core",
				adminOnly: true,
			},
			{
				slug: "project",
				icon: "clipboard-list",
				label: __("Project Settings"),
				desc: __(
					"The standard project page: which tabs every project offers by default. Each project can overrule it."
				),
				to: "/settings/project",
				adminOnly: true,
			},
			{
				slug: "finance-accounts",
				icon: "wallet",
				label: __("Bank & Cash Accounts"),
				desc: __(
					"Bank, cash and petty cash accounts shown across Project Finance, with opening and current balances."
				),
				to: "/settings/finance-accounts",
				adminOnly: true,
			},
			{
				slug: "terms",
				icon: "file",
				label: __("Terms & Conditions"),
				desc: __(
					"The clause library printed documents pull from, grouped by document. Rich text with tables."
				),
				to: "/settings/terms",
				// Managed by the admin + the roles that author document terms; everyone else gets
				// select-only and doesn't see the library.
				rolesAny: [
					"BuildSuite Administrator",
					"BuildSuite Accountant",
					"BuildSuite Procurement Officer",
					"BuildSuite Estimator",
				],
			},
			{
				slug: "workspace-setting",
				icon: "layout-grid",
				label: __("Workspace Setting"),
				desc: __(
					"Report-style shortcut tiles shown in each workspace — one tab per workspace."
				),
				to: "/settings/workspaces",
				adminOnly: true,
			},
			{
				slug: "project-categories",
				icon: "tag",
				label: __("Project Categories"),
				desc: __(
					"Construction categories that drive project templating, each with its own Work Package label."
				),
				to: "/settings/project-categories",
				adminOnly: true,
			},
		],
	},
	{
		title: __("Data & Diagnostics"),
		tiles: [
			{
				slug: "data",
				icon: "database",
				label: __("Data Tools"),
				desc: __("Export the dataset, reset to defaults, inspect local storage."),
				to: "/settings/data",
			},
			{
				slug: "app-icon-diagnostics",
				icon: "activity",
				label: __("App Icon Diagnostics"),
				desc: __(
					"Why the BuildSuite app icon may not be showing — a copyable server report."
				),
				to: "/settings/app-icon-diagnostics",
				adminOnly: true,
			},
		],
	},
	// Tiles installed apps add (hook-declared Single DocTypes and sdk.settings.addTile).
	...extensionGroups.value,
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
				// rolesAny: show when the user is an admin or holds one of the listed roles.
				if (t.rolesAny && !isAdmin.value && !t.rolesAny.some((r) => store.hasRole(r)))
					return false;
				return true;
			}),
		}))
		.filter((g) => g.tiles.length)
);

function onTileClick(tile) {
	if (tile.to) router.push(tile.to);
}
</script>

<template>
	<DeskPage
		:title="__('Settings')"
		:subtitle="__('Organisation, product settings, data and diagnostics')"
		:breadcrumbs="breadcrumbs"
	>
		<!-- PRM-005 — Settings is restricted to System Manager + BuildSuite Administrator. -->
		<div
			v-if="!isAdmin"
			class="px-3 py-2 bg-warning-50 border border-warning-100 text-xs text-warning-700 dark:bg-ink-800 dark:border-ink-700"
			style="border-radius: 6px"
		>
			{{ __("Settings is restricted to administrators.") }}
		</div>
		<template v-else>
			<!-- Signed-in chip — shows which role/company is active -->
			<div
				class="flex items-center gap-3 mb-6 px-4 py-3 border border-ink-200 bg-white"
				style="border-radius: 8px"
			>
				<UserAvatar :user-id="store.user?.id" size="sm" />
				<div class="flex-1 min-w-0">
					<div class="text-sm text-ink-900">
						{{ __("Signed in as") }}
						<span class="font-medium">{{ store.user?.name }}</span>
					</div>
					<div class="text-[11px] text-ink-500 mt-0.5">
						{{ __("Role:") }}
						<span class="text-ink-700">{{ store.currentRole?.name }}</span>
						<span v-if="store.isMultiCompany && store.currentCompany">
							· {{ __("Acting on:") }}
							<span class="text-ink-700">{{ store.currentCompany.shortName }}</span>
						</span>
					</div>
				</div>
			</div>

			<div v-for="group in visibleGroups" :key="group.title" class="mb-8">
				<h2 class="text-[11px] font-semibold uppercase tracking-wider text-ink-500 mb-3">
					{{ group.title }}
				</h2>
				<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
					<div
						v-for="tile in group.tiles"
						:key="tile.slug"
						class="group border border-ink-200 bg-white p-4 transition-all hover:border-brand-400 hover:shadow-sm cursor-pointer"
						style="border-radius: 8px"
						@click="onTileClick(tile)"
					>
						<div class="flex items-start gap-3">
							<!-- Icon chip — same shape as the workspace shortcut tiles. -->
							<div
								class="w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0 transition-colors bg-ink-50 text-ink-600 group-hover:bg-brand-50 group-hover:text-brand-700"
							>
								<WorkspaceIcon :slug="tile.icon" :size="20" />
							</div>
							<div class="flex-1 min-w-0">
								<div class="flex items-center gap-2 flex-wrap">
									<div class="text-sm font-medium text-ink-900">
										{{ tile.label }}
									</div>
									<span
										v-if="tile.count !== undefined"
										class="ml-auto text-[10px] text-ink-500 tabular-nums whitespace-nowrap"
										>{{ tile.count }} {{ tile.countLabel }}</span
									>
								</div>
								<div class="text-[11px] text-ink-600 mt-1 leading-snug">
									{{ tile.desc }}
								</div>
							</div>
						</div>
					</div>
				</div>
			</div>

			<p class="text-[11px] text-ink-500 border-t border-ink-100 pt-3">
				{{
					__(
						"Date and currency formats, email, workflows, custom fields, print formats, naming series and the audit trail are managed in Frappe Desk, so they are not repeated here."
					)
				}}
			</p>
		</template>
	</DeskPage>
</template>
