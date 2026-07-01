<script setup>
// BOQ list — backend-backed via the data adapter (Construction Rate Master / Assembly
// pattern). Rows/KPIs are transformed into the same shape the Desk template expects.

import { computed, ref } from "vue";
import { useRouter } from "vue-router";
import { useDataStore } from "@/stores";
import { createDataAdapter } from "@/data/adapters";
import { useDocTypeList } from "@/composables/useDocTypeList";
import { showToast } from "@/utils/appToast";
import { parseFrappeError } from "@/utils/frappeError";
import StatusBadge from "@/components/StatusBadge.vue";
import DeskPage from "@/components/desk/DeskPage.vue";
import DeskList from "@/components/desk/DeskList.vue";
import DeskSelect from "@/components/desk/DeskSelect.vue";
import DeskField from "@/components/desk/DeskField.vue";
import DeskInput from "@/components/desk/DeskInput.vue";
import DeskLink from "@/components/desk/DeskLink.vue";
import DeskLinkPicker from "@/components/desk/DeskLinkPicker.vue";
import DeskFilterChip from "@/components/desk/DeskFilterChip.vue";
import { fmtCompactINR, fmtINR } from "@/utils/format";

const router = useRouter();
const adapter = createDataAdapter(useDataStore());

const search = ref("");
const projectFilter = ref("");
const statusFilter = ref("");
const showNew = ref(false);
const newForm = ref({ projectId: "", title: "" });
const creating = ref(false);

// Projects (for filter labels + the new-BOQ picker).
const projectsRes = useDocTypeList("Project", {
	fields: ["name", "project_name", "custom_project_id", "parent_project"],
	orderBy: "project_name asc",
	// Fetch all projects so every BOQ row resolves its project name + code (a
	// `pageLength: 0` is treated as the default page of 20, which left rows
	// falling back to the raw project id). Explicit high cap = "effectively all".
	pageLength: 5000,
	cache: "buildsuite-boq-projects",
});
const projectsMap = computed(() => {
	const map = {};
	for (const p of projectsRes.data || []) {
		map[p.name] = { name: p.project_name || p.name, code: p.custom_project_id || "" };
	}
	return map;
});
function projectName(id) {
	return projectsMap.value[id]?.name || id;
}

const boqRes = useDocTypeList("BOQ", {
	fields: [
		"name",
		"title",
		"project",
		"revision",
		"status",
		"planned_amount",
		"actual_amount",
		"prepared_date",
	],
	orderBy: "creation desc",
	// Show every BOQ (client-side search/filter over the fetched rows); a
	// `pageLength: 0` capped the list at 20. Explicit high cap = "effectively all".
	pageLength: 5000,
	cache: "buildsuite-boq-list",
	transform: (data) =>
		data.map((b) => {
			const planned = b.planned_amount || 0;
			const actual = b.actual_amount || 0;
			const variance = actual - planned;
			return {
				id: b.name,
				title: b.title,
				projectId: b.project,
				revision: b.revision,
				status: b.status,
				preparedDate: b.prepared_date,
				totals: {
					planned,
					actual,
					variance,
					variancePct: planned ? (variance / planned) * 100 : 0,
				},
			};
		}),
});

const rows = computed(() => {
	const term = search.value.trim().toLowerCase();
	let list = boqRes.data || [];
	if (projectFilter.value) list = list.filter((b) => b.projectId === projectFilter.value);
	if (statusFilter.value) list = list.filter((b) => b.status === statusFilter.value);
	if (term)
		list = list.filter(
			(b) =>
				b.id.toLowerCase().includes(term) || (b.title || "").toLowerCase().includes(term)
		);
	return list.map((b) => ({
		...b,
		projectName: projectsMap.value[b.projectId]?.name || b.projectId,
		projectCode: projectsMap.value[b.projectId]?.code || "",
	}));
});

const kpis = computed(() => {
	const all = boqRes.data || [];
	const approved = all.filter((b) => b.status === "Approved");
	const totalPlanned = approved.reduce((a, b) => a + b.totals.planned, 0);
	const totalActual = approved.reduce((a, b) => a + b.totals.actual, 0);
	const variance = totalActual - totalPlanned;
	return {
		active: approved.length,
		draft: all.filter((b) => b.status === "Draft").length,
		submitted: all.filter((b) => b.status === "Submitted").length,
		totalPlanned,
		totalActual,
		variance,
		variancePct: totalPlanned ? (variance / totalPlanned) * 100 : 0,
	};
});

