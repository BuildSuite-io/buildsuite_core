<script setup>
// BOQ list — backend-backed via the data adapter (Construction Rate Master / Assembly
// pattern). Rows/KPIs are transformed into the same shape the Desk template expects.

import { computed, ref, watch } from "vue";
import { useRouter } from "vue-router";
import { useDataStore } from "@/stores";
import { getActualsTotals } from "@/utils/boqApi";
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
import { usePermissions } from "@/composables/usePermissions";
import { activeCompanyFilter } from "@/composables/useActiveCompany";
import { fmtCompactINR, fmtINR, currencySymbol } from "@/utils/format";
import { __ } from "@/utils/translate";

const router = useRouter();
const adapter = createDataAdapter(useDataStore());
const { canCreate } = usePermissions();
// Scope the Project pickers to the active company; re-queries when the switcher changes.
const companyFilter = activeCompanyFilter();

const search = ref("");
const projectFilter = ref("");
const statusFilter = ref("");
// Estimates (no project yet) and project BOQs are one doctype — one list with a scope filter.
const scopeFilter = ref("");
const showNew = ref(false);
// `for` decides what is being made: an estimate priced before the work is won (customer + title,
// no project), or a revision under a project that already exists. Same doctype either way.
const newForm = ref({ for: "estimate", projectId: "", title: "", customer: "" });
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

// Customers — for the new-BOQ customer picker label + resolving an estimate's customer name in
// the list (the BOQ stores the Customer link id).
const customersRes = useDocTypeList("Customer", {
	fields: ["name", "customer_name"],
	orderBy: "customer_name asc",
	pageLength: 5000,
	cache: "buildsuite-boq-customers",
});
const customersMap = computed(() => {
	const map = {};
	for (const c of customersRes.data || []) map[c.name] = c.customer_name || c.name;
	return map;
});
function customerName(id) {
	return id ? customersMap.value[id] || id : "";
}

const boqRes = useDocTypeList("BOQ", {
	fields: [
		"name",
		"title",
		"project",
		"customer",
		"revision",
		"status",
		"planned_amount",
		"prepared_date",
	],
	orderBy: "creation desc",
	// Show every BOQ (client-side search/filter over the fetched rows); a
	// `pageLength: 0` capped the list at 20. Explicit high cap = "effectively all".
	pageLength: 5000,
	cache: "buildsuite-boq-list",
	// Actual/variance are layered on in `withActuals` from the cost-code log, not the stored
	// actual_amount — so only planned is carried here.
	transform: (data) =>
		data.map((b) => ({
			id: b.name,
			title: b.title,
			projectId: b.project,
			customer: b.customer,
			isEstimate: !b.project,
			revision: b.revision,
			status: b.status,
			preparedDate: b.prepared_date,
			totals: { planned: b.planned_amount || 0 },
		})),
});

// Actual is COST, not progress: the stored BOQ.actual_amount is task-progress earned value
// (0 until a task-linked recalc runs), which disagreed with the BOQ page — that reads the
// cost-code actuals log (Material + Subcontract + Expense + JV by cost code, per project). Pull
// the same per-project totals here so the list reconciles with the page (R2). Actuals are a
// project quantity, so every revision of a project shows the same actual; an estimate (no
// project) has none.
const actualsByProject = ref({});
watch(
	() => boqRes.data,
	async (data) => {
		const pids = [...new Set((data || []).map((b) => b.projectId).filter(Boolean))];
		if (!pids.length) {
			actualsByProject.value = {};
			return;
		}
		try {
			actualsByProject.value = (await getActualsTotals(pids)) || {};
		} catch {
			actualsByProject.value = {};
		}
	},
	{ immediate: true }
);

// The fetched BOQs with Actual sourced from the cost-code log (not the stored field).
const withActuals = computed(() =>
	(boqRes.data || []).map((b) => {
		const planned = b.totals.planned;
		const actual = b.isEstimate ? 0 : actualsByProject.value[b.projectId] || 0;
		const variance = actual - planned;
		return {
			...b,
			totals: {
				planned,
				actual,
				variance,
				variancePct: planned ? (variance / planned) * 100 : 0,
			},
		};
	})
);

const rows = computed(() => {
	const term = search.value.trim().toLowerCase();
	let list = withActuals.value;
	if (scopeFilter.value === "estimate") list = list.filter((b) => b.isEstimate);
	if (scopeFilter.value === "project") list = list.filter((b) => !b.isEstimate);
	if (projectFilter.value) list = list.filter((b) => b.projectId === projectFilter.value);
	if (statusFilter.value) list = list.filter((b) => b.status === statusFilter.value);
	if (term)
		list = list.filter(
			(b) =>
				b.id.toLowerCase().includes(term) ||
				(b.title || "").toLowerCase().includes(term) ||
				customerName(b.customer).toLowerCase().includes(term)
		);
	return list.map((b) => ({
		...b,
		projectName: projectsMap.value[b.projectId]?.name || b.projectId,
		projectCode: projectsMap.value[b.projectId]?.code || "",
		customerName: customerName(b.customer),
	}));
});

