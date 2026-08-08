<script setup>
// Bulk Select Employees. Workers already on the sheet open pre-checked; Add to
// Table only appends the rest.

import { computed, ref, watch } from "vue";
import { useDataStore } from "@/stores";
import { createDataAdapter } from "@/data/adapters";
import { getRoster } from "@/data/fieldAttendanceApi";
import { useFieldEmployeeOptions } from "@/composables/useFieldEmployeeOptions";
import { showToast } from "@/utils/appToast";
import { fmtDate } from "@/utils/format";
import DeskSearchableSelect from "@/components/desk/DeskSearchableSelect.vue";

const props = defineProps({
	open: { type: Boolean, default: false },
	project: { type: String, default: "" },
	date: { type: String, default: "" },
	projectLabel: { type: String, default: "" },
	// Workers already on the sheet — open pre-checked.
	existing: { type: Array, default: () => [] },
});
const emit = defineEmits(["close", "add"]);

const adapter = createDataAdapter(useDataStore());
const { workerOptions } = useFieldEmployeeOptions();

const search = ref("");
const bulkCrew = ref("");
const checked = ref(new Set());
const allocated = ref(new Set());
const projectRoster = ref([]);
// Names for ids from a roster/crew that aren't in workerOptions — otherwise
// they'd count as selected, stay invisible, and vanish on Add.
const extraNames = ref(new Map());

const crewRes = adapter.list("Crew", {
	fields: ["name", "crew_name"],
	orderBy: "crew_name asc",
	pageLength: 0,
	cache: "buildsuite-crew-options",
});
const crewOpts = computed(() =>
	(crewRes?.data || []).map((c) => ({ value: c.name, label: c.crew_name || c.name }))
);

// Workers allocated to this project float to the top; they're the ones the user
// is nearly always after.
const bulkList = computed(() => {
	const t = search.value.trim().toLowerCase();
	// Roster/crew picks outside the option list still get a row, so the footer
	// count always matches what you can see and untick.
	const known = new Set(workerOptions.value.map((o) => o.value));
	const extras = [...extraNames.value]
		.filter(([id]) => !known.has(id))
		.map(([id, label]) => ({ value: id, label, hint: id }));
	const list = [...workerOptions.value, ...extras].filter(
		(o) => !t || `${o.label} ${o.hint || ""}`.toLowerCase().includes(t)
	);
	return list.slice().sort((a, b) => {
		const d = (allocated.value.has(b.value) ? 1 : 0) - (allocated.value.has(a.value) ? 1 : 0);
		return d || (a.label || "").localeCompare(b.label || "");
	});
});

function isAllocated(id) {
	return allocated.value.has(id);
}

// Reset on open and preload the allocated set for the chips and the count.
watch(
	() => props.open,
	async (isOpen) => {
		if (!isOpen) return;
		search.value = "";
		bulkCrew.value = "";
		checked.value = new Set(props.existing);
		extraNames.value = new Map();
		projectRoster.value = [];
		allocated.value = new Set();
		if (!props.project) return;
		try {
			const rows = await getRoster(props.project);
			projectRoster.value = rows;
			allocated.value = new Set(rows.map((r) => r.employee));
		} catch {
			// A failed preload only costs the chips — leave the modal usable.
			projectRoster.value = [];
			allocated.value = new Set();
		}
	}
);

function toggleCheck(id) {
	const s = new Set(checked.value);
	s.has(id) ? s.delete(id) : s.add(id);
	checked.value = s;
}

function addWorkerRows(workers) {
	const known = new Set(workerOptions.value.map((o) => o.value));
	const names = new Map(extraNames.value);
	const s = new Set(checked.value);
	for (const w of workers) {
		if (!w.employee) continue;
		s.add(w.employee);
		if (!known.has(w.employee)) names.set(w.employee, w.employee_name || w.employee);
	}
	extraNames.value = names;
	checked.value = s;
}

function selectProjectRoster() {
	addWorkerRows(projectRoster.value);
}

// Union over every worker, not the search-filtered subset — otherwise Select All
// after a search silently drops the rest.
function selectAll() {
	const s = new Set(checked.value);
	workerOptions.value.forEach((o) => s.add(o.value));
	checked.value = s;
}

function unselectAll() {
	checked.value = new Set();
}

// Everything checked, including ids that aren't in workerOptions.
const selectedWorkers = computed(() =>
	[...checked.value].map((id) => {
		const opt = workerOptions.value.find((o) => o.value === id);
		return { employee: id, employee_name: opt?.label || extraNames.value.get(id) || id };
	})
);

async function selectCrew() {
	if (!bulkCrew.value) return;
	try {
		// frappe.client.get returns child tables; reload() resolves once loaded.
		const res = adapter.read("Crew", bulkCrew.value);
		await res?.reload?.();
		const members = res?.doc?.members || [];
		if (!members.length) {
			showToast("That crew has no members.", "info");
			return;
		}
		addWorkerRows(
			members
				.filter((m) => m.field_employee)
				.map((m) => ({ employee: m.field_employee, employee_name: m.employee_name }))
		);
	} catch (err) {
		showToast(err.message || "Could not load the crew.", "error");
	}
}

