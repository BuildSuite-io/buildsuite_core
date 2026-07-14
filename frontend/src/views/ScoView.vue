<script setup>

import { computed, ref } from "vue";
import { useRouter } from "vue-router";
import { useDocTypeList } from "@/composables/useDocTypeList";
import StatusBadge from "@/components/StatusBadge.vue";
import UserAvatar from "@/components/UserAvatar.vue";
import DeskPage from "@/components/desk/DeskPage.vue";
import DeskList from "@/components/desk/DeskList.vue";
import DeskSelect from "@/components/desk/DeskSelect.vue";
import DeskFilterChip from "@/components/desk/DeskFilterChip.vue";
import DeskLink from "@/components/desk/DeskLink.vue";
import { fmtINR, fmtCompactINR, fmtDate, impactClass, impactSign } from "@/utils/format";

// Cost-recovery value → pill label + colour. Add a row here to support a new type.
const COST_RECOVERY = {
	"Recoverable from Client": { label: "Client", class: "bg-success-50 text-success-700" },
	Internal: { label: "Internal", class: "bg-ink-100 text-ink-600" },
};

const router = useRouter();

const search = ref("");
const statusFilter = ref("");

const scosRes = useDocTypeList("Scope Change Order", {
	fields: [
		"name",
		"title",
		"project",
		"sco_type",
		"cost_impact",
		"cost_recovery",
		"status",
		"raised_by",
		"raised_date",
	],
	orderBy: "creation desc",
	pageLength: 0,
	cache: "buildsuite-sco-list",
	transform: (data) =>
		data.map((s) => ({
			id: s.name,
			title: s.title,
			project: s.project,
			type: s.sco_type,
			impact: s.cost_impact || 0,
			costRecovery: s.cost_recovery,
			status: s.status,
			raisedBy: s.raised_by,
			raisedDate: s.raised_date,
		})),
});

const rows = computed(() => scosRes.data || []);

const items = computed(() => {
	const term = search.value.trim().toLowerCase();
	return rows.value.filter((s) => {
		if (statusFilter.value && s.status !== statusFilter.value) return false;
		if (
			term &&
			!(s.title || "").toLowerCase().includes(term) &&
			!(s.id || "").toLowerCase().includes(term)
		)
			return false;
		return true;
	});
});

const pendingCount = computed(
	() => rows.value.filter((s) => s.status === "Pending Approval").length
);
const totalImpact = computed(() => rows.value.reduce((a, s) => a + (s.impact || 0), 0));
const recoverableTotal = computed(() =>
	rows.value
		.filter((s) => s.costRecovery === "Recoverable from Client")
		.reduce((a, s) => a + (s.impact || 0), 0)
);

function onRowClick(row) {
	router.push(`/sco/${row.id}`);
}
function onNew() {
	router.push("/sco/new");
}

const columns = [
	{ key: "id", label: "ID" },
	{ key: "title", label: "Title" },
	{ key: "project", label: "Project" },
	{ key: "type", label: "Type" },
	{ key: "impact", label: "Impact", align: "right" },
	{ key: "costRecovery", label: "Cost Recovery" },
	{ key: "status", label: "Status" },
	{ key: "raisedBy", label: "Raised by" },
	{ key: "raisedDate", label: "Date" },
];

const breadcrumbs = [{ label: "BuildSuite Core", to: "/" }, { label: "Scope Change" }];
</script>

<template>
	<DeskPage title="Scope Change Order" :breadcrumbs="breadcrumbs">
		<template #actions>
			<button type="button" class="desk-save-btn" @click="onNew">+ Raise SCO</button>
		</template>

		<!-- KPI strip — Desk-tight -->
		<div class="grid grid-cols-2 md:grid-cols-4 gap-2 mb-4">
			<div class="bg-white border border-ink-200 px-3 py-2" style="border-radius: 2px">
				<div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">
					Total SCOs
				</div>
				<div class="text-base font-semibold text-ink-900 mt-0.5">
					{{ rows.length }}
				</div>
			</div>
			<div class="bg-white border border-ink-200 px-3 py-2" style="border-radius: 2px">
				<div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">
					Pending approval
				</div>
				<div class="text-base font-semibold text-warning-700 mt-0.5">
					{{ pendingCount }}
				</div>
			</div>
			<div class="bg-white border border-ink-200 px-3 py-2" style="border-radius: 2px">
				<div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">
					Net cost impact
				</div>
				<div
					class="text-base font-semibold mt-0.5 tabular-nums"
					:class="impactClass(totalImpact)"
				>
					{{ impactSign(totalImpact) }}{{ fmtCompactINR(Math.abs(totalImpact)) }}
				</div>
			</div>
			<div class="bg-white border border-ink-200 px-3 py-2" style="border-radius: 2px">
				<div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">
					Client recoverable
				</div>
				<div class="text-base font-semibold text-success-700 mt-0.5 tabular-nums">
					{{ fmtCompactINR(recoverableTotal) }}
				</div>
			</div>
		</div>

		<DeskList
			v-model="search"
			:rows="items"
			:columns="columns"
			row-key="id"
			search-placeholder="Search SCO id or title…"
			@row-click="onRowClick"
		>
			<template #filter-chips>
				<DeskSelect v-if="!statusFilter" v-model="statusFilter" class="!w-44">
					<option value="">Status: Any</option>
					<option>Pending Approval</option>
					<option>Approved</option>
					<option>Rejected</option>
				</DeskSelect>
				<DeskFilterChip
					v-else
					label="Status"
					:value="statusFilter"
					@remove="statusFilter = ''"
				/>
			</template>

			<template #cell-id="{ row }">
				<DeskLink :to="`/sco/${row.id}`" class="font-mono text-xs" @click.stop>{{
					row.id
				}}</DeskLink>
			</template>
			<template #cell-title="{ row }">
				<span class="text-ink-900 font-medium text-sm">{{ row.title }}</span>
			</template>
			<template #cell-project="{ row }">
				<span class="text-ink-700 text-xs">{{ row.project }}</span>
			</template>
			<template #cell-type="{ row }">
				<span class="text-ink-700 text-xs">{{ row.type }}</span>
			</template>
			<template #cell-impact="{ row }">
				<span
					class="tabular-nums"
					:class="impactClass(row.impact)"
				>
					{{ impactSign(row.impact) }}{{ fmtINR(Math.abs(row.impact)) }}
				</span>
			</template>
			<template #cell-costRecovery="{ row }">
				<span
					v-if="COST_RECOVERY[row.costRecovery]"
					class="text-[10px] px-1.5 py-0.5 font-medium rounded-full"
					:class="COST_RECOVERY[row.costRecovery].class"
					>{{ COST_RECOVERY[row.costRecovery].label }}</span
				>
				<span v-else class="text-ink-300">—</span>
			</template>
			<template #cell-status="{ row }">
				<StatusBadge :status="row.status" />
			</template>
			<template #cell-raisedBy="{ row }">
				<UserAvatar v-if="row.raisedBy" :user-id="row.raisedBy" size="xs" />
				<span v-else class="text-ink-300">—</span>
			</template>
			<template #cell-raisedDate="{ row }">
				<span class="text-xs text-ink-500">{{ row.raisedDate ? fmtDate(row.raisedDate) : "—" }}</span>
			</template>

			<template #empty>
				<div class="text-sm text-ink-500">
					{{ scosRes.loading ? "Loading…" : "No scope change orders yet." }}
				</div>
			</template>
		</DeskList>
	</DeskPage>
</template>
