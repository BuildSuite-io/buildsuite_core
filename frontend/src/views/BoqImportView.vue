<script setup>
// S430 — import lines into a Draft BOQ from Excel (.xlsx), CSV, or rows pasted
// from Excel.
//
// Three steps on one page: choose the file, check the columns, review. Nothing
// is written until "Import". Anything the import would CREATE (a unit the app
// does not know, a new group) is listed first and waits for the user: an
// unknown unit can be created, mapped to an existing UOM, or its rows skipped;
// a common spelling ("MT", "No.") is offered as a suggestion, never assumed.
//
// The reading + rules live in utils/boqImport.js (pure); this page only shows
// them and calls the whitelisted importBoqRows wrapper to persist.
import { ref, computed, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useDataStore } from "@/stores";
import { createDataAdapter } from "@/data/adapters";
import { useDocTypeList } from "@/composables/useDocTypeList";
import { usePermissions } from "@/composables/usePermissions";
import { showToast } from "@/utils/appToast";
import { parseFrappeError } from "@/utils/frappeError";
import { importBoqRows } from "@/utils/boqApi";
import DeskPage from "@/components/desk/DeskPage.vue";
import DeskLink from "@/components/desk/DeskLink.vue";
import DeskSelect from "@/components/desk/DeskSelect.vue";
import DeskLinkPicker from "@/components/desk/DeskLinkPicker.vue";
import { fmtINR } from "@/utils/format";
import { __ } from "@/utils/translate";
import {
	readSpreadsheet,
	parseDelimited,
	detectColumns,
	planImport,
	defaultDecisions,
	buildPayload,
	templateCsv,
	colLetter,
	FIELDS,
} from "@/utils/boqImport";

const props = defineProps({ id: { type: String, default: "" } });
const route = useRoute();
const router = useRouter();
const boqId = computed(() => props.id || route.params.id);
const adapter = createDataAdapter(useDataStore());
const { canEdit } = usePermissions();

// ---- the BOQ header (title + status gate)
const boqResource = adapter.read("BOQ", boqId.value, {
	fields: ["name", "title", "status", "project"],
});
const boq = computed(() => {
	const d = boqResource?.doc;
	if (!d) return null;
	return { id: d.name, title: d.title, status: d.status, projectId: d.project };
});
const editable = computed(() => boq.value?.status === "Draft" && canEdit("boq"));

// ---- live data for the import context (ctx) ----
// Known units: every ERPNext UOM master name — matchUnit suggests/validates against these.
const unitsRes = useDocTypeList("UOM", {
	fields: ["name"],
	pageLength: 5000,
	cache: "buildsuite-uom-all",
});
// This BOQ's existing groups (merge by name) + item codes (dedupe).
const groupsRes = useDocTypeList("BOQ Group", {
	filters: [["boq", "=", boqId.value]],
	fields: ["name", "code", "group_name"],
	pageLength: 0,
});
const codesRes = useDocTypeList("BOQ Item", {
	filters: [["boq", "=", boqId.value]],
	fields: ["code"],
	pageLength: 0,
});

const ctx = computed(() => ({
	units: (unitsRes.data || []).map((u) => u.name),
	groups: (groupsRes.data || []).map((g) => ({
		id: g.name,
		code: g.code,
		name: g.group_name,
	})),
	codes: (codesRes.data || []).map((i) => i.code).filter(Boolean),
	defaultGroup: "General",
}));

// ---- step 1: the file
const fileName = ref("");
const sheets = ref([]);
const sheetIndex = ref(0);
const error = ref("");
const loading = ref(false);
const pasteOpen = ref(false);
const pasteText = ref("");
const dragging = ref(false);

const rows = computed(() => sheets.value[sheetIndex.value]?.rows || []);
const headerRow = ref(-1);
const mapping = ref({});