function addToTable() {
	const already = new Set(props.existing);
	emit(
		"add",
		selectedWorkers.value.filter((w) => !already.has(w.employee))
	);
	emit("close");
}
</script>

<template>
	<Teleport to="body">
		<div
			v-if="open"
			class="fixed inset-0 bg-ink-900/40 z-[70] flex items-center justify-center p-6"
			@click.self="emit('close')"
		>
			<div
				class="bg-white border border-ink-200 w-full max-w-2xl shadow-fp-lg flex flex-col"
				style="border-radius: 12px; max-height: calc(100vh - 3rem)"
				@click.stop
			>
				<header
					class="px-5 py-3 border-b border-ink-200 flex items-center justify-between"
				>
					<h2 class="text-sm font-semibold text-ink-900">Bulk Select Employees</h2>
					<button
						type="button"
						class="text-ink-500 hover:text-ink-900 text-lg leading-none"
						@click="emit('close')"
					>
						×
					</button>
				</header>

				<div class="p-5 min-h-0 flex flex-col">
					<div class="grid grid-cols-2 gap-3 mb-3 text-xs">
						<div>
							<div class="text-[10px] uppercase tracking-wider text-ink-500 mb-1">
								Project
							</div>
							<div class="text-ink-800">{{ projectLabel || project || "—" }}</div>
						</div>
						<div>
							<div class="text-[10px] uppercase tracking-wider text-ink-500 mb-1">
								Date
							</div>
							<div class="text-ink-800">{{ fmtDate(date) || "—" }}</div>
						</div>
					</div>

					<input
						v-model="search"
						type="text"
						class="desk-input mb-3"
						placeholder="Search employee…"
					/>

					<div class="flex flex-wrap items-center gap-2 mb-3">
						<!-- The project roster is the usual answer, so it leads. -->
						<button
							type="button"
							class="text-xs px-2.5 py-1 border border-brand-200 bg-brand-50 hover:bg-brand-100 text-brand-700 rounded-md font-medium disabled:opacity-50 disabled:cursor-not-allowed"
							:disabled="!projectRoster.length"
							@click="selectProjectRoster"
						>
							Project roster ({{ projectRoster.length }})
						</button>
						<button
							type="button"
							class="text-xs px-2.5 py-1 border border-ink-200 bg-white hover:bg-ink-50 rounded-md"
							@click="selectAll"
						>
							Select All
						</button>
						<div class="flex items-center gap-1">
							<div class="w-48">
								<DeskSearchableSelect
									v-model="bulkCrew"
									:options="crewOpts"
									placeholder="Select crew…"
									search-placeholder="Search crews…"
									allow-clear
								/>
							</div>
							<button
								type="button"
								class="text-xs px-2.5 py-1 border border-ink-200 bg-white hover:bg-ink-50 rounded-md"
								:disabled="!bulkCrew"
								@click="selectCrew"
							>
								Select Crew
							</button>
						</div>
						<button
							type="button"
							class="text-xs px-2.5 py-1 border border-ink-200 bg-white hover:bg-ink-50 rounded-md"
							@click="unselectAll"
						>
							Unselect All
						</button>
					</div>

					<!-- Only the list scrolls. A site with hundreds of workers would
					     otherwise stretch the dialog to the full viewport and push the
					     search box and quick-selects out of reach. -->
					<div
						class="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-1 overflow-y-auto min-h-0"
						style="max-height: 340px"
					>
						<label
							v-for="e in bulkList"
							:key="e.value"
							class="flex items-center gap-2 py-1.5 cursor-pointer"
						>
							<input
								type="checkbox"
								:checked="checked.has(e.value)"
								@change="toggleCheck(e.value)"
							/>
							<span class="min-w-0">
								<span class="flex items-center gap-1.5">
									<span class="text-sm text-ink-900 truncate">{{
										e.label
									}}</span>
									<!-- allocated to this project (these sort first) -->
									<span
										v-if="isAllocated(e.value)"
										class="text-[10px] px-1.5 py-0.5 bg-brand-50 text-brand-700 rounded-full whitespace-nowrap"
									>
										Allocated
									</span>
								</span>
								<span class="block text-[11px] text-ink-500">{{ e.hint }}</span>
							</span>
						</label>
						<div v-if="!bulkList.length" class="text-xs text-ink-400 italic py-3">
							No workers match.
						</div>
					</div>
				</div>

				<footer
					class="px-5 py-3 border-t border-ink-200 flex items-center justify-between gap-2"
				>
					<span class="text-[11px] text-ink-500">{{ checked.size }} selected</span>
					<button
						type="button"
						class="text-xs px-3 py-1.5 bg-ink-900 text-white hover:bg-ink-800 rounded-md font-medium"
						@click="addToTable"
					>
						Add to Table
					</button>
				</footer>
			</div>
		</div>
	</Teleport>
</template>
