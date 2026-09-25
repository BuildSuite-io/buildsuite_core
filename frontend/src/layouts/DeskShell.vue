<script setup>
import { computed, ref, watch, nextTick, onMounted, onBeforeUnmount } from "vue";
import { useRoute, useRouter, RouterLink } from "vue-router";
import { useDataStore } from "@/stores";
import { useSessionStore } from "@/stores/session";
import { useUserNames } from "@/composables/useUserNames";
import { usePermissions } from "@/composables/usePermissions";
import LogoIcon from "@/components/LogoIcon.vue";
import RoleSwitcher from "@/components/RoleSwitcher.vue";
import CompanySwitcher from "@/components/CompanySwitcher.vue";
import UserAvatar from "@/components/UserAvatar.vue";
import { getWorkspaceIconPath } from "@/utils/workspaceIcons";
import { getDeskUrl, logout, getSessionUser } from "@/utils/session";
import { searchPlaces, decorateRecord, decorateDoctype } from "@/data/search";
import { commandPalette } from "@/data/searchApi";

const route = useRoute();
const router = useRouter();
const store = useDataStore();
const session = useSessionStore();
const { userName } = useUserNames();
const { canRead } = usePermissions();

// Command palette (⌘K). Two kinds of answer — PLACES (a doctype's list or a
// report, permission-gated client-side) and RECORDS (the documents themselves,
// fetched from the permission-safe global-search index). Both flow through the
// shared search data layer (src/data/search.js, searchApi.js) so this shell only
// wires the UX, never the search logic.
const searchOpen = ref(false);
const searchQuery = ref("");
const records = ref([]);
const doctypeMatches = ref([]);
const searchCursor = ref(0);
const searchInput = ref(null);

// Places: the curated app lists + reports (permission-gated client-side), followed by any doctype
// whose NAME matches the query (backend, permission-filtered) opening its generic list — so a
// query can name a doctype the SPA has no bespoke list for and still reach it.
const places = computed(() => [
	...searchPlaces(searchQuery.value, {
		canRead,
		reportRoutes: session.access?.reportRoutes || [],
	}),
	...doctypeMatches.value.map(decorateDoctype),
]);
// Record results decorated into palette rows (bespoke view, else the generic records browser).
const recordRows = computed(() => records.value.map(decorateRecord));
// One flat list, so the arrow keys walk places then records without the caller
// having to know which section the cursor is standing in.
const searchFlat = computed(() => [...places.value, ...recordRows.value]);

// Debounced record fetch. A new query resets the cursor and, after ~180ms of no
// typing, fetches records when there are ≥ 2 chars; out-of-order responses are
// dropped by checking the query hasn't moved on since the request went out.
let searchTimer = null;
watch(searchQuery, (q) => {
	searchCursor.value = 0;
	if (searchTimer) clearTimeout(searchTimer);
	const text = q.trim();
	if (text.length < 2) {
		records.value = [];
		doctypeMatches.value = [];
		return;
	}
	searchTimer = setTimeout(async () => {
		try {
			const { doctypes, records: recs } = await commandPalette(text, 12);
			// Ignore a stale response whose query has since changed.
			if (searchQuery.value.trim() === text) {
				doctypeMatches.value = doctypes;
				records.value = recs;
			}
		} catch {
			if (searchQuery.value.trim() === text) {
				doctypeMatches.value = [];
				records.value = [];
			}
		}
	}, 180);
});

function openSearch() {
	searchOpen.value = true;
	nextTick(() => searchInput.value?.focus());
}
function closeSearch() {
	searchOpen.value = false;
	searchQuery.value = "";
	records.value = [];
	doctypeMatches.value = [];
	searchCursor.value = 0;
}
function goSearch(row) {
	if (!row) return;
	closeSearch();
	router.push(row.to);
}
function moveSearch(delta) {
	const n = searchFlat.value.length;
	if (!n) return;
	searchCursor.value = (searchCursor.value + delta + n) % n;
}