const kpis = computed(() => {
	const all = withActuals.value;
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
	return s === "Superseded" ? __("Replaced") : __(s);
}

function openNew() {
	newForm.value = { for: "estimate", projectId: "", title: "", customer: "" };
	showNew.value = true;
}
// An estimate needs a title (it is how it is found until it has a project); a project BOQ needs a
// project (its title can auto-name). Distinct from the `canCreate('boq')` permission gate.
const formValid = computed(() =>
	newForm.value.for === "estimate" ? !!newForm.value.title.trim() : !!newForm.value.projectId
);
async function createBoq() {
	if (!formValid.value || creating.value) return;
	creating.value = true;
	try {
		const forProject = newForm.value.for === "project";
		const title = forProject
			? newForm.value.title?.trim() || `${projectName(newForm.value.projectId)} — BOQ`
			: newForm.value.title.trim();
		const payload = forProject
			? { project: newForm.value.projectId, title }
			: { project: null, customer: newForm.value.customer || null, title };
		const res = await adapter.create("BOQ", payload);
		showNew.value = false;
		router.push(`/boq/${res.name}`);
	} catch (err) {
		showToast(parseFrappeError(err).summary ?? __("Failed to create BOQ"), "error");
	} finally {
		creating.value = false;
	}
}

function onRowClick(row) {
	router.push(`/boq/${row.id}`);
}

const columns = [
	{ key: "id", label: __("ID") },
	{ key: "project", label: __("Project") },
	{ key: "revision", label: __("Rev."), align: "center" },
	{ key: "status", label: __("Status") },
	{ key: "planned", label: __("Planned"), align: "right" },
	{ key: "actual", label: __("Actual"), align: "right" },
	{ key: "variance", label: __("Variance"), align: "right" },
];

const breadcrumbs = [{ label: __("BuildSuite Core"), to: "/" }, { label: __("BOQ") }];
const subtitle = computed(() =>
	__("{0} of {1} · estimation", [rows.value.length, (boqRes.data || []).length])
);
</script>

<template>
	<DeskPage :title="__('Bill of Quantities')" :subtitle="subtitle" :breadcrumbs="breadcrumbs">
		<template #actions>
			<DeskLink
				to="/rate-master"
				class="text-xs px-2 py-1 border border-ink-200 bg-white hover:bg-ink-50"
				style="border-radius: 2px"
				>{{ currencySymbol() }} Rate Master</DeskLink
			>
			<button v-if="canCreate('boq')" type="button" class="desk-save-btn" @click="openNew">
				{{ __("+ New BOQ") }}
			</button>
		</template>

		<!-- KPI strip -->
		<div class="grid grid-cols-2 md:grid-cols-5 gap-2 mb-4">
			<div class="bg-white border border-ink-200 px-3 py-2" style="border-radius: 2px">
				<div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">
					{{ __("Approved") }}
				</div>
				<div class="text-base font-semibold text-success-700 mt-0.5">
					{{ kpis.active }}
				</div>
			</div>
			<div class="bg-white border border-ink-200 px-3 py-2" style="border-radius: 2px">
				<div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">
					{{ __("Drafts") }}
				</div>
				<div class="text-base font-semibold text-ink-700 mt-0.5">{{ kpis.draft }}</div>
			</div>
			<div class="bg-white border border-ink-200 px-3 py-2" style="border-radius: 2px">
				<div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">
					{{ __("Submitted") }}
				</div>
				<div class="text-base font-semibold text-warning-700 mt-0.5">
					{{ kpis.submitted }}
				</div>
			</div>
			<div class="bg-white border border-ink-200 px-3 py-2" style="border-radius: 2px">
				<div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">
					{{ __("Total planned") }}
				</div>
				<div class="text-base font-semibold text-ink-900 mt-0.5 tabular-nums">
					{{ fmtCompactINR(kpis.totalPlanned) }}
				</div>
				<div class="text-[10px] text-ink-500 mt-0.5">{{ __("approved BOQs") }}</div>
			</div>
			<div class="bg-white border border-ink-200 px-3 py-2" style="border-radius: 2px">
				<div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">
					{{ __("Variance") }}
				</div>
				<div
					class="text-base font-semibold mt-0.5 tabular-nums"
					:class="variancePill(kpis.variancePct)"
				>
					{{ kpis.variancePct > 0 ? "+" : "" }}{{ kpis.variancePct.toFixed(1) }}%
				</div>
				<div class="text-[10px] text-ink-500 mt-0.5">
					{{ __("{0} delta", [fmtCompactINR(kpis.variance)]) }}
				</div>
			</div>
		</div>

		<DeskList
			v-model="search"
			:rows="rows"
			:columns="columns"
			row-key="id"
			:search-placeholder="__('Search BOQ id or title…')"
			@row-click="onRowClick"
		>
			<template #filter-chips>
				<DeskSelect v-model="scopeFilter" class="!w-48">
					<option value="">{{ __("Estimates and BOQs") }}</option>
					<option value="estimate">{{ __("Estimates only") }}</option>
					<option value="project">{{ __("Project BOQs only") }}</option>
				</DeskSelect>

				<template v-if="scopeFilter !== 'estimate'">
					<div v-if="!projectFilter" class="w-48">
						<DeskLinkPicker
							v-model="projectFilter"
							doctype="Project"
							label-field="project_name"
							value-field="name"
							:search-fields="['project_name', 'custom_project_id', 'name']"
							:filters="companyFilter"
							:placeholder="__('Project: Any')"
						/>
					</div>
					<DeskFilterChip
						v-else
						:label="__('Project')"
						:value="projectName(projectFilter)"
						@remove="projectFilter = ''"
					/>
				</template>

				<DeskSelect v-if="!statusFilter" v-model="statusFilter" class="!w-36">
					<option value="">{{ __("Status: Any") }}</option>
					<option value="Draft">{{ __("Draft") }}</option>
					<option value="Submitted">{{ __("Submitted") }}</option>
					<option value="Approved">{{ __("Approved") }}</option>
					<option value="Superseded">{{ __("Replaced") }}</option>
				</DeskSelect>
				<DeskFilterChip
					v-else
					:label="__('Status')"
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
					<template v-if="row.isEstimate">
						<div class="text-ink-900">{{ row.customerName || "—" }}</div>
						<div class="text-ink-500">{{ __("Estimate · not yet won") }}</div>
					</template>
					<template v-else>
						<div class="text-ink-900">{{ row.projectName }}</div>
						<div class="font-mono text-ink-400">{{ row.projectCode }}</div>
					</template>
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
				<div class="text-sm text-ink-500">{{ __("No BOQs match these filters.") }}</div>
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
					<h2 class="text-sm font-semibold text-ink-900">{{ __("New BOQ") }}</h2>
					<button
						type="button"
						@click="showNew = false"
						class="ml-auto text-ink-400 hover:text-ink-900"
						:aria-label="__('Close')"
					>
						✕
					</button>
				</div>
				<div class="p-4 space-y-3">
					<!-- The one question that decides the rest of the form: an estimate has no
					     project yet; a project BOQ has one already. -->
					<DeskField :label="__('What is this for')" required>
						<div class="space-y-2">
							<button
								type="button"
								class="w-full text-left border px-3 py-2.5"
								style="border-radius: 6px"
								:class="
									newForm.for === 'estimate'
										? 'border-brand-600 bg-brand-50'
										: 'border-ink-200'
								"
								@click="newForm.for = 'estimate'"
							>
								<div class="text-sm font-medium text-ink-900">
									{{ __("Work we have not won yet") }}
								</div>
								<div class="text-xs text-ink-500">
									{{
										__(
											"Price it, bid it, and attach it to a project if it lands"
										)
									}}
								</div>
							</button>
							<button
								type="button"
								class="w-full text-left border px-3 py-2.5"
								style="border-radius: 6px"
								:class="
									newForm.for === 'project'
										? 'border-brand-600 bg-brand-50'
										: 'border-ink-200'
								"
								@click="newForm.for = 'project'"
							>
								<div class="text-sm font-medium text-ink-900">
									{{ __("An existing project") }}
								</div>
								<div class="text-xs text-ink-500">
									{{ __("A revision of that project's BOQ") }}
								</div>
							</button>
						</div>
					</DeskField>

					<DeskField v-if="newForm.for === 'project'" :label="__('Project')" required>
						<DeskLinkPicker
							v-model="newForm.projectId"
							doctype="Project"
							label-field="project_name"
							value-field="name"
							:search-fields="['project_name', 'custom_project_id', 'name']"
							:filters="companyFilter"
							:placeholder="__('Select a project')"
						/>
					</DeskField>

					<DeskField
						v-else
						:label="__('Customer')"
						:hint="
							__(
								'Who it is being priced for. Optional, but it is how you will find it later.'
							)
						"
					>
						<DeskLinkPicker
							v-model="newForm.customer"
							doctype="Customer"
							label-field="customer_name"
							value-field="name"
							:search-fields="['customer_name', 'name']"
							:placeholder="__('Pick a customer…')"
						/>
					</DeskField>

					<DeskField
						:label="__('Title')"
						:required="newForm.for === 'estimate'"
						:hint="
							newForm.for === 'estimate'
								? __(
										'What the job is — this is how the estimate is identified until it has a project.'
								  )
								: __('Leave blank to auto-name.')
						"
					>
						<DeskInput
							v-model="newForm.title"
							:placeholder="__('e.g. Whitefield villa — interior fit-out')"
						/>
					</DeskField>
				</div>
				<div class="px-4 py-2 border-t border-ink-200 flex items-center justify-end gap-2">
					<button
						type="button"
						@click="showNew = false"
						class="text-xs text-ink-600 hover:text-ink-900 px-2 py-1"
					>
						{{ __("Cancel") }}
					</button>
					<button
						type="button"
						@click="createBoq"
						class="desk-save-btn"
						:disabled="creating || !formValid"
					>
						{{ creating ? __("Creating…") : __("Create draft") }}
					</button>
				</div>
			</div>
		</div>
	</DeskPage>
</template>