function useRows(list, name) {
	if (list.length > 5000) {
		error.value = __("That file has more than 5,000 rows. Split it and import it in parts.");
		return;
	}
	sheets.value = list.length ? [{ name, rows: list }] : [];
	sheetIndex.value = 0;
	if (!list.length) error.value = __("No rows were found.");
}
async function onFile(file) {
	if (!file) return;
	error.value = "";
	loading.value = true;
	try {
		const book = await readSpreadsheet(await file.arrayBuffer(), file.name);
		if (book.sheets.reduce((a, sh) => a + sh.rows.length, 0) > 5000)
			throw new Error(
				__("That file has more than 5,000 rows. Split it and import it in parts.")
			);
		sheets.value = book.sheets;
		// Start on the first sheet that has something a BOQ would have.
		const firstUseful = book.sheets.findIndex((sh) => detectColumns(sh.rows).headerRow >= 0);
		sheetIndex.value = firstUseful >= 0 ? firstUseful : 0;
		fileName.value = file.name;
	} catch (e) {
		error.value = e.message || __("The file could not be read.");
		sheets.value = [];
	} finally {
		loading.value = false;
	}
}
function onPick(e) {
	onFile(e.target.files?.[0]);
	e.target.value = "";
}
function onDrop(e) {
	dragging.value = false;
	onFile(e.dataTransfer?.files?.[0]);
}
function usePaste() {
	error.value = "";
	useRows(parseDelimited(pasteText.value), __("Pasted rows"));
	fileName.value = __("Pasted rows");
	pasteOpen.value = false;
}
function startOver() {
	sheets.value = [];
	fileName.value = "";
	error.value = "";
	pasteText.value = "";
}
function downloadTemplate() {
	const url = URL.createObjectURL(new Blob([templateCsv()], { type: "text/csv" }));
	const a = document.createElement("a");
	a.href = url;
	a.download = "boq-import-template.csv";
	a.click();
	setTimeout(() => URL.revokeObjectURL(url), 1000);
}

// A new sheet means new columns.
watch(rows, (r) => {
	const det = detectColumns(r);
	headerRow.value = det.headerRow;
	mapping.value = { ...det.mapping };
});

// ---- step 2: the columns
const width = computed(() => rows.value.reduce((a, r) => Math.max(a, r.length), 0));
const columnOptions = computed(() =>
	Array.from({ length: width.value }, (_, i) => {
		const head =
			headerRow.value >= 0 ? String(rows.value[headerRow.value]?.[i] ?? "").trim() : "";
		return { value: i, label: colLetter(i) + (head ? " · " + head : "") };
	})
);
const headerChoices = computed(() =>
	rows.value.slice(0, 15).map((r, i) => ({
		value: i,
		label:
			__("Row {0}", [i + 1]) +
			": " +
			(r
				.filter((v) => String(v ?? "").trim() !== "")
				.slice(0, 4)
				.join(" · ") || __("(blank)")),
	}))
);
function setMap(key, v) {
	mapping.value = { ...mapping.value, [key]: v === "" ? undefined : Number(v) };
}
function setHeaderRow(v) {
	headerRow.value = Number(v);
}

// ---- step 3: review
const plan = computed(() =>
	mapping.value.description == null
		? null
		: planImport(rows.value, { headerRow: headerRow.value, mapping: mapping.value }, ctx.value)
);
const decisions = ref({ units: {}, missingUnit: { action: "set", value: "Nos" } });
// Fresh defaults whenever the set of questions changes; answers already given are kept.
watch(
	() => plan.value?.units.map((u) => u.raw.toLowerCase()).join("|"),
	() => {
		if (!plan.value) return;
		const d = defaultDecisions(plan.value);
		for (const k of Object.keys(d.units))
			if (decisions.value.units[k]) d.units[k] = decisions.value.units[k];
		decisions.value = { units: d.units, missingUnit: decisions.value.missingUnit };
	},
	{ immediate: true }
);
const payload = computed(() => (plan.value ? buildPayload(plan.value, decisions.value) : null));
const newGroups = computed(() => (payload.value?.groups || []).filter((g) => !g.existingId));
const total = computed(() =>
	(payload.value?.items || []).reduce((a, i) => a + i.plannedQty * i.rate, 0)
);
const needsAnswers = computed(
	() => !!plan.value && (plan.value.units.length > 0 || plan.value.missingUnit > 0)
);

function setUnit(raw, patch) {
	const k = raw.toLowerCase();
	decisions.value = {
		...decisions.value,
		units: { ...decisions.value.units, [k]: { ...decisions.value.units[k], ...patch } },
	};
}
function setMissing(patch) {
	decisions.value = {
		...decisions.value,
		missingUnit: { ...decisions.value.missingUnit, ...patch },
	};
}