// Global hotkey: ⌘K / Ctrl+K toggles the palette; Escape closes it when open.
function onGlobalKey(e) {
	if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
		e.preventDefault();
		searchOpen.value ? closeSearch() : openSearch();
		return;
	}
	// No preventDefault on Esc — other Esc handlers must still run.
	if (e.key === "Escape" && searchOpen.value) closeSearch();
}
onMounted(() => window.addEventListener("keydown", onGlobalKey));
onBeforeUnmount(() => window.removeEventListener("keydown", onGlobalKey));
// Mobile sidebar drawer state. The sidebar is always visible on lg+ and
// collapses to a slide-in drawer below that breakpoint.
const sidebarOpen = ref(false);
function closeSidebar() {
	sidebarOpen.value = false;
}

// Desktop-only rail collapse (lg+). Below lg the sidebar is a full-width drawer,
// so collapse never applies there — every collapsed style is `lg:`-prefixed.
// Persisted so the choice survives navigation + reload.
const collapsed = ref(localStorage.getItem("bs-nav-collapsed") === "1");
watch(collapsed, (v) => localStorage.setItem("bs-nav-collapsed", v ? "1" : "0"));
function toggleCollapse() {
	collapsed.value = !collapsed.value;
}
function toggleTheme() {
	store.toggleTheme();
}

// App-branding dropdown (mirrors prototype S149). The BuildSuite header is a
// trigger that opens a menu with "Go to Desktop" (the real ERPNext desk) and
// "Logout" (real Frappe logout → login). Backdrop click dismisses.
const appMenuOpen = ref(false);
function toggleAppMenu() {
	appMenuOpen.value = !appMenuOpen.value;
}
function closeAppMenu() {
	appMenuOpen.value = false;
}
function goToDesktop() {
	closeAppMenu();
	window.location.href = getDeskUrl();
}
function onLogout() {
	closeAppMenu();
	logout();
}

// Footer profile — the REAL signed-in user (session store), not the prototype
// demo user. Name + avatar resolve from the backend User directory; the role is
// the user's BuildSuite persona (falling back to a real role label).
const profileUser = computed(() => {
	const u = session.user;
	return u && u !== "Guest" ? u : getSessionUser();
});
const profileName = computed(() => userName(profileUser.value) || profileUser.value || "User");
const profileRole = computed(() => {
	const persona = session.access?.persona;
	if (persona) return persona;
	const roles = session.access?.roles || [];
	const bs = roles.find((r) => r.startsWith("BuildSuite "));
	if (bs) return bs.replace("BuildSuite ", "");
	if (roles.includes("System Manager")) return "System Manager";
	if (profileUser.value === "Administrator") return "Administrator";
	return "";
});

// Access-level hint pills (CLAUDE.md §12.3). Shown next to a workspace link when
// the active role has restricted access (anything other than 'full').
const ACCESS_HINTS = {
	read: { label: "R", title: "Read-only access" },
	approve: { label: "A", title: "Approve-only access" },
	"create-own": { label: "C", title: "Create own work only" },
	"self-service": { label: "SS", title: "Self-service only" },
	"team-only": { label: "T", title: "Team-only (direct reports)" },
	"pay-only": { label: "P", title: "Pay-only view" },
	"mr-only": { label: "MR", title: "Material-request raise only" },
};

// ERPNext-inherited workspaces link OUT to the real Frappe desk (full-page nav), not to
// SPA routes — the SPA doesn't reimplement Accounting/Buying/Stock/Assets/HR, so their nav
// rows open the actual ERPNext workspaces. Routes match the standard ERPNext workspace slugs.
const ERPNEXT_DESK_ROUTES = {
	accounting: "accounting",
	buying: "buying",
	stock: "stock",
	assets: "assets",
	hr: "hr",
};
function deskWorkspaceUrl(slug) {
	return `${getDeskUrl()}/${ERPNEXT_DESK_ROUTES[slug] || slug}`;
}

// Per-session collapse for the ERPNext nav group — closed by default. A construction user
// works in the BuildSuite group all day and drops into ERPNext occasionally, so its rows are
// hidden until asked for. State lives on the layout (survives navigation) and resets on
// reload, keeping "closed by default" true every time the app opens.
const collapsedGroups = ref({ erpnext: true });
function toggleGroup(key) {
	collapsedGroups.value = { ...collapsedGroups.value, [key]: !collapsedGroups.value[key] };
}
function groupCollapsed(group) {
	return !!(group.collapsible && collapsedGroups.value[group.key]);
}
// Group-collapse applies only in the expanded sidebar; the icon rail always shows every item
// (there is no group header there to reopen a collapsed group).
function renderItems(group) {
	return groupCollapsed(group) && !collapsed.value ? [] : group.items;
}

