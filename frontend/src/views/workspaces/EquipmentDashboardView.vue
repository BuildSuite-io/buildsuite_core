<script setup>
// Equipment dashboard — plant register + usage cost at a glance. Mirrors the demo.

import { computed, ref, onMounted } from "vue";
import { RouterLink, useRouter } from "vue-router";
import { fmtINR, fmtCompactINR, fmtDate } from "@/utils/format";
import { getWorkspaceIconPath } from "@/utils/workspaceIcons";
import { getEquipmentDashboard } from "@/data/equipmentApi";
import { useProjectNames } from "@/composables/useProjectNames";
import StatusBadge from "@/components/StatusBadge.vue";

const router = useRouter();
const { projectName } = useProjectNames();

const today = computed(() =>
	new Date().toLocaleDateString("en-US", { weekday: "long", month: "short", day: "numeric" })
);

const loading = ref(true);
const error = ref("");
const kpis = ref(null);

onMounted(loadDashboard);

async function loadDashboard() {
	loading.value = true;
	error.value = "";
	try {
		kpis.value = await getEquipmentDashboard();
	} catch (e) {
		error.value = e.message || "Could not load the dashboard.";
	} finally {
		loading.value = false;
	}
}

const recentUsage = computed(() => kpis.value?.recent_usage || []);
const register = computed(() => kpis.value?.register || []);
</script>

<template>
	<div class="bg-white min-h-full">
		<div class="max-w-6xl mx-auto px-6 py-8">
			<div class="mb-6">
				<div class="text-xs text-ink-500 mb-1 flex items-center gap-2">
					<RouterLink to="/equipment" class="hover:text-brand-700">Equipment</RouterLink>
					<span class="text-ink-300">/</span>
					<span>Dashboard</span>
					<span class="text-ink-300 mx-2">·</span>
					<span>{{ today }}</span>
				</div>
				<h1 class="text-2xl font-semibold text-ink-900">Equipment Dashboard</h1>
				<p class="text-xs text-ink-500 mt-1">
					Plant register, utilisation and equipment cost at a glance.
				</p>
			</div>

			<div v-if="loading" class="text-sm text-ink-500 py-8">Loading…</div>
			<div v-else-if="error" class="text-sm text-danger-700 py-8">{{ error }}</div>

			<template v-else-if="kpis">
				<!-- ===== KPI strip ===== -->
				<div class="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
					<div class="card p-4 bg-white border border-ink-200">
						<div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">
							Machines
						</div>
						<div class="text-2xl font-semibold text-ink-900 tabular-nums mt-1.5">
							{{ kpis.machines }}
						</div>
						<div class="text-[10px] text-ink-400 mt-1">In the register</div>
					</div>

					<div class="card p-4 bg-white border border-ink-200">
						<div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">
							Owned
						</div>
						<div class="text-2xl font-semibold text-ink-900 tabular-nums mt-1.5">
							{{ kpis.owned }}
						</div>
						<div class="text-[10px] text-ink-400 mt-1">Company-owned plant</div>
					</div>

					<div class="card p-4 bg-white border border-ink-200">
						<div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">
							Hired
						</div>
						<div class="text-2xl font-semibold text-warning-700 tabular-nums mt-1.5">
							{{ kpis.hired }}
						</div>
						<div class="text-[10px] text-ink-400 mt-1">On hire from vendors</div>
					</div>

					<div class="card p-4 bg-white border border-ink-200">
						<div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">
							Equipment cost
						</div>
						<div class="text-2xl font-semibold text-info-700 tabular-nums mt-1.5">
							{{ fmtCompactINR(kpis.equipment_cost) }}
						</div>
						<div class="text-[10px] text-ink-400 mt-1">Usage + fuel logged</div>
					</div>
				</div>

				<!-- ===== Panels ===== -->
				<div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
					<!-- Recent usage -->
					<div class="card border border-ink-200">
						<div
							class="flex items-center justify-between px-4 py-3 border-b border-ink-100 bg-gradient-to-r from-brand-50 to-white"
						>
							<div class="flex items-center gap-2">
								<svg
									class="w-4 h-4 text-brand-700"
									viewBox="0 0 24 24"
									fill="none"
									stroke="currentColor"
									stroke-width="1.8"
									stroke-linecap="round"
									stroke-linejoin="round"
									aria-hidden="true"
									v-html="getWorkspaceIconPath('clipboard-list')"
								/>
								<h2 class="text-sm font-semibold text-ink-900">Recent usage</h2>
							</div>
							<RouterLink
								to="/machinery-usage"
								class="text-xs text-brand-700 hover:underline"
								>View all →</RouterLink
							>
						</div>
						<ul v-if="recentUsage.length" class="divide-y divide-ink-50">
							<li
								v-for="u in recentUsage"
								:key="u.name"
								class="px-4 py-3 hover:bg-brand-50/30 cursor-pointer"
								@click="router.push(`/machinery-usage/${u.name}`)"
							>
								<div class="flex items-center justify-between">
									<span class="text-sm text-ink-900 font-medium">{{
										u.machine_name || u.machine
									}}</span>
									<span class="text-sm text-ink-900 tabular-nums">{{
										fmtCompactINR(u.total)
									}}</span>
								</div>
								<div class="text-[11px] text-ink-500 mt-0.5">
									{{ projectName(u.project) || "—" }} · {{ fmtDate(u.date) }} ·
									{{ u.quantity }} {{ u.unit }}
								</div>
							</li>
						</ul>
						<div v-else class="px-4 py-6 text-sm text-ink-400">
							No usage logged yet.
						</div>
					</div>

					<!-- Register -->
					<div class="card border border-ink-200">
						<div
							class="flex items-center justify-between px-4 py-3 border-b border-ink-100 bg-gradient-to-r from-info-50 to-white"
						>
							<div class="flex items-center gap-2">
								<svg
									class="w-4 h-4 text-info-700"
									viewBox="0 0 24 24"
									fill="none"
									stroke="currentColor"
									stroke-width="1.8"
									stroke-linecap="round"
									stroke-linejoin="round"
									aria-hidden="true"
									v-html="getWorkspaceIconPath('wrench')"
								/>
								<h2 class="text-sm font-semibold text-ink-900">Register</h2>
							</div>
							<RouterLink
								to="/machinery"
								class="text-xs text-brand-700 hover:underline"
								>View all →</RouterLink
							>
						</div>
						<ul v-if="register.length" class="divide-y divide-ink-50">
							<li
								v-for="m in register"
								:key="m.name"
								class="px-4 py-3 hover:bg-brand-50/30 cursor-pointer"
								@click="router.push(`/machinery/${m.name}`)"
							>
								<div class="flex items-center justify-between">
									<span class="text-sm text-ink-900 font-medium">{{
										m.machinery_name
									}}</span>
									<span class="text-sm text-ink-700 tabular-nums">{{
										m.rate ? fmtINR(m.rate) + "/" + (m.rate_unit || "—") : "—"
									}}</span>
								</div>
								<div
									class="text-[11px] text-ink-500 mt-0.5 flex items-center gap-1.5"
								>
									<StatusBadge :status="m.status" size="xs" />
									<span
										>· {{ m.machinery_type || "—" }} · {{ m.ownership }}</span
									>
								</div>
							</li>
						</ul>
						<div v-else class="px-4 py-6 text-sm text-ink-400">
							No machines registered.
						</div>
					</div>
				</div>
			</template>
		</div>
	</div>
</template>