/** How a row's unit will come in, given the answers so far. */
function resolvedUnit(it) {
	if (it.unit.status === "exact") return { text: it.unit.value, tone: "ok" };
	if (it.unit.status === "missing") {
		return decisions.value.missingUnit?.action === "set"
			? {
					text: __("{0} (no unit in file)", [decisions.value.missingUnit.value]),
					tone: "set",
			  }
			: { text: __("Skipped: no unit"), tone: "skip" };
	}
	const d = decisions.value.units[it.unit.raw.toLowerCase()];
	if (d?.action === "create") return { text: __("{0} (new unit)", [it.unit.raw]), tone: "set" };
	if (d?.action === "map")
		return { text: __('{0} (file says "{1}")', [d.value, it.unit.raw]), tone: "set" };
	return { text: __('Skipped: "{0}"', [it.unit.raw]), tone: "skip" };
}
const showNotesOnly = ref(false);
const previewRows = computed(() => {
	const list = (plan.value?.items || []).filter(
		(it) => !showNotesOnly.value || it.notes.length || it.unit.status !== "exact"
	);
	return list.slice(0, 300);
});
// The preview reads like the estimate it will become: one collapsible section per group, in file
// order, all open to start. The subtotal counts only the rows that will come in (a row whose unit
// is skipped is left out of it).
const previewGroups = computed(() =>
	(plan.value?.groups || [])
		.map((g) => {
			const its = previewRows.value.filter((it) => it.groupKey === g.key);
			return {
				...g,
				rows: its,
				amount: its
					.filter((it) => resolvedUnit(it).tone !== "skip")
					.reduce((a, it) => a + (Number(it.amount) || 0), 0),
				noted: its.filter((it) => it.notes.length || it.unit.status !== "exact").length,
			};
		})
		.filter((g) => g.rows.length)
);
const collapsed = ref([]);
const isOpen = (key) => !collapsed.value.includes(key);
function toggleGroup(key) {
	collapsed.value = isOpen(key)
		? [...collapsed.value, key]
		: collapsed.value.filter((k) => k !== key);
}
const allOpen = computed(() => previewGroups.value.every((g) => isOpen(g.key)));
function setAll(open) {
	collapsed.value = open ? [] : previewGroups.value.map((g) => g.key);
}
const notedCount = computed(
	() =>
		(plan.value?.items || []).filter((it) => it.notes.length || it.unit.status !== "exact")
			.length
);

const importing = ref(false);
async function importNow() {
	if (!payload.value?.items.length || importing.value) return;
	importing.value = true;
	try {
		const res = await importBoqRows(boqId.value, payload.value);
		showToast(__("Imported {0} items into {1} groups", [res.items, res.groups]));
		router.push(`/boq/${boqId.value}`);
	} catch (err) {
		showToast(parseFrappeError(err).summary ?? __("Failed to import"), "error");
	} finally {
		importing.value = false;
	}
}

const breadcrumbs = computed(() => [
	{ label: "BuildSuite Core", to: "/" },
	{ label: __("BOQ"), to: "/boq" },
	{ label: boq.value?.title || boqId.value, to: `/boq/${boqId.value}` },
	{ label: __("Import") },
]);
</script>

