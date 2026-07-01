<script setup>
import { computed } from "vue";
import { RouterLink } from "vue-router";
import { ROLES } from "@/data/roles";
import { WORKSPACE_META, ACCESS_LABEL, workspaceMetric } from "@/data/workspaces";
import { useDataStore } from "@/stores";
import LandingShell from "@/layouts/LandingShell.vue";

const ROLE_ID = "store-keeper";
const role = ROLES.find((r) => r.id === ROLE_ID);
const store = useDataStore();

// Prototype assumption: there is no dedicated "Store Keeper" in the seed team — USR-007
// (Suresh N., labelled "Procurement") doubles as the store-keeper persona for demo, since
// in small construction firms procurement and store-keeping are often the same person.
// When the prototype gains real auth, this becomes the team member with the Store Keeper
// role assignment.
const STORE_KEEPER_USER_ID = "USR-007";

const today = new Date();
const todayLabel = today.toLocaleDateString("en-IN", {
	weekday: "long",
	day: "2-digit",
	month: "short",
	year: "numeric",
});

// All four KPI values below are ILLUSTRATIVE — the seed has no stock / GRN / issue / wastage
// data. Replace with live store reads once the M4 Procurement + ERPNext Stock screens are
// wired (see CLAUDE.md §12.2 / §12.6).
const ILLUSTRATIVE_KPIS = [
	{ label: "Items below threshold", value: "12", sub: "Stock alerts" },
	{ label: "GRN today", value: "4", sub: "Goods receipts" },
	{ label: "Issues to crew", value: "7", sub: "Pending issue" },
	{ label: "Wastage this week", value: "2.3%", sub: "Reconciled" },
];

// Illustrative GRN list — would come from ERPNext Stock entries with consumption_purpose=
// 'Receive' once wired. Items chosen to match real seed rate-master codes so the list at
// least references things that exist elsewhere in the prototype.
const todaysGRNs = [
	{
		id: "GRN-2026-0421",
		supplier: "UltraTech Cement Ltd.",
		item: "Cement OPC 53",
		qty: "200 bags",
		expectedAt: "10:30",
	},
	{
		id: "GRN-2026-0422",
		supplier: "JSW Steel",
		item: "TMT Fe500 — 12mm",
		qty: "4.5 MT",
		expectedAt: "12:00",
	},
	{
		id: "GRN-2026-0423",
		supplier: "Prism Johnson",
		item: "RMC M30",
		qty: "18 m³",
		expectedAt: "14:00",
	},
	{
		id: "GRN-2026-0424",
		supplier: "Sand Suppliers Co-op",
		item: "River sand",
		qty: "24 m³",
		expectedAt: "15:30",
	},
	{
		id: "GRN-2026-0425",
		supplier: "Local Brick Kiln Network",
		item: "Common burnt bricks",
		qty: "8,000 nos",
		expectedAt: "16:00",
	},
];

const tiles = computed(() =>
	store.visibleWorkspaces.map((slug) => ({
		slug,
		...WORKSPACE_META[slug],
		metric: workspaceMetric(slug, store),
		access: store.workspaceAccess(slug),
	}))
);
</script>

<template>
	<LandingShell>
		<div class="max-w-5xl mx-auto px-6 py-10">
			<!-- Greeting -->
			<div class="flex items-center gap-3 mb-2">
				<span :class="role.color" class="w-2.5 h-2.5 rounded-full"></span>
				<p class="text-xs text-ink-500 uppercase tracking-wider font-medium">
					{{ role.shortName }} · Site stores
				</p>
			</div>
			<h1 class="text-2xl font-semibold text-ink-900 tracking-tight">Stock status today</h1>
			<p class="text-sm text-ink-500 mt-1">
				{{ todayLabel }} ·
				<span class="text-ink-700 font-medium"
					>{{ todaysGRNs.length }} GRN{{ todaysGRNs.length === 1 ? "" : "s" }} expected
					today</span
				>
			</p>

			<!-- KPIs -->
			<div class="grid grid-cols-2 md:grid-cols-4 gap-3 mt-8">
				<div
					v-for="k in ILLUSTRATIVE_KPIS"
					:key="k.label"
					class="bg-white border border-ink-200 rounded-xl p-4"
				>
					<div class="text-[11px] uppercase tracking-wider text-ink-500 font-medium">
						{{ k.label }}
					</div>
					<div class="text-2xl font-semibold text-ink-900 mt-1">{{ k.value }}</div>
					<div class="text-[11px] text-ink-400 mt-0.5">{{ k.sub }}</div>
				</div>
			</div>

			<!-- Today's GRN list -->
			<h2 class="text-sm font-semibold text-ink-900 mt-10 mb-3">Today's GRN list</h2>
			<div class="bg-white border border-ink-200 rounded-xl overflow-hidden">
				<div class="divide-y divide-ink-100">
					<RouterLink
						v-for="g in todaysGRNs"
						:key="g.id"
						to="/stock"
						class="flex items-center gap-3 px-4 py-3 hover:bg-ink-50"
					>
						<div
							class="w-8 h-8 rounded-lg bg-info-50 text-info-700 flex items-center justify-center text-xs font-mono"
						>
							📦
						</div>
						<div class="flex-1 min-w-0">
							<div class="text-sm font-medium text-ink-900 truncate">
								{{ g.item }} · {{ g.qty }}
							</div>
							<div class="text-xs text-ink-500 mt-0.5 truncate">
								{{ g.supplier }} · expected {{ g.expectedAt }}
							</div>
						</div>
						<span class="text-[10px] text-ink-500 font-mono flex-shrink-0">{{
							g.id
						}}</span>
					</RouterLink>
				</div>
			</div>

			<!-- Your workspaces -->
			<h2 class="text-sm font-semibold text-ink-900 mt-10 mb-3">Your workspaces</h2>
			<div class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
				<RouterLink
					v-for="t in tiles"
					:key="t.slug"
					:to="t.to"
					class="block bg-white border border-ink-200 rounded-xl p-4 hover:border-brand-400 hover:shadow-fp-md transition-all"
				>
					<div class="flex items-start gap-3">
						<div class="text-2xl">{{ t.icon }}</div>
						<div class="flex-1 min-w-0">
							<div class="flex items-center gap-2 flex-wrap">
								<span class="text-sm font-medium text-ink-900">{{ t.name }}</span>
								<span
									v-if="t.access && t.access !== 'full'"
									class="text-[9px] font-medium text-ink-500 border border-ink-200 rounded px-1.5 leading-4"
									>{{ ACCESS_LABEL[t.access] }}</span
								>
							</div>
							<div class="text-[11px] text-ink-500 mt-1 leading-snug">
								{{ t.desc }}
							</div>
							<div
								v-if="t.metric"
								class="text-[11px] text-brand-700 font-medium mt-2"
							>
								{{ t.metric }}
							</div>
						</div>
					</div>
				</RouterLink>
			</div>
		</div>
	</LandingShell>
</template>
