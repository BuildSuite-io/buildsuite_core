<script setup>
// Machinery Usage Log — the Machinery Utilisation report (Equipment workspace). Plant usage +
// cost by machine / project / task, with the prototype's filter strip (machine, project,
// period). Rows come resolved from the server (machine / project / task names + total cost) so
// nothing is looked up a second time on the client — see ISS-142.

import { computed, onMounted, reactive, ref } from "vue";
import { useRouter, RouterLink } from "vue-router";

import DeskInput from "@/components/desk/DeskInput.vue";
import DeskLink from "@/components/desk/DeskLink.vue";
import DeskList from "@/components/desk/DeskList.vue";
import DeskPage from "@/components/desk/DeskPage.vue";
import DeskSearchableSelect from "@/components/desk/DeskSearchableSelect.vue";
import ReportFilters from "@/components/reports/ReportFilters.vue";
import { getMachineryUsageReport } from "@/data/equipmentApi";
import { fmtDate, fmtINR } from "@/utils/format";

const router = useRouter();

const all = ref([]);
const loading = ref(true);
const error = ref("");

onMounted(async () => {
	try {
		all.value = (await getMachineryUsageReport()) || [];
	} catch (e) {
		error.value = e.message || "Failed to load the usage log.";
	} finally {
		loading.value = false;
	}
});

const search = ref("");
const BLANK = { machine: "", project: "", from: "", to: "" };
const f = reactive({ ...BLANK });
const anyFilter = computed(
	() => Object.keys(BLANK).some((k) => f[k] !== BLANK[k]) || !!search.value
);
function clearFilters() {
	Object.assign(f, BLANK);
	search.value = "";
}

// Machine + project pickers are built from the entries themselves, so no option offers a value
// with nothing behind it.
const machineOptions = computed(() => {
	const m = new Map();
	for (const u of all.value) if (u.machine) m.set(u.machine, u.machine_name || u.machine);
	return [...m.entries()]
		.map(([value, label]) => ({ value, label }))
		.sort((a, b) => a.label.localeCompare(b.label));
});
const projectOptions = computed(() => {
	const m = new Map();
	for (const u of all.value) if (u.project) m.set(u.project, u.project_name || u.project);
	return [...m.entries()]
		.map(([value, label]) => ({ value, label }))
		.sort((a, b) => a.label.localeCompare(b.label));
});

const rows = computed(() => {
	const t = search.value.trim().toLowerCase();
	return all.value.filter(
		(u) =>
			(!f.machine || u.machine === f.machine) &&
			(!f.project || u.project === f.project) &&
			(!f.from || (u.date || "") >= f.from) &&
			(!f.to || (u.date || "") <= f.to) &&
			(!t ||
				(u.machine_name || "").toLowerCase().includes(t) ||
				(u.project_name || "").toLowerCase().includes(t) ||
				(u.task_subject || "").toLowerCase().includes(t))
	);
});

const columns = [
	{ key: "date", label: "Date" },
	{ key: "machine", label: "Machine" },
	{ key: "project", label: "Project" },
	{ key: "task", label: "Task" },
	{ key: "quantity", label: "Qty", align: "right" },
	{ key: "total", label: "Total cost", align: "right" },
];

const breadcrumbs = [
	{ label: "BuildSuite Core", to: "/" },
	{ label: "Equipment", to: "/equipment" },
	{ label: "Machinery Usage" },
];

function onRowClick(row) {
	router.push(`/machinery-usage/${row.name}`);
}
</script>

<template>
	<DeskPage title="Machinery Usage Log" :breadcrumbs="breadcrumbs">
		<template #actions>
			<RouterLink to="/machinery-usage/new" class="desk-save-btn">+ Log usage</RouterLink>
		</template>

		<div v-if="error" class="text-sm text-danger-600 py-10 text-center">{{ error }}</div>
		<template v-else>
			<ReportFilters
				:active="anyFilter"
				:shown="rows.length"
				:total="all.length"
				noun="entries"
				@clear="clearFilters"
			>
				<label class="flex items-center gap-1.5">
					<span class="text-[11px] uppercase tracking-wider text-ink-500 font-medium"
						>Machine</span
					>
					<span class="w-48 inline-block">
						<DeskSearchableSelect
							v-model="f.machine"
							:options="machineOptions"
							allow-clear
							placeholder="All machines"
							search-placeholder="Search…"
						/>
					</span>
				</label>
				<label class="flex items-center gap-1.5">
					<span class="text-[11px] uppercase tracking-wider text-ink-500 font-medium"
						>Project</span
					>
					<span class="w-52 inline-block">
						<DeskSearchableSelect
							v-model="f.project"
							:options="projectOptions"
							allow-clear
							placeholder="All projects"
							search-placeholder="Search…"
						/>
					</span>
				</label>
				<label class="flex items-center gap-1.5">
					<span class="text-[11px] uppercase tracking-wider text-ink-500 font-medium"
						>Used</span
					>
					<DeskInput v-model="f.from" type="date" class="!w-36" />
					<span class="text-[11px] text-ink-400">to</span>
					<DeskInput v-model="f.to" type="date" class="!w-36" />
				</label>
			</ReportFilters>

			<DeskList
				v-model="search"
				:rows="rows"
				:columns="columns"
				row-key="name"
				search-placeholder="Search usage…"
				@row-click="onRowClick"
			>
				<template #cell-date="{ row }">
					<span class="text-ink-500">{{ fmtDate(row.date) }}</span>
				</template>
				<template #cell-machine="{ row }">
					<DeskLink :to="`/machinery/${row.machine}`" @click.stop>{{
						row.machine_name
					}}</DeskLink>
				</template>
				<template #cell-project="{ row }">
					<span class="text-ink-700">{{ row.project_name || "—" }}</span>
				</template>
				<template #cell-task="{ row }">
					<span class="text-ink-500">{{ row.task ? row.task_subject : "—" }}</span>
				</template>
				<template #cell-quantity="{ row }">
					<span class="tabular-nums">{{ row.quantity }} {{ row.unit }}</span>
				</template>
				<template #cell-total="{ row }">
					<span class="tabular-nums text-ink-900 font-medium">{{
						fmtINR(row.total)
					}}</span>
				</template>

				<template #empty>
					<div class="text-sm text-ink-500">
						{{ loading ? "Loading usage log…" : "No usage logged yet." }}
						<RouterLink v-if="!loading" to="/machinery-usage/new" class="desk-link"
							>Log usage →</RouterLink
						>
					</div>
				</template>
			</DeskList>
		</template>
	</DeskPage>
</template>