function variancePill(pct) {
	if (Math.abs(pct) < 0.5) return "text-ink-500";
	return pct > 0 ? "text-danger-700" : "text-success-700";
}

// Backend stores "Superseded"; the prototype renames it to "Replaced" for display.
function statusLabel(s) {
	return s === "Superseded" ? "Replaced" : s;
}

function openNew() {
	newForm.value = { projectId: "", title: "" };
	showNew.value = true;
}
async function createBoq() {
	if (!newForm.value.projectId || creating.value) return;
	creating.value = true;
	try {
		const title =
			newForm.value.title?.trim() || `${projectName(newForm.value.projectId)} — BOQ`;
		const res = await adapter.create("BOQ", { project: newForm.value.projectId, title });
		showNew.value = false;
		router.push(`/boq/${res.name}`);
	} catch (err) {
		showToast(parseFrappeError(err).summary ?? "Failed to create BOQ", "error");
	} finally {
		creating.value = false;
	}
}

function onRowClick(row) {
	router.push(`/boq/${row.id}`);
}

const columns = [
	{ key: "id", label: "ID" },
	{ key: "project", label: "Project" },
	{ key: "revision", label: "Rev.", align: "center" },
	{ key: "status", label: "Status" },
	{ key: "planned", label: "Planned", align: "right" },
	{ key: "actual", label: "Actual", align: "right" },
	{ key: "variance", label: "Variance", align: "right" },
];

const breadcrumbs = [{ label: "BuildSuite Core", to: "/" }, { label: "BOQ" }];
const subtitle = computed(
	() => `${rows.value.length} of ${(boqRes.data || []).length} · estimation`
);
</script>