<template>
	<DeskPage
		:title="boq ? __('Import into {0}', [boq.title]) : __('BOQ not found')"
		:breadcrumbs="breadcrumbs"
	>
		<template v-if="boq && editable && payload?.items.length" #actions>
			<button
				type="button"
				class="text-xs px-2 py-1 border border-ink-200 bg-white hover:bg-ink-50"
				style="border-radius: 2px"
				@click="router.push(`/boq/${boqId}`)"
			>
				{{ __("Cancel") }}
			</button>
			<button type="button" class="desk-save-btn" :disabled="importing" @click="importNow">
				{{
					payload.items.length === 1
						? __("Import 1 line")
						: __("Import {0} lines", [payload.items.length])
				}}
			</button>
		</template>

		<div v-if="!boq" class="text-sm text-ink-600">
			{{ __("No BOQ with that id.") }}
			<DeskLink to="/boq">{{ __("Back to the BOQ list") }}</DeskLink>
		</div>
		<div
			v-else-if="!editable"
			class="bg-warning-50 border border-warning-200 px-4 py-3 text-sm text-ink-900"
			style="border-radius: 6px"
		>
			{{ __("Only a Draft BOQ can take imported lines. This one is {0}.", [boq.status]) }}
			<DeskLink :to="`/boq/${boqId}`">{{ __("Back to the BOQ") }}</DeskLink
			>, and make a revision to change it.
		</div>

		<template v-else>
			<!-- Step 1: the file -->
			<section v-if="!sheets.length" class="max-w-3xl">
				<label
					class="block border-2 border-dashed px-6 py-10 text-center cursor-pointer transition-colors"
					:class="
						dragging
							? 'border-brand-500 bg-brand-50'
							: 'border-ink-200 hover:border-brand-400'
					"
					style="border-radius: 10px"
					@dragover.prevent="dragging = true"
					@dragleave.prevent="dragging = false"
					@drop.prevent="onDrop"
				>
					<input
						type="file"
						class="hidden"
						accept=".xlsx,.xlsm,.csv,.tsv,.txt"
						@change="onPick"
					/>
					<div class="text-sm font-medium text-ink-900">
						{{
							loading
								? __("Reading the file…")
								: __("Choose an Excel file, or drop it here")
						}}
					</div>
					<div class="text-xs text-ink-500 mt-1">
						{{
							__(
								".xlsx or .csv. The first sheet with a Description column is used; you can switch sheets after."
							)
						}}
					</div>
				</label>
				<div class="flex flex-wrap items-center gap-4 mt-3 text-xs">
					<button
						type="button"
						class="text-brand-700 hover:underline"
						@click="pasteOpen = !pasteOpen"
					>
						{{ __("Paste rows from Excel instead") }}
					</button>
					<button
						type="button"
						class="text-brand-700 hover:underline"
						@click="downloadTemplate"
					>
						{{ __("Download a template") }}
					</button>
					<span class="text-ink-500">
						{{
							__(
								"Columns it understands: Group, Code, Description, Unit, Quantity, Rate, Amount, Cost head."
							)
						}}
					</span>
				</div>
				<div v-if="pasteOpen" class="mt-3">
					<textarea
						v-model="pasteText"
						rows="8"
						class="desk-input font-mono text-xs"
						:placeholder="
							__('Copy the cells in Excel, headings included, and paste them here.')
						"
					></textarea>
					<button
						type="button"
						class="desk-save-btn mt-2"
						:disabled="!pasteText.trim()"
						@click="usePaste"
					>
						{{ __("Use these rows") }}
					</button>
				</div>
				<div
					v-if="error"
					class="mt-3 bg-danger-50 border border-danger-200 px-3 py-2 text-xs text-ink-900"
					style="border-radius: 6px"
				>
					{{ error }}
				</div>
			</section>

			<template v-else>
				<!-- Step 2: the columns -->
				<section class="border border-ink-200 mb-4" style="border-radius: 8px">
					<header
						class="px-4 py-2.5 bg-ink-50 border-b border-ink-100 flex flex-wrap items-center justify-between gap-2"
					>
						<div class="text-sm text-ink-900">
							<span class="font-semibold">{{ fileName }}</span>
							<span class="text-ink-500">
								· {{ __("{0} rows", [rows.length]) }}</span
							>
						</div>
						<button
							type="button"
							class="text-xs text-brand-700 hover:underline"
							@click="startOver"
						>
							{{ __("Choose another file") }}
						</button>
					</header>
					<div class="p-4 space-y-3">
						<div class="flex flex-wrap gap-3">
							<label v-if="sheets.length > 1" class="block">
								<span class="block text-[11px] text-ink-500 mb-1">{{
									__("Sheet")
								}}</span>
								<DeskSelect v-model.number="sheetIndex" class="w-56">
									<option v-for="(sh, i) in sheets" :key="i" :value="i">
										{{ sh.name }} ({{ __("{0} rows", [sh.rows.length]) }})
									</option>
								</DeskSelect>
							</label>
							<label class="block min-w-0 flex-1">
								<span class="block text-[11px] text-ink-500 mb-1">{{
									__("Column headings are on")
								}}</span>
								<DeskSelect
									:model-value="headerRow"
									@update:model-value="setHeaderRow"
								>
									<option :value="-1">
										{{ __("No heading row: map the columns by letter") }}
									</option>
									<option
										v-for="h in headerChoices"
										:key="h.value"
										:value="h.value"
									>
										{{ h.label }}
									</option>
								</DeskSelect>
							</label>
						</div>
						<div class="grid grid-cols-2 md:grid-cols-4 gap-3">
							<label v-for="f in FIELDS" :key="f.key" class="block">
								<span class="block text-[11px] text-ink-500 mb-1">
									{{ __(f.label)
									}}<span v-if="f.key === 'description'" class="text-danger-700">
										*</span
									>
								</span>
								<DeskSelect
									:model-value="mapping[f.key] ?? ''"
									@update:model-value="(v) => setMap(f.key, v)"
								>
									<option value="">{{ __("— Not in the file —") }}</option>
									<option
										v-for="o in columnOptions"
										:key="o.value"
										:value="o.value"
									>
										{{ o.label }}
									</option>
								</DeskSelect>
							</label>
						</div>
						<p class="text-[11px] text-ink-500">
							{{
								__(
									'Without a Group column, a row with only a description is read as a group heading and the rows below it go into that group. Rows starting with "Total" or "Sub total" are left out.'
								)
							}}
						</p>
					</div>
				</section>

				<div
					v-if="!plan"
					class="bg-warning-50 border border-warning-200 px-3 py-2 text-xs text-ink-900 mb-4"
					style="border-radius: 6px"
				>
					{{
						__(
							"Pick the column that holds the description to see what will be imported."
						)
					}}
				</div>

				<template v-else>
					<!-- What the import will do -->
					<div class="grid grid-cols-2 md:grid-cols-4 gap-2 mb-4">
						<div
							class="bg-white border border-ink-200 px-3 py-2"
							style="border-radius: 6px"
						>
							<div
								class="text-[10px] uppercase tracking-wider text-ink-500 font-medium"
							>
								{{ __("Lines to import") }}
							</div>
							<div class="text-lg font-semibold text-ink-900 tabular-nums">
								{{ payload.items.length }}
							</div>
							<div class="text-[10px] text-ink-500">
								{{ __("worth {0}", [fmtINR(Math.round(total))]) }}
							</div>
						</div>
						<div
							class="bg-white border border-ink-200 px-3 py-2"
							style="border-radius: 6px"
						>
							<div
								class="text-[10px] uppercase tracking-wider text-ink-500 font-medium"
							>
								{{ __("Groups") }}
							</div>
							<div class="text-lg font-semibold text-ink-900 tabular-nums">
								{{ payload.groups.length }}
							</div>
							<div class="text-[10px] text-ink-500">
								{{
									__("{0} new, {1} already in this BOQ", [
										newGroups.length,
										payload.groups.length - newGroups.length,
									])
								}}
							</div>
						</div>
						<div
							class="bg-white border border-ink-200 px-3 py-2"
							style="border-radius: 6px"
						>
							<div
								class="text-[10px] uppercase tracking-wider text-ink-500 font-medium"
							>
								{{ __("Left out") }}
							</div>
							<div class="text-lg font-semibold text-ink-900 tabular-nums">
								{{ plan.skipped.length + payload.skippedByChoice }}
							</div>
							<div class="text-[10px] text-ink-500">
								{{
									__("{0} total or blank-description rows, {1} by your choice", [
										plan.skipped.length,
										payload.skippedByChoice,
									])
								}}
							</div>
						</div>
						<div
							class="bg-white border border-ink-200 px-3 py-2"
							style="border-radius: 6px"
						>
							<div
								class="text-[10px] uppercase tracking-wider text-ink-500 font-medium"
							>
								{{ __("New units") }}
							</div>
							<div class="text-lg font-semibold text-ink-900 tabular-nums">
								{{ payload.units.length }}
							</div>
							<div class="text-[10px] text-ink-500 truncate">
								{{ payload.units.join(", ") || __("none") }}
							</div>
						</div>
					</div>

					<!-- Things to create or decide, before anything is written -->
					<section
						v-if="needsAnswers || newGroups.length"
						class="border border-warning-200 bg-warning-50 mb-4"
						style="border-radius: 8px"
					>
						<header class="px-4 py-2.5 border-b border-warning-200">
							<div class="text-sm font-semibold text-ink-900">
								{{ __("Check these before importing") }}
							</div>
							<div class="text-[11px] text-ink-700">
								{{ __("Nothing is created until you press Import.") }}
							</div>
						</header>
						<div class="p-4 space-y-4">
							<div
								v-for="u in plan.units"
								:key="u.raw"
								class="bg-white border border-ink-200 px-3 py-3"
								style="border-radius: 6px"
							>
								<div class="text-sm text-ink-900">
									{{ __("Unit") }}
									<span class="font-semibold">"{{ u.raw }}"</span>
									<span class="text-ink-500">
										·
										{{
											u.count === 1
												? __("{0} row", [u.count])
												: __("{0} rows", [u.count])
										}}
										·
										{{
											u.status === "alias"
												? __("looks like {0}", [u.suggestion])
												: __("not in the unit list")
										}}</span
									>
								</div>
								<div
									class="flex flex-wrap items-center gap-x-5 gap-y-2 mt-2 text-sm text-ink-700"
								>
									<label class="flex items-center gap-2">
										<input
											type="radio"
											class="accent-brand-600"
											:name="'u-' + u.raw"
											:checked="
												decisions.units[u.raw.toLowerCase()]?.action ===
												'create'
											"
											@change="
												setUnit(u.raw, { action: 'create', value: u.raw })
											"
										/>
										{{ __('Create "{0}" as a new unit', [u.raw]) }}
									</label>
									<label class="flex items-center gap-2">
										<input
											type="radio"
											class="accent-brand-600"
											:name="'u-' + u.raw"
											:checked="
												decisions.units[u.raw.toLowerCase()]?.action ===
												'map'
											"
											@change="
												setUnit(u.raw, {
													action: 'map',
													value:
														decisions.units[u.raw.toLowerCase()]
															?.value &&
														decisions.units[u.raw.toLowerCase()]
															.action === 'map'
															? decisions.units[u.raw.toLowerCase()]
																	.value
															: u.suggestion || 'Nos',
												})
											"
										/>
										{{ __("Use an existing unit") }}
									</label>
									<div
										v-if="
											decisions.units[u.raw.toLowerCase()]?.action === 'map'
										"
										class="w-48"
									>
										<DeskLinkPicker
											doctype="UOM"
											:model-value="
												decisions.units[u.raw.toLowerCase()].value
											"
											:placeholder="__('Search units…')"
											@update:model-value="
												(v) => setUnit(u.raw, { action: 'map', value: v })
											"
										/>
									</div>
									<label class="flex items-center gap-2">
										<input
											type="radio"
											class="accent-brand-600"
											:name="'u-' + u.raw"
											:checked="
												decisions.units[u.raw.toLowerCase()]?.action ===
												'skip'
											"
											@change="setUnit(u.raw, { action: 'skip' })"
										/>
										{{ __("Leave these rows out") }}
									</label>
								</div>
							</div>

							<div
								v-if="plan.missingUnit"
								class="bg-white border border-ink-200 px-3 py-3"
								style="border-radius: 6px"
							>
								<div class="text-sm text-ink-900">
									{{
										plan.missingUnit === 1
											? __("{0} row has", [plan.missingUnit])
											: __("{0} rows have", [plan.missingUnit])
									}}
									<span class="font-semibold">{{ __("no unit") }}</span>
								</div>
								<div
									class="flex flex-wrap items-center gap-x-5 gap-y-2 mt-2 text-sm text-ink-700"
								>
									<label class="flex items-center gap-2">
										<input
											type="radio"
											name="missing"
											class="accent-brand-600"
											:checked="decisions.missingUnit.action === 'set'"
											@change="
												setMissing({
													action: 'set',
													value: decisions.missingUnit.value || 'Nos',
												})
											"
										/>
										{{ __("Give them") }}
									</label>
									<div
										v-if="decisions.missingUnit.action === 'set'"
										class="w-48"
									>
										<DeskLinkPicker
											doctype="UOM"
											:model-value="decisions.missingUnit.value"
											:placeholder="__('Search units…')"
											@update:model-value="(v) => setMissing({ value: v })"
										/>
									</div>
									<label class="flex items-center gap-2">
										<input
											type="radio"
											name="missing"
											class="accent-brand-600"
											:checked="decisions.missingUnit.action === 'skip'"
											@change="setMissing({ action: 'skip' })"
										/>
										{{ __("Leave them out") }}
									</label>
								</div>
							</div>

							<div
								v-if="newGroups.length"
								class="bg-white border border-ink-200 px-3 py-3"
								style="border-radius: 6px"
							>
								<div class="text-sm text-ink-900">
									{{
										newGroups.length === 1
											? __("{0} new group will be created", [
													newGroups.length,
											  ])
											: __("{0} new groups will be created", [
													newGroups.length,
											  ])
									}}
								</div>
								<div class="text-xs text-ink-600 mt-1">
									{{
										newGroups
											.map((g) => (g.code ? g.code + " " : "") + g.name)
											.join(" · ")
									}}.
									{{
										__(
											"A code this BOQ already uses is replaced with the next free one."
										)
									}}
								</div>
							</div>
						</div>
					</section>

					<!-- Preview -->
					<section class="border border-ink-200" style="border-radius: 8px">
						<header
							class="px-4 py-2.5 border-b border-ink-100 flex flex-wrap items-center justify-between gap-2"
						>
							<div class="text-sm font-semibold text-ink-900">
								{{ __("Preview") }}
								<span class="text-xs font-normal text-ink-500"
									>·
									{{
										previewGroups.length === 1
											? __("{0} group", [previewGroups.length])
											: __("{0} groups", [previewGroups.length])
									}}</span
								>
							</div>
							<div class="flex flex-wrap items-center gap-4">
								<button
									v-if="previewGroups.length > 1"
									type="button"
									class="text-xs text-brand-700 hover:underline"
									@click="setAll(!allOpen)"
								>
									{{ allOpen ? __("Collapse all") : __("Expand all") }}
								</button>
								<label class="flex items-center gap-2 text-xs text-ink-700">
									<input
										v-model="showNotesOnly"
										type="checkbox"
										class="accent-brand-600"
									/>
									{{ __("Only rows with notes ({0})", [notedCount]) }}
								</label>
							</div>
						</header>
						<div class="overflow-x-auto">
							<table class="w-full text-sm min-w-[900px]">
								<thead class="bg-ink-50 border-b border-ink-200">
									<tr
										class="text-[11px] uppercase tracking-wider text-ink-500 text-left"
									>
										<th class="px-3 py-2 font-medium w-14">{{ __("Row") }}</th>
										<th class="px-3 py-2 font-medium w-24">
											{{ __("Code") }}
										</th>
										<th class="px-3 py-2 font-medium">
											{{ __("Description") }}
										</th>
										<th class="px-3 py-2 font-medium text-right w-20">
											{{ __("Qty") }}
										</th>
										<th class="px-3 py-2 font-medium">{{ __("Unit") }}</th>
										<th class="px-3 py-2 font-medium text-right w-28">
											{{ __("Rate") }}
										</th>
										<th class="px-3 py-2 font-medium text-right w-32">
											{{ __("Amount") }}
										</th>
										<th class="px-3 py-2 font-medium">{{ __("Notes") }}</th>
									</tr>
								</thead>
								<tbody v-if="!previewRows.length">
									<tr>
										<td colspan="8" class="px-3 py-4 text-sm text-ink-500">
											{{ __("No lines found with these columns.") }}
										</td>
									</tr>
								</tbody>
								<tbody v-for="g in previewGroups" :key="g.key">
									<!-- The group's own row: click to fold its lines away. -->
									<tr class="bg-ink-50 border-b border-ink-200">
										<td colspan="6" class="p-0">
											<button
												type="button"
												class="w-full flex items-center gap-2 px-3 py-2 text-left hover:bg-ink-100"
												:aria-expanded="isOpen(g.key)"
												:data-group="g.name"
												@click="toggleGroup(g.key)"
											>
												<svg
													width="16"
													height="16"
													viewBox="0 0 24 24"
													fill="none"
													stroke="currentColor"
													stroke-width="2"
													stroke-linecap="round"
													stroke-linejoin="round"
													class="text-ink-500 flex-shrink-0 transition-transform"
													:class="isOpen(g.key) ? 'rotate-90' : ''"
												>
													<path d="m9 18 6-6-6-6" />
												</svg>
												<span
													v-if="g.code"
													class="font-mono text-xs text-ink-500"
													>{{ g.code }}</span
												>
												<span class="font-semibold text-ink-900">{{
													g.name
												}}</span>
												<span
													class="text-[10px] px-1.5 py-0.5 rounded-full font-medium"
													:class="
														g.existingId
															? 'bg-ink-100 text-ink-600'
															: 'bg-brand-50 text-brand-700'
													"
													>{{
														g.existingId
															? __("Existing group")
															: __("New group")
													}}</span
												>
												<span class="text-xs text-ink-500">
													{{
														g.count === 1
															? __("{0} line", [g.count])
															: __("{0} lines", [g.count])
													}}<template
														v-if="
															g.rows.length < g.count &&
															!showNotesOnly
														"
													>
														·
														{{
															__("first {0} shown", [g.rows.length])
														}}</template
													>
												</span>
											</button>
										</td>
										<td
											class="px-3 py-2 text-right tabular-nums font-semibold text-ink-900 whitespace-nowrap"
										>
											{{ fmtINR(g.amount) }}
										</td>
										<td
											class="px-3 py-2 text-[11px] text-ink-500 whitespace-nowrap"
										>
											{{ g.noted ? __("{0} with notes", [g.noted]) : "" }}
										</td>
									</tr>
									<tr
										v-for="it in isOpen(g.key) ? g.rows : []"
										:key="it.rowNo"
										class="border-b border-ink-100 align-top"
										:class="
											resolvedUnit(it).tone === 'skip' ? 'opacity-50' : ''
										"
									>
										<td class="px-3 py-2 text-ink-500 tabular-nums">
											{{ it.rowNo }}
										</td>
										<td class="px-3 py-2 text-ink-700">
											{{ it.code || __("auto") }}
										</td>
										<td class="px-3 py-2 text-ink-900">
											{{ it.description }}
										</td>
										<td class="px-3 py-2 text-right tabular-nums text-ink-900">
											{{ it.qty }}
										</td>
										<td
											class="px-3 py-2 whitespace-nowrap"
											:class="{
												'text-ink-900': resolvedUnit(it).tone === 'ok',
												'text-warning-700':
													resolvedUnit(it).tone === 'set',
												'text-danger-700':
													resolvedUnit(it).tone === 'skip',
											}"
										>
											{{ resolvedUnit(it).text }}
										</td>
										<td class="px-3 py-2 text-right tabular-nums text-ink-900">
											{{ fmtINR(it.rate) }}
										</td>
										<td class="px-3 py-2 text-right tabular-nums text-ink-900">
											{{ fmtINR(it.amount) }}
										</td>
										<td class="px-3 py-2 text-[11px] text-ink-600">
											<div v-for="n in it.notes" :key="n">{{ n }}</div>
										</td>
									</tr>
								</tbody>
							</table>
						</div>
						<div
							v-if="
								(showNotesOnly ? notedCount : plan.items.length) >
								previewRows.length
							"
							class="px-4 py-2 text-[11px] text-ink-500 border-t border-ink-100"
						>
							{{
								__("Showing the first {0}. Every line is imported.", [
									previewRows.length,
								])
							}}
						</div>
						<div
							v-if="plan.skipped.length"
							class="px-4 py-2 text-[11px] text-ink-500 border-t border-ink-100"
						>
							{{ __("Left out:") }}
							{{
								plan.skipped
									.map(
										(x) =>
											__("row {0}", [x.rowNo]) +
											" (" +
											x.reason.toLowerCase() +
											")"
									)
									.join(", ")
							}}.
						</div>
					</section>

					<div class="flex justify-end gap-2 mt-4">
						<button
							type="button"
							class="text-xs px-3 py-1.5 border border-ink-200 text-ink-700 hover:bg-ink-50"
							style="border-radius: 6px"
							@click="router.push(`/boq/${boqId}`)"
						>
							{{ __("Cancel") }}
						</button>
						<button
							type="button"
							class="desk-save-btn"
							:disabled="!payload.items.length || importing"
							@click="importNow"
						>
							{{
								payload.items.length === 1
									? __("Import 1 line")
									: __("Import {0} lines", [payload.items.length])
							}}
						</button>
					</div>
				</template>
			</template>
		</template>
	</DeskPage>
</template>