// Sidebar groups for the active role.
// Home is synthesized as the first BuildSuite item and Site Execution is pinned
// second when visible because it is the highest-frequency workspace.
const navGroups = computed(() => {
	const HOME_ITEM = { slug: "home", name: "Home", to: "/home", group: "buildsuite", hint: null };
	const buildsuiteItems = [HOME_ITEM];
	// Insights — ask-a-question reporting. First layer is leadership-only (Director /
	// PM / Administrator); it's a standalone feature, not a workspace, so it's pinned
	// here rather than driven off the workspace-visibility matrix.
	if (store.isLeadership) {
		buildsuiteItems.push({ slug: "insights", name: "Insights", to: "/insights", icon: "💡", group: "buildsuite", hint: null });
	}
	const erpnextItems = [];
	// store.workspaces is the backend registry list — role-filtered, ordered (sort_order),
	// and carrying its own metadata (name/icon/to/group). Adding a BuildSuite Workspace record
	// therefore flows into the sidebar with no frontend edit.
	for (const ws of store.workspaces) {
		const hint = ws.access && ws.access !== "full" ? ACCESS_HINTS[ws.access] : null;
		const item = { slug: ws.slug, name: ws.name, icon: ws.icon, to: ws.to, group: ws.group, hint };
		if (ws.group === "erpnext") {
			// Link to the real ERPNext desk workspace (full-page nav), not the SPA route.
			erpnextItems.push({ ...item, external: true, href: deskWorkspaceUrl(ws.slug) });
		} else {
			buildsuiteItems.push(item);
		}
	}

	const groups = [];
	if (buildsuiteItems.length) {
		groups.push({
			key: "buildsuite",
			title: "BuildSuite",
			muted: false,
			topSeparator: false,
			items: buildsuiteItems,
		});
	}
	if (erpnextItems.length) {
		groups.push({
			key: "erpnext",
			title: "ERPNext",
			muted: true,
			// Collapsible, closed by default — the inherited workspaces are occasional-use.
			collapsible: true,
			// Only render the top-border separator when there's a BuildSuite group above it;
			// otherwise it looks like an orphan rule at the top of the nav.
			topSeparator: groups.length > 0,
			items: erpnextItems,
		});
	}
	return groups;
});

// Topbar breadcrumb removed; each view already renders richer page breadcrumbs.
</script>