<template>
	<DeskPage title="Bill of Quantities" :subtitle="subtitle" :breadcrumbs="breadcrumbs">
		<template #actions>
			<DeskLink
				to="/rate-master"
				class="text-xs px-2 py-1 border border-ink-200 bg-white hover:bg-ink-50"
				style="border-radius: 2px"
				>₹ Rate Master</DeskLink
			>
			<button type="button" class="desk-save-btn" @click="openNew">+ New BOQ</button>
		</template>

		<!-- KPI strip -->
		<div class="grid grid-cols-2 md:grid-cols-5 gap-2 mb-4">
			<div class="bg-white border border-ink-200 px-3 py-2" style="border-radius: 2px">
				<div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">
					Approved
				</div>
				<div class="text-base font-semibold text-success-700 mt-0.5">
					{{ kpis.active }}
				</div>
			</div>
			<div class="bg-white border border-ink-200 px-3 py-2" style="border-radius: 2px">
				<div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">
					Drafts
				</div>
				<div class="text-base font-semibold text-ink-700 mt-0.5">{{ kpis.draft }}</div>
			</div>
			<div class="bg-white border border-ink-200 px-3 py-2" style="border-radius: 2px">
				<div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">
					Submitted
				</div>
				<div class="text-base font-semibold text-warning-700 mt-0.5">
					{{ kpis.submitted }}
				</div>
			</div>
			<div class="bg-white border border-ink-200 px-3 py-2" style="border-radius: 2px">
				<div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">
					Total planned
				</div>
				<div class="text-base font-semibold text-ink-900 mt-0.5 tabular-nums">
					{{ fmtCompactINR(kpis.totalPlanned) }}
				</div>
				<div class="text-[10px] text-ink-500 mt-0.5">approved BOQs</div>
			</div>
			<div class="bg-white border border-ink-200 px-3 py-2" style="border-radius: 2px">
				<div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">
					Variance
				</div>
				<div
					class="text-base font-semibold mt-0.5 tabular-nums"
					:class="variancePill(kpis.variancePct)"
				>
					{{ kpis.variancePct > 0 ? "+" : "" }}{{ kpis.variancePct.toFixed(1) }}%
				</div>
				<div class="text-[10px] text-ink-500 mt-0.5">
					{{ fmtCompactINR(kpis.variance) }} delta
				</div>
			</div>
		</div>

		<DeskList
			v-model="search"
			:rows="rows"
			:columns="columns"
			row-key="id"
			search-placeholder="Search BOQ id or title…"
			@row-click="onRowClick"
		>
			<template #filter-chips>
				<div v-if="!projectFilter" class="w-48">
					<DeskLinkPicker
						v-model="projectFilter"
						doctype="Project"
						label-field="project_name"
						value-field="name"
						:search-fields="['project_name', 'custom_project_id', 'name']"
						placeholder="Project: Any"
					/>
				</div>
				<DeskFilterChip
					v-else
					label="Project"
					:value="projectName(projectFilter)"
					@remove="projectFilter = ''"
				/>

				<DeskSelect v-if="!statusFilter" v-model="statusFilter" class="!w-36">
					<option value="">Status: Any</option>
					<option>Draft</option>
					<option>Submitted</option>
					<option>Approved</option>
					<option value="Superseded">Replaced</option>
				</DeskSelect>
				<DeskFilterChip
					v-else
					label="Status"
					:value="statusLabel(statusFilter)"
					@remove="statusFilter = ''"
				/>
			</template>

			<template #cell-id="{ row }">
				<DeskLink :to="`/boq/${row.id}`" @click.stop class="font-mono text-xs">{{
					row.id
				}}</DeskLink>
			</template>
			<template #cell-project="{ row }">
				<div class="text-xs">
					<div class="text-ink-900">{{ row.projectName }}</div>
					<div class="font-mono text-ink-400">{{ row.projectCode }}</div>
				</div>
			</template>
			<template #cell-revision="{ row }">
				<span
					class="font-mono text-xs px-1.5 py-0.5 bg-ink-100 text-ink-700"
					style="border-radius: 2px"
					>R{{ row.revision }}</span
				>
			</template>
			<template #cell-status="{ row }">
				<StatusBadge :status="row.status" />
			</template>
			<template #cell-planned="{ row }">
				<span class="tabular-nums text-ink-900">{{ fmtINR(row.totals.planned) }}</span>
			</template>
			<template #cell-actual="{ row }">
				<span class="tabular-nums text-ink-700">{{ fmtINR(row.totals.actual) }}</span>
			</template>
			<template #cell-variance="{ row }">
				<span class="tabular-nums" :class="variancePill(row.totals.variancePct)">
					{{ row.totals.variancePct > 0 ? "+" : ""
					}}{{ row.totals.variancePct.toFixed(1) }}%
				</span>
			</template>

			<template #empty>
				<div class="text-sm text-ink-500">No BOQs match these filters.</div>
			</template>
		</DeskList>

		<!-- New BOQ modal -->
		<div
			v-if="showNew"
			class="fixed inset-0 bg-ink-900/40 z-[60] flex items-center justify-center p-4"
			@click="showNew = false"
		>
			<div
				class="bg-white border border-ink-200 shadow-fp-lg w-full max-w-md"
				style="border-radius: 2px"
				@click.stop
			>
				<div class="px-4 py-3 border-b border-ink-200 flex items-center">
					<h2 class="text-sm font-semibold text-ink-900">New BOQ</h2>
					<button
						type="button"
						@click="showNew = false"
						class="ml-auto text-ink-400 hover:text-ink-900"
						aria-label="Close"
					>
						✕
					</button>
				</div>
				<div class="p-4 space-y-3">
					<DeskField label="Project" required>
						<DeskLinkPicker
							v-model="newForm.projectId"
							doctype="Project"
							label-field="project_name"
							value-field="name"
							:search-fields="['project_name', 'custom_project_id', 'name']"
							placeholder="Select a project"
						/>
					</DeskField>
					<DeskField label="Title" hint="Leave blank to auto-name.">
						<DeskInput v-model="newForm.title" placeholder="e.g. Tender draft…" />
					</DeskField>
				</div>
				<div class="px-4 py-2 border-t border-ink-200 flex items-center justify-end gap-2">
					<button
						type="button"
						@click="showNew = false"
						class="text-xs text-ink-600 hover:text-ink-900 px-2 py-1"
					>
						Cancel
					</button>
					<button
						type="button"
						@click="createBoq"
						class="desk-save-btn"
						:disabled="creating"
					>
						{{ creating ? "Creating…" : "Create draft" }}
					</button>
				</div>
			</div>
		</div>
	</DeskPage>
</template>