<template>
	<div class="min-h-screen flex bg-white">
		<!-- Mobile backdrop. Only visible when the drawer is open. -->
		<div
			v-if="sidebarOpen"
			class="fixed inset-0 bg-ink-900/40 z-40 lg:hidden"
			@click="closeSidebar"
		></div>

		<!-- Sidebar — sticky on lg+; slide-in drawer below that breakpoint. -->
		<aside
			class="w-60 bg-white border-r border-ink-200 flex flex-col flex-shrink-0 lg:sticky lg:top-0 lg:h-screen lg:translate-x-0 fixed inset-y-0 left-0 z-50 transform transition-all duration-200"
			:class="[
				sidebarOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0',
				collapsed ? 'lg:w-16' : 'lg:w-60',
			]"
		>
			<!-- App-branding dropdown (prototype S149): Go to Desktop / Logout.
           The "Core" badge moved into the dropdown sub-line. -->
			<div class="h-14 border-b border-ink-200 relative">
				<button
					type="button"
					class="w-full h-full flex items-center justify-between text-left hover:bg-ink-50 pl-3 pr-2"
					:class="[appMenuOpen ? 'bg-ink-50' : '', collapsed ? 'lg:justify-center lg:px-0' : '']"
					title="BuildSuite"
					@click="toggleAppMenu"
				>
					<span class="flex items-center gap-2">
						<LogoIcon :size="26" />
						<span class="font-semibold text-ink-900 text-sm" :class="collapsed ? 'lg:hidden' : ''"
							>BuildSuite</span
						>
					</span>
					<svg
						class="w-4 h-4 text-ink-400 transition-transform"
						:class="[appMenuOpen ? 'rotate-180' : '', collapsed ? 'lg:hidden' : '']"
						fill="none"
						stroke="currentColor"
						viewBox="0 0 24 24"
					>
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							stroke-width="2"
							d="M19 9l-7 7-7-7"
						/>
					</svg>
				</button>

				<div v-if="appMenuOpen" class="fixed inset-0 z-[55]" @click="closeAppMenu"></div>
				<div
					v-if="appMenuOpen"
					class="absolute left-2 right-2 top-full mt-1 z-[56] bg-white border border-ink-200 rounded-md shadow-fp-lg py-1"
				>
					<div class="px-3 py-2 border-b border-ink-100">
						<div class="text-xs font-semibold text-ink-900">BuildSuite</div>
						<div class="text-[10px] text-brand-700 mt-0.5">Core edition</div>
					</div>
					<button
						type="button"
						class="w-full text-left flex items-center gap-2 px-3 py-1.5 text-xs text-ink-700 hover:bg-ink-50"
						@click="goToDesktop"
					>
						<svg
							class="w-3.5 h-3.5 text-ink-500"
							fill="none"
							stroke="currentColor"
							viewBox="0 0 24 24"
						>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M4 5a1 1 0 011-1h5a1 1 0 011 1v5a1 1 0 01-1 1H5a1 1 0 01-1-1V5zM13 5a1 1 0 011-1h5a1 1 0 011 1v5a1 1 0 01-1 1h-5a1 1 0 01-1-1V5zM4 14a1 1 0 011-1h5a1 1 0 011 1v5a1 1 0 01-1 1H5a1 1 0 01-1-1v-5zM13 14a1 1 0 011-1h5a1 1 0 011 1v5a1 1 0 01-1 1h-5a1 1 0 01-1-1v-5z"
							/>
						</svg>
						<span>Go to Desktop</span>
					</button>
					<button
						type="button"
						class="w-full text-left flex items-center gap-2 px-3 py-1.5 text-xs text-ink-700 hover:bg-ink-50"
						@click="onLogout"
					>
						<svg
							class="w-3.5 h-3.5 text-ink-500"
							fill="none"
							stroke="currentColor"
							viewBox="0 0 24 24"
						>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"
							/>
						</svg>
						<span>Logout</span>
					</button>
				</div>
			</div>

			<div class="px-3 py-2" :class="collapsed ? 'lg:px-2' : ''">
				<button
					@click="openSearch"
					class="w-full px-2.5 py-1.5 text-xs bg-ink-50 text-ink-600 rounded flex items-center gap-2 hover:bg-ink-100"
					:class="collapsed ? 'lg:justify-center lg:px-0' : ''"
					:title="collapsed ? 'Search (⌘K)' : ''"
				>
					<svg class="w-3.5 h-3.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							stroke-width="2"
							d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
						/>
					</svg>
					<span :class="collapsed ? 'lg:hidden' : ''">Search or jump to...</span>
					<span
						class="ml-auto text-[10px] text-ink-400 font-mono bg-white px-1.5 py-0.5 rounded border border-ink-200"
						:class="collapsed ? 'lg:hidden' : ''"
						>⌘K</span
					>
				</button>
			</div>

			<nav class="flex-1 overflow-y-auto scrollbar-thin px-3 pb-4">
				<div
					v-for="group in navGroups"
					:key="group.key"
					class="mb-1"
					:class="group.topSeparator ? 'mt-4 pt-3 border-t border-ink-100' : 'mt-2'"
				>
					<!-- A collapsible group's label is the toggle; a fixed one stays a plain label
					     so it doesn't invite a click that does nothing. -->
					<component
						:is="group.collapsible ? 'button' : 'div'"
						:type="group.collapsible ? 'button' : null"
						class="px-2 py-1.5 w-full text-left"
						:class="[
							group.collapsible ? 'flex items-center gap-1.5 rounded hover:bg-ink-50' : '',
							collapsed ? 'lg:hidden' : '',
						]"
						@click="group.collapsible ? toggleGroup(group.key) : null"
					>
						<span
							class="font-semibold uppercase tracking-wider"
							:class="
								group.muted
									? 'text-[10px] text-ink-400'
									: 'text-[11px] text-ink-500'
							"
						>
							{{ group.title }}
						</span>
						<span
							v-if="group.collapsible"
							class="text-[9px] text-ink-300 tabular-nums"
							>{{ group.items.length }}</span
						>
						<svg
							v-if="group.collapsible"
							class="w-3 h-3 text-ink-300 ml-auto flex-shrink-0 transition-transform"
							:class="groupCollapsed(group) ? '-rotate-90' : ''"
							viewBox="0 0 24 24"
							fill="none"
							stroke="currentColor"
							stroke-width="2.5"
							stroke-linecap="round"
							stroke-linejoin="round"
						>
							<polyline points="6 9 12 15 18 9" />
						</svg>
					</component>
					<!-- BuildSuite items are SPA routes (RouterLink); ERPNext items link out to the
					     real Frappe desk (<a href> → full-page nav). Collapsed groups render no items. -->
					<component
						:is="item.external ? 'a' : 'RouterLink'"
						v-for="item in renderItems(group)"
						:key="item.slug || item.to"
						v-bind="item.external ? { href: item.href } : { to: item.to, activeClass: 'active' }"
						class="desk-nav-link flex items-center gap-2.5 px-2 py-1.5 rounded hover:bg-ink-50"
						:class="[
							group.muted ? 'text-sm text-ink-500' : 'text-sm text-ink-700',
							collapsed ? 'lg:justify-center' : '',
						]"
						:title="collapsed ? item.name : ''"
						@click="closeSidebar"
					>
						<span
							class="desk-icon w-5 h-5 flex items-center justify-center leading-none flex-shrink-0"
							:class="group.muted ? 'text-ink-300' : 'text-ink-400'"
						>
							<svg
								class="w-4 h-4"
								viewBox="0 0 24 24"
								fill="none"
								stroke="currentColor"
								stroke-width="1.75"
								stroke-linecap="round"
								stroke-linejoin="round"
								aria-hidden="true"
								v-html="getWorkspaceIconPath(item.slug)"
							/>
						</span>
						<span class="flex-1 truncate" :class="collapsed ? 'lg:hidden' : ''">{{ item.name }}</span>
						<span
							v-if="item.hint"
							:title="item.hint.title"
							class="text-[9px] font-medium text-ink-400 border border-ink-200 rounded px-1 leading-4 flex-shrink-0"
							:class="collapsed ? 'lg:hidden' : ''"
							>{{ item.hint.label }}</span
						>
					</component>
				</div>
			</nav>

			<!-- Collapse toggle — desktop only (below lg the sidebar is a drawer). -->
			<button
				type="button"
				class="hidden lg:flex items-center gap-2 mx-2 mb-1 px-2 py-1.5 rounded text-xs text-ink-500 hover:bg-ink-50"
				:class="collapsed ? 'lg:justify-center lg:mx-1' : ''"
				:title="collapsed ? 'Expand sidebar' : 'Collapse sidebar'"
				@click="toggleCollapse"
			>
				<svg
					class="w-4 h-4 flex-shrink-0 transition-transform"
					:class="collapsed ? 'rotate-180' : ''"
					viewBox="0 0 24 24"
					fill="none"
					stroke="currentColor"
					stroke-width="1.75"
					stroke-linecap="round"
					stroke-linejoin="round"
				>
					<path d="M15 18l-6-6 6-6" />
				</svg>
				<span :class="collapsed ? 'lg:hidden' : ''">Collapse</span>
			</button>

			<!-- Profile entry (prototype S149) — replaces the footer Settings link.
           Settings is still reachable from the topbar gear. No flow wired yet. -->
			<div class="border-t border-ink-200 p-2">
				<button
					type="button"
					class="w-full flex items-center gap-2 px-2 py-1.5 text-xs text-ink-700 hover:bg-ink-50 rounded"
					:class="collapsed ? 'lg:justify-center' : ''"
					:title="collapsed ? profileName : 'Profile'"
					@click="closeSidebar"
				>
					<UserAvatar :user-id="profileUser" size="sm" />
					<div class="flex-1 min-w-0 text-left" :class="collapsed ? 'lg:hidden' : ''">
						<div class="truncate font-medium text-ink-900">{{ profileName }}</div>
						<div class="truncate text-[10px] text-ink-500">{{ profileRole }}</div>
					</div>
				</button>
			</div>
		</aside>

		<!-- Main -->
		<div class="flex-1 flex flex-col min-w-0">
			<header
				class="h-12 bg-white border-b border-ink-200 px-3 sm:px-5 flex items-center sticky top-0 z-20 gap-2"
			>
				<!-- Hamburger — opens the sidebar drawer on mobile -->
				<button
					type="button"
					class="lg:hidden p-1.5 text-ink-600 hover:text-ink-900 hover:bg-ink-50 rounded"
					aria-label="Open menu"
					@click="sidebarOpen = true"
				>
					<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							stroke-width="2"
							d="M4 6h16M4 12h16M4 18h16"
						/>
					</svg>
				</button>
				<!-- To-dos — a permanent slot in the top nav; the badge counts your open items. -->
				<RouterLink
					to="/todo"
					class="flex items-center gap-2 h-8 px-2 rounded-lg text-ink-600 hover:text-ink-900 hover:bg-ink-50 shrink-0"
					:title="store.openTodoCount ? `To-dos — ${store.openTodoCount} open` : 'To-dos — your to-do list'"
				>
					<svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="1.8" viewBox="0 0 24 24">
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
						/>
					</svg>
					<span class="text-sm hidden sm:inline">To-dos</span>
					<span
						v-if="store.openTodoCount"
						class="text-[10px] font-semibold tabular-nums leading-none px-1.5 py-1 rounded-full bg-brand-700 text-white"
						>{{ store.openTodoCount }}</span
					>
				</RouterLink>

				<div class="ml-auto flex items-center gap-1 sm:gap-2">
					<!-- Theme toggle — sun in dark mode, moon in light mode -->
					<button
						type="button"
						class="text-ink-500 hover:text-ink-900 hover:bg-ink-50 p-1.5 rounded"
						:aria-label="
							store.theme === 'dark'
								? 'Switch to light theme'
								: 'Switch to dark theme'
						"
						:title="
							store.theme === 'dark'
								? 'Switch to light theme'
								: 'Switch to dark theme'
						"
						@click="toggleTheme"
					>
						<svg
							v-if="store.theme === 'dark'"
							class="w-4 h-4"
							fill="none"
							stroke="currentColor"
							viewBox="0 0 24 24"
						>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364-6.364l-.707.707M6.343 17.657l-.707.707m12.728 0l-.707-.707M6.343 6.343l-.707-.707M16 12a4 4 0 11-8 0 4 4 0 018 0z"
							/>
						</svg>
						<svg
							v-else
							class="w-4 h-4"
							fill="none"
							stroke="currentColor"
							viewBox="0 0 24 24"
						>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z"
							/>
						</svg>
					</button>
					<button class="text-ink-400 hover:text-ink-700 p-1.5 hidden sm:inline-flex">
						<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"
							/>
						</svg>
					</button>
					<button class="text-ink-400 hover:text-ink-700 p-1.5 hidden sm:inline-flex">
						<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
							/>
						</svg>
					</button>
					<!-- Settings (Session 32) — Frappe-standard topbar placement (gear icon
               near the user / role chip). Active state when on a /app/settings/* route. -->
					<RouterLink
						v-if="store.isAdmin"
						to="/settings"
						class="p-1.5 rounded-md"
						:class="
							route.path.startsWith('/settings')
								? 'text-brand-700 bg-brand-50'
								: 'text-ink-400 hover:text-ink-700'
						"
						title="Settings"
					>
						<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"
							/>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
							/>
						</svg>
					</RouterLink>
					<CompanySwitcher />
					<RoleSwitcher />
				</div>
			</header>

			<main class="flex-1 min-h-0">
				<router-view v-slot="{ Component }">
					<transition name="fade" mode="out-in">
						<component :is="Component" />
					</transition>
				</router-view>
			</main>
		</div>

		<!-- Search palette (⌘K) — PLACES (Go to) first, then RECORDS. One flat,
		     keyboard-navigable list; every row is permission-gated upstream. -->
		<div
			v-if="searchOpen"
			class="fixed inset-0 bg-ink-900/40 z-50 flex items-start justify-center pt-20 px-4"
			@click="closeSearch"
		>
			<div
				class="bg-white rounded-lg shadow-fp-lg w-full max-w-xl border border-ink-200 overflow-hidden"
				@click.stop
			>
				<div class="p-3 border-b border-ink-200 flex items-center gap-2">
					<svg
						class="w-4 h-4 text-ink-400 flex-shrink-0"
						fill="none"
						stroke="currentColor"
						viewBox="0 0 24 24"
					>
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							stroke-width="2"
							d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
						/>
					</svg>
					<input
						ref="searchInput"
						v-model="searchQuery"
						placeholder="Search anything — a project, a task, an order number..."
						class="w-full text-sm bg-transparent focus:outline-none text-ink-900 placeholder:text-ink-400"
						@keydown.down.prevent="moveSearch(1)"
						@keydown.up.prevent="moveSearch(-1)"
						@keydown.enter.prevent="goSearch(searchFlat[searchCursor])"
					/>
				</div>

				<div class="max-h-[26rem] overflow-y-auto">
					<!-- PLACES — where to go: a doctype's list, or a report. -->
					<div v-if="places.length" class="pt-2">
						<div
							class="px-3 pb-1 text-[10px] uppercase tracking-wider text-ink-500 font-medium"
						>
							Go to
						</div>
						<button
							v-for="(p, pi) in places"
							:key="p.key"
							type="button"
							class="w-full text-left px-3 py-2 flex items-center gap-2.5"
							:class="searchCursor === pi ? 'bg-brand-50' : 'hover:bg-ink-50'"
							@mouseenter="searchCursor = pi"
							@click="goSearch(p)"
						>
							<span
								class="w-7 h-7 rounded-lg bg-ink-50 text-ink-600 flex items-center justify-center flex-shrink-0"
							>
								<svg
									class="w-4 h-4"
									viewBox="0 0 24 24"
									fill="none"
									stroke="currentColor"
									stroke-width="1.75"
									stroke-linecap="round"
									stroke-linejoin="round"
									aria-hidden="true"
									v-html="getWorkspaceIconPath(p.icon)"
								/>
							</span>
							<span class="min-w-0 flex-1 truncate text-sm text-ink-900">{{ p.label }}</span>
							<span class="text-[10px] text-ink-400 flex-shrink-0">{{
								p.isReport ? "report" : "list"
							}}</span>
						</button>
					</div>

					<!-- RECORDS — the documents themselves. -->
					<div v-if="recordRows.length" class="pt-2 pb-2">
						<div
							class="px-3 pb-1 text-[10px] uppercase tracking-wider text-ink-500 font-medium"
						>
							Records
						</div>
						<button
							v-for="(r, ri) in recordRows"
							:key="r.key"
							type="button"
							class="w-full text-left px-3 py-2 flex items-center gap-2.5"
							:class="
								searchCursor === places.length + ri ? 'bg-brand-50' : 'hover:bg-ink-50'
							"
							@mouseenter="searchCursor = places.length + ri"
							@click="goSearch(r)"
						>
							<span
								class="w-7 h-7 rounded-lg bg-ink-50 text-ink-600 flex items-center justify-center flex-shrink-0"
							>
								<svg
									class="w-4 h-4"
									viewBox="0 0 24 24"
									fill="none"
									stroke="currentColor"
									stroke-width="1.75"
									stroke-linecap="round"
									stroke-linejoin="round"
									aria-hidden="true"
									v-html="getWorkspaceIconPath(r.icon)"
								/>
							</span>
							<span class="min-w-0 flex-1 truncate text-sm text-ink-900">{{ r.title }}</span>
							<span class="text-[10px] text-ink-400 flex-shrink-0">{{ r.type }}</span>
						</button>
					</div>

					<!-- Nothing matched a searchable query. -->
					<div
						v-if="searchQuery.trim().length >= 2 && !searchFlat.length"
						class="px-3 py-6 text-center"
					>
						<div class="text-sm text-ink-700">No matches</div>
						<div class="text-[11px] text-ink-500 mt-1">
							Try a project, a person, a supplier, or a document number.
						</div>
					</div>

					<!-- Before they have typed enough to search on. -->
					<div v-if="searchQuery.trim().length < 2" class="px-3 py-6 text-center">
						<div class="text-sm text-ink-700">Type to search</div>
						<div class="text-[11px] text-ink-500 mt-1">
							Jump to a list or report, or find a record by name or number.
						</div>
					</div>
				</div>

				<div
					class="px-3 py-2 border-t border-ink-200 bg-ink-50 flex items-center gap-3 text-[10px] text-ink-500"
				>
					<span>↑↓ to move</span><span>Enter to open</span><span>Esc to close</span>
				</div>
			</div>
		</div>
	</div>
</template>
