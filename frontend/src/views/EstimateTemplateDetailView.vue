<script setup>
// Estimate Template detail — group-first authoring (BOQ-style): groups are structural
// (a `groups` child table) and created first; items map under a fixed group. Groups and
// rows join by the group's name, so a rename/delete rewrites both tables in one save.
import { computed, reactive, ref, watch } from "vue";
import { useRouter } from "vue-router";
import { useDataStore } from "@/stores";
import { useConfirm } from "@/composables/useConfirm";
import { useFormErrors } from "@/composables/useFormErrors";
import { useDoctypeMeta } from "@/composables/useDoctypeMeta";
import { useDocTypeList } from "@/composables/useDocTypeList";
import { showToast } from "@/utils/appToast";
import { createDataAdapter } from "@/data/adapters";
import { fmtINR, fmtDate } from "@/utils/format";
import DeskPage from "@/components/desk/DeskPage.vue";
import DeskSection from "@/components/desk/DeskSection.vue";
import DeskField from "@/components/desk/DeskField.vue";
import DeskInput from "@/components/desk/DeskInput.vue";
import DeskSelect from "@/components/desk/DeskSelect.vue";
import DeskTextarea from "@/components/desk/DeskTextarea.vue";
import DeskLinkPicker from "@/components/desk/DeskLinkPicker.vue";
import DeskSearchableSelect from "@/components/desk/DeskSearchableSelect.vue";

// 7 columns — no Group column on item rows (the group is structural).
const GRID_COLS = "minmax(200px, 1.4fr) 60px 120px 110px 130px 150px 44px";

const props = defineProps({ id: String });
const router = useRouter();
const confirmDialog = useConfirm();
const { errors, applyServerErrors, setErrors } = useFormErrors({ template_name: "templateName" });
const adapter = createDataAdapter(useDataStore());

const groupKeyOf = (row) => (row?.group_name || "").trim().toLowerCase();

// ===== Data reads =====
const resource = adapter.read("Estimate Template", props.id, { fields: ["*"] });
const doc = computed(() => resource?.doc || null);
const rawRows = computed(() => doc.value?.rows || []);
const rawGroups = computed(() => doc.value?.groups || []);

const assembliesRes = useDocTypeList("Assembly", {
	fields: ["name", "assembly_name", "category", "rate_per_unit", "uom"],
	filters: [["disabled", "=", 0]],
	orderBy: "assembly_name asc",
	pageLength: 0,
	cache: "buildsuite-assembly-options",
});
const rateMastersRes = useDocTypeList("Construction Rate Master", {
	fields: ["name", "rate_name", "category", "current_rate", "uom"],
	filters: [["disabled", "=", 0]],
	orderBy: "category asc",
	pageLength: 0,
	cache: "buildsuite-rate-master-options",
});
const assemblyMap = computed(() =>
	Object.fromEntries((assembliesRes.data || []).map((a) => [a.name, a])),
);
const rateMap = computed(() =>
	Object.fromEntries((rateMastersRes.data || []).map((r) => [r.name, r])),
);

const { selectOptions } = useDoctypeMeta("Estimate Template Row");
const costHeadOptions = computed(() => selectOptions("cost_head"));

const breadcrumbs = computed(() => [
	{ label: "BuildSuite Core", to: "/" },
	{ label: "Estimation", to: "/estimation" },
	{ label: "Estimate Template", to: "/estimate-template" },
	{ label: doc.value?.template_name || props.id },
]);

// ===== Source picker (Assembly + Rate Master pooled) =====
// Value is prefix-encoded — A:<assembly> / R:<rate master> — decoded in sourceToFields().
const sourceOptions = computed(() => {
	const out = [];
	for (const a of assembliesRes.data || []) {
		out.push({
			value: `A:${a.name}`,
			label: `${a.name} · ${a.assembly_name}`,
			group: "Assembly",
			hint: `${fmtINR(a.rate_per_unit)} per ${a.uom}`,
		});
	}
	for (const r of rateMastersRes.data || []) {
		out.push({
			value: `R:${r.name}`,
			label: `${r.name} · ${r.rate_name}`,
			group: r.category,
			hint: `${fmtINR(r.current_rate)} per ${r.uom}`,
		});
	}
	return out;
});

function sourceToFields(source) {
	if (source.startsWith("A:"))
		return { line_type: "Assembly", assembly: source.slice(2), resource: null };
	return { line_type: "Resource", resource: source.slice(2), assembly: null };
}

// ===== Derived rows + group-first grouping =====
function decorate(row) {
	let unit = row.uom || "";
	let liveRate = 0;
	let sourceLabel = "";
	let sourceKind = "";
	if (row.line_type === "Assembly") {
		sourceKind = "Assembly";
		const a = assemblyMap.value[row.assembly];
		if (a) {
			unit = unit || a.uom;
			liveRate = a.rate_per_unit || 0;
			sourceLabel = a.assembly_name;
		}
	} else if (row.line_type === "Resource") {
		sourceKind = "Rate Master";
		const r = rateMap.value[row.resource];
		if (r) {
			unit = unit || r.uom;
			liveRate = r.current_rate || 0;
			sourceLabel = r.rate_name;
		}
	}
	const qty = Number(row.placeholder_qty) || 0;
	// Prefer the stored (server-computed) rate/amount; fall back to a live resolve pre-save.
	const rate = Number(row.rate) || 0 || liveRate;
	const amount = Number(row.amount) || 0 || qty * rate;
	return {
		...row,
		unit,
		rate,
		qty,
		amount,
		sourceKind,
		sourceLabel: sourceLabel || row.description || row.assembly || row.resource || "—",
	};
}

const previewRows = computed(() => rawRows.value.map(decorate));
const estimatedTotal = computed(() => previewRows.value.reduce((sum, r) => sum + r.amount, 0));

// Render groups in their stored order (empty groups still show); rows with an unknown
// or blank group fall into a trailing, non-editable "Ungrouped" bucket.
const groupedRows = computed(() => {
	const byKey = new Map();
	for (const row of previewRows.value) {
		const key = groupKeyOf(row);
		if (!byKey.has(key)) byKey.set(key, []);
		byKey.get(key).push(row);
	}
	const build = (key, name, real) => {
		const rows = byKey.get(key) || [];
		return {
			key: real ? name : "__ungrouped__",
			name,
			rows,
			count: rows.length,
			subtotal: rows.reduce((a, r) => a + r.amount, 0),
			real,
		};
	};
	const out = [];
	for (const g of rawGroups.value) {
		const name = (g.group_name || "").trim();
		if (!name) continue;
		const key = name.toLowerCase();
		out.push(build(key, name, true));
		byKey.delete(key);
	}
	for (const [key, rows] of byKey.entries()) {
		if (rows.length) out.push(build(key, key ? rows[0].group_name : "Ungrouped", false));
	}
	return out;
});

const cards = computed(() => {
	const d = doc.value;
	if (!d) return [];
	return [
		{ label: "Project Category", value: d.project_category || "Any" },
		{ label: "Rows", value: rawRows.value.length, cls: "tabular-nums" },
		{
			label: "Estimated total",
			value: fmtINR(estimatedTotal.value),
			cls: "tabular-nums font-semibold",
		},
		{ label: "Updated", value: fmtDate(d.modified), cls: "text-xs" },
	];
});

// ===== Persistence core =====
// Snapshot the child tables keeping each `name` so Frappe updates rows in place.
function currentRows() {
	return rawRows.value.map((r) => ({
		name: r.name,
		line_type: r.line_type,
		assembly: r.assembly || null,
		resource: r.resource || null,
		group_name: r.group_name || "",
		placeholder_qty: r.placeholder_qty || 0,
		cost_head: r.cost_head || "",
		description: r.description || "",
	}));
}
function currentGroups() {
	return rawGroups.value.map((g) => ({ name: g.name, group_name: g.group_name || "" }));
}

const savingRows = ref(false);

// Single write path — patch may carry `rows`, `groups`, or both.
async function persistTemplate(patch) {
	savingRows.value = true;
	try {
		await adapter.update("Estimate Template", props.id, patch);
		await resource?.reload?.();
	} catch (err) {
		showToast(applyServerErrors(err) ?? "Failed to update template", "error");
	} finally {
		savingRows.value = false;
	}
}

// ===== Metadata edit (modal) + delete =====
const editing = ref(false);
const saving = ref(false);
const form = ref({});

function snapshot() {
	const d = doc.value;
	if (!d) return {};
	return {
		templateName: d.template_name || "",
		projectType: d.project_category || "",
		enabled: !!d.enabled,
		description: d.description || "",
	};
}
watch(
	doc,
	(v) => {
		if (v && !editing.value) form.value = snapshot();
	},
	{ immediate: true },
);

function startEdit() {
	form.value = snapshot();
	setErrors({});
	editing.value = true;
}
function cancelEdit() {
	editing.value = false;
}

async function saveEdit() {
	const e = {};
	if (!form.value.templateName?.trim()) e.templateName = "Name is required";
	setErrors(e);
	if (Object.keys(e).length) return;

	saving.value = true;
	try {
		await adapter.update("Estimate Template", props.id, {
			template_name: form.value.templateName.trim(),
			project_category: form.value.projectType || null,
			enabled: form.value.enabled ? 1 : 0,
			description: form.value.description,
		});
		resource?.reload?.();
		editing.value = false;
	} catch (err) {
		showToast(applyServerErrors(err) ?? "Failed to update template", "error");
	} finally {
		saving.value = false;
	}
}

async function onDelete() {
	const ok = await confirmDialog({
		title: "Delete estimate template",
		message: `Delete "${doc.value?.template_name}" (${doc.value?.template_code})? This cannot be undone.`,
		confirmLabel: "Delete",
		destructive: true,
	});
	if (!ok) return;
	try {
		await adapter.remove("Estimate Template", props.id);
		router.push("/estimate-template");
	} catch (err) {
		showToast(applyServerErrors(err) ?? "Failed to delete template", "error");
	}
}

// ===== Group authoring =====
const addingGroup = ref(false);
const newGroupName = ref("");
const editingGroupKey = ref("");
const editGroupName = ref("");

// Name collides with an existing group (case-insensitive), ignoring `self`.
function groupNameTaken(name, self = "") {
	const key = name.trim().toLowerCase();
	return rawGroups.value.some((g) => {
		const gk = (g.group_name || "").trim().toLowerCase();
		return gk === key && gk !== self.toLowerCase();
	});
}

function startAddGroup() {
	newGroupName.value = "";
	addingGroup.value = true;
}
function cancelAddGroup() {
	addingGroup.value = false;
	newGroupName.value = "";
}
async function saveAddGroup() {
	const name = newGroupName.value.trim();
	if (!name) return;
	if (groupNameTaken(name)) return showToast("A group with that name already exists.", "error");
	await persistTemplate({ groups: [...currentGroups(), { group_name: name }] });
	cancelAddGroup();
}

function startRenameGroup(group) {
	editingGroupKey.value = group.key;
	editGroupName.value = group.name;
}
function cancelRenameGroup() {
	editingGroupKey.value = "";
	editGroupName.value = "";
}
async function saveRenameGroup(group) {
	const name = editGroupName.value.trim();
	if (!name || name === group.name) return cancelRenameGroup();
	if (groupNameTaken(name, group.name))
		return showToast("A group with that name already exists.", "error");
	// Rename the group AND re-point every row joined to its old name, in one save.
	const groups = currentGroups().map((g) =>
		(g.group_name || "").trim() === group.name ? { ...g, group_name: name } : g,
	);
	const rows = currentRows().map((r) =>
		(r.group_name || "").trim() === group.name ? { ...r, group_name: name } : r,
	);
	await persistTemplate({ groups, rows });
	cancelRenameGroup();
}

async function removeGroup(group) {
	const ok = await confirmDialog({
		title: "Delete group",
		message: group.count
			? `Delete "${group.name}" and its ${group.count} row${
					group.count === 1 ? "" : "s"
				}? This cannot be undone.`
			: `Delete the empty group "${group.name}"?`,
		confirmLabel: "Delete",
		destructive: true,
	});
	if (!ok) return;
	const groups = currentGroups().filter((g) => (g.group_name || "").trim() !== group.name);
	const rows = currentRows().filter((r) => (r.group_name || "").trim() !== group.name);
	await persistTemplate({ groups, rows });
}

// ===== Item authoring (into a fixed group) =====
const blankRow = () => ({
	source: "",
	group_name: "",
	placeholder_qty: 1,
	cost_head: "",
	description: "",
});
const addingRow = ref(""); // group key the add-item form is open under ('' = none)
const newRow = reactive(blankRow());

const newRowSource = computed(() => {
	if (!newRow.source) return null;
	if (newRow.source.startsWith("A:")) {
		const a = assemblyMap.value[newRow.source.slice(2)];
		return a ? { unit: a.uom, rate: a.rate_per_unit } : null;
	}
	const r = rateMap.value[newRow.source.slice(2)];
	return r ? { unit: r.uom, rate: r.current_rate } : null;
});
const newRowAmount = computed(
	() => (Number(newRow.placeholder_qty) || 0) * (newRowSource.value?.rate || 0),
);

function startAddRow(group) {
	Object.assign(newRow, blankRow(), { group_name: group.name });
	addingRow.value = group.key;
}
function cancelAddRow() {
	addingRow.value = "";
}

async function saveAddRow() {
	if (!newRow.source || (Number(newRow.placeholder_qty) || 0) < 0) return;
	await persistTemplate({
		rows: [
			...currentRows(),
			{
				...sourceToFields(newRow.source),
				group_name: newRow.group_name,
				placeholder_qty: Number(newRow.placeholder_qty) || 0,
				cost_head: newRow.cost_head,
				description: newRow.description,
			},
		],
	});
	cancelAddRow();
}

// Edit by child `name` — grouping reorders rows, so the index isn't stable.
function patchRowByName(name, field, value) {
	const next = currentRows();
	const target = next.find((r) => r.name === name);
	if (!target) return;
	target[field] = field === "placeholder_qty" ? Number(value) || 0 : value;
	persistTemplate({ rows: next });
}

async function removeRow(name) {
	const ok = await confirmDialog({
		title: "Remove row",
		message: "Remove this line from the template?",
		confirmLabel: "Remove",
		destructive: true,
	});
	if (!ok) return;
	persistTemplate({ rows: currentRows().filter((r) => r.name !== name) });
}
</script>

<template>
	<DeskPage
		v-if="doc"
		:title="doc.template_name"
		:subtitle="doc.template_code"
		:breadcrumbs="breadcrumbs"
		:status="doc.enabled ? 'Enabled' : 'Disabled'"
	>
		<template #actions>
			<button
				type="button"
				class="text-xs px-2.5 py-1 border border-ink-200 bg-white hover:bg-ink-50 text-ink-700"
				style="border-radius: 6px"
				@click="startEdit"
			>
				Edit
			</button>
			<button
				type="button"
				class="text-xs px-2.5 py-1 border border-danger-200 bg-white hover:bg-danger-50 text-danger-700"
				style="border-radius: 6px"
				@click="onDelete"
			>
				Delete
			</button>
		</template>

		<div class="grid grid-cols-2 md:grid-cols-4 gap-2 mb-4">
			<div
				v-for="c in cards"
				:key="c.label"
				class="bg-white border border-ink-200 px-3 py-2"
				style="border-radius: 6px"
			>
				<div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">
					{{ c.label }}
				</div>
				<div class="text-sm text-ink-900 mt-0.5" :class="c.cls">{{ c.value }}</div>
			</div>
		</div>

		<div
			v-if="doc.description"
			class="mb-4 px-3 py-2 bg-white border border-ink-200"
			style="border-radius: 6px"
		>
			<div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium mb-1">
				Description
			</div>
			<div class="text-sm text-ink-800 leading-snug whitespace-pre-line">
				{{ doc.description }}
			</div>
		</div>

		<DeskSection title="Template rows" :cols="1">
			<div class="flex items-start justify-between gap-3 mb-2 px-1">
				<div class="text-[11px] text-ink-500">
					Groups are created first; items are mapped under them — same structure as a
					BOQ. Assembly-driven rows auto-explode into snapshot sub-items when imported.
				</div>
				<button
					v-if="!addingGroup"
					type="button"
					class="desk-save-btn !text-xs flex-shrink-0"
					:disabled="savingRows"
					@click="startAddGroup"
				>
					+ Add group
				</button>
			</div>

			<div
				v-if="addingGroup"
				class="mb-3 border border-brand-200 bg-brand-50 px-3 py-2.5 flex items-center gap-2"
				style="border-radius: 8px"
			>
				<DeskInput
					v-model="newGroupName"
					placeholder="Group name — e.g. Substructure, Finishes…"
					class="flex-1"
					@keyup.enter="saveAddGroup"
					@keyup.esc="cancelAddGroup"
				/>
				<button
					type="button"
					class="text-xs px-2.5 py-1.5 border border-ink-200 bg-white hover:bg-ink-50 text-ink-700"
					style="border-radius: 6px"
					@click="cancelAddGroup"
				>
					Cancel
				</button>
				<button
					type="button"
					class="desk-save-btn !text-xs"
					:disabled="savingRows"
					@click="saveAddGroup"
				>
					Add group
				</button>
			</div>

			<div
				v-if="groupedRows.length"
				class="border border-ink-200 overflow-x-auto"
				style="border-radius: 8px"
			>
				<div style="min-width: 820px">
					<div
						class="grid bg-gradient-to-r from-brand-50 to-white border-b border-ink-200 text-[10px] uppercase tracking-wider text-ink-500 font-medium"
						:style="{ gridTemplateColumns: GRID_COLS }"
					>
						<div class="px-3 py-1.5">Item source</div>
						<div class="px-2 py-1.5">Unit</div>
						<div class="px-2 py-1.5 text-right">Qty</div>
						<div class="px-2 py-1.5 text-right">Rate</div>
						<div class="px-2 py-1.5 text-right">Amount</div>
						<div class="px-2 py-1.5">Cost head</div>
						<div class="px-2 py-1.5"></div>
					</div>

					<template v-for="group in groupedRows" :key="group.key">
						<div
							class="grid items-center bg-ink-50 border-b border-ink-200 border-t border-t-ink-200 first:border-t-0"
							:style="{ gridTemplateColumns: GRID_COLS }"
						>
							<div class="px-3 py-2" style="grid-column: 1 / span 4">
								<div
									v-if="editingGroupKey === group.key"
									class="flex items-center gap-2"
								>
									<DeskInput
										v-model="editGroupName"
										class="flex-1"
										@keyup.enter="saveRenameGroup(group)"
										@keyup.esc="cancelRenameGroup"
									/>
									<button
										type="button"
										class="text-xs px-2 py-1 border border-ink-200 bg-white hover:bg-ink-50 text-ink-700"
										style="border-radius: 6px"
										@click="cancelRenameGroup"
									>
										Cancel
									</button>
									<button
										type="button"
										class="desk-save-btn !text-xs"
										:disabled="savingRows"
										@click="saveRenameGroup(group)"
									>
										Save
									</button>
								</div>
								<div v-else class="text-sm font-semibold text-ink-900">
									{{ group.name }}
									<span class="ml-2 text-[11px] text-ink-500 font-normal"
										>· {{ group.count }} item{{
											group.count === 1 ? "" : "s"
										}}</span
									>
									<span
										v-if="!group.real"
										class="ml-2 text-[10px] text-warning-700 font-normal italic"
										>unassigned</span
									>
								</div>
							</div>
							<div
								class="px-2 py-2 text-right text-[11px] uppercase tracking-wider text-ink-500 font-medium"
								style="grid-column: 5 / span 1"
							>
								Subtotal
							</div>
							<div
								class="px-2 py-2 text-right tabular-nums font-semibold text-ink-900"
								style="grid-column: 6 / span 1"
							>
								{{ fmtINR(group.subtotal) }}
							</div>
							<div
								class="px-2 py-2 flex items-center justify-end gap-2"
								style="grid-column: 7 / span 1"
							>
								<template v-if="group.real && editingGroupKey !== group.key">
									<button
										type="button"
										class="text-ink-400 hover:text-brand-700 disabled:opacity-40"
										title="Rename group"
										:disabled="savingRows"
										@click="startRenameGroup(group)"
									>
										<svg
											width="14"
											height="14"
											viewBox="0 0 24 24"
											fill="none"
											stroke="currentColor"
											stroke-width="1.75"
											stroke-linecap="round"
											stroke-linejoin="round"
											aria-hidden="true"
										>
											<path
												d="M21.174 6.812a1 1 0 0 0-3.986-3.987L3.842 16.174a2 2 0 0 0-.5.83l-1.321 4.352a.5.5 0 0 0 .623.622l4.353-1.32a2 2 0 0 0 .83-.497Z"
											/>
											<path d="m15 5 4 4" />
										</svg>
									</button>
									<button
										type="button"
										class="text-ink-400 hover:text-danger-700 disabled:opacity-40"
										title="Delete group"
										:disabled="savingRows"
										@click="removeGroup(group)"
									>
										<svg
											width="14"
											height="14"
											viewBox="0 0 24 24"
											fill="none"
											stroke="currentColor"
											stroke-width="1.75"
											stroke-linecap="round"
											stroke-linejoin="round"
											aria-hidden="true"
										>
											<path d="M3 6h18" />
											<path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6" />
											<path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
											<line x1="10" x2="10" y1="11" y2="17" />
											<line x1="14" x2="14" y1="11" y2="17" />
										</svg>
									</button>
								</template>
							</div>
						</div>

						<div class="divide-y divide-ink-100">
							<div
								v-for="row in group.rows"
								:key="row.name"
								class="grid items-center text-sm hover:bg-brand-50/40 transition-colors"
								:style="{ gridTemplateColumns: GRID_COLS }"
							>
								<div class="px-3 py-1.5 min-w-0">
									<div class="text-ink-900 font-medium truncate">
										{{ row.sourceLabel }}
									</div>
									<span
										class="text-[9px] px-1 py-0.5 font-medium uppercase tracking-wider"
										:class="
											row.sourceKind === 'Assembly'
												? 'bg-brand-50 text-brand-700'
												: 'bg-ink-100 text-ink-600'
										"
										style="border-radius: 2px"
										>{{ row.sourceKind || "—" }}</span
									>
								</div>
								<div class="px-2 py-1.5 text-xs text-ink-700">
									{{ row.unit || "—" }}
								</div>
								<div class="px-2 py-1">
									<input
										type="number"
										class="desk-input"
										:value="row.placeholder_qty"
										:min="0"
										step="0.01"
										:disabled="savingRows"
										@change="
											patchRowByName(
												row.name,
												'placeholder_qty',
												$event.target.value,
											)
										"
									/>
								</div>
								<div class="px-2 py-1.5 text-right tabular-nums text-ink-700">
									{{ fmtINR(row.rate) }}
								</div>
								<div
									class="px-2 py-1.5 text-right tabular-nums font-medium text-ink-900"
								>
									{{ fmtINR(row.amount) }}
								</div>
								<div class="px-2 py-1">
									<DeskSelect
										:model-value="row.cost_head"
										:disabled="savingRows"
										@update:model-value="
											(v) => patchRowByName(row.name, 'cost_head', v)
										"
									>
										<option value="">—</option>
										<option v-for="c in costHeadOptions" :key="c">
											{{ c }}
										</option>
									</DeskSelect>
								</div>
								<div class="px-2 py-1 text-right">
									<button
										type="button"
										class="text-ink-400 hover:text-danger-700 text-base leading-none"
										title="Remove"
										:disabled="savingRows"
										@click="removeRow(row.name)"
									>
										×
									</button>
								</div>
							</div>
							<div
								v-if="!group.rows.length && addingRow !== group.key"
								class="px-3 py-2 text-[11px] text-ink-400 italic"
							>
								No items in this group yet.
							</div>
						</div>

						<!-- Group is fixed by which group's button was clicked; the form has no group field. -->
						<template v-if="group.real">
							<template v-if="addingRow === group.key">
								<div
									class="grid items-start text-sm border-t border-ink-200 bg-brand-50"
									:style="{ gridTemplateColumns: GRID_COLS }"
								>
									<div class="px-2 py-2">
										<DeskSearchableSelect
											v-model="newRow.source"
											:options="sourceOptions"
											placeholder="Pick a source…"
											search-placeholder="Search assemblies / rate master…"
										/>
									</div>
									<div class="px-2 py-2 text-[11px] text-ink-500">
										{{ newRowSource?.unit || "auto" }}
									</div>
									<div class="px-2 py-2">
										<DeskInput
											v-model="newRow.placeholder_qty"
											type="number"
											:min="0"
											:step="0.01"
										/>
									</div>
									<div class="px-2 py-2 text-right text-[11px] text-ink-500">
										{{ newRowSource ? fmtINR(newRowSource.rate) : "auto" }}
									</div>
									<div
										class="px-2 py-2 text-right text-[11px] tabular-nums"
										:class="
											newRowSource
												? 'text-ink-900 font-medium'
												: 'text-ink-500'
										"
									>
										{{ newRowSource ? fmtINR(newRowAmount) : "auto" }}
									</div>
									<div class="px-2 py-2">
										<DeskSelect v-model="newRow.cost_head">
											<option value="">—</option>
											<option v-for="c in costHeadOptions" :key="c">
												{{ c }}
											</option>
										</DeskSelect>
									</div>
									<div></div>
								</div>
								<div
									class="bg-brand-50 border-b border-ink-200 px-3 pb-2 flex items-center justify-end gap-2"
								>
									<button
										type="button"
										class="text-xs px-2.5 py-1 border border-ink-200 bg-white hover:bg-ink-50 text-ink-700"
										style="border-radius: 6px"
										@click="cancelAddRow"
									>
										Cancel
									</button>
									<button
										type="button"
										class="desk-save-btn !text-xs"
										:disabled="savingRows"
										@click="saveAddRow"
									>
										+ Add item
									</button>
								</div>
							</template>

							<div v-else class="border-t border-ink-100 px-3 py-1.5 bg-white">
								<button
									type="button"
									class="text-[11px] text-ink-500 hover:text-brand-700"
									@click="startAddRow(group)"
								>
									+ Add item to "{{ group.name }}"
								</button>
							</div>
						</template>
					</template>

					<!-- Footer total — green fades in from the right, toward the total. -->
					<div
						class="grid items-center bg-gradient-to-l from-brand-50 to-white border-t border-ink-200 text-xs"
						:style="{ gridTemplateColumns: GRID_COLS }"
					>
						<div
							class="px-3 py-2 text-[11px] uppercase tracking-wider text-ink-700 font-semibold"
							style="grid-column: 1 / span 4"
						>
							Estimated total
						</div>
						<div
							class="px-2 py-2 text-right text-[11px] uppercase tracking-wider text-ink-500 font-medium"
							style="grid-column: 5 / span 1"
						>
							Grand total
						</div>
						<div
							class="px-2 py-2 text-right tabular-nums font-semibold text-ink-900 text-sm"
							style="grid-column: 6 / span 1"
						>
							{{ fmtINR(estimatedTotal) }}
						</div>
						<div style="grid-column: 7 / span 1"></div>
					</div>
				</div>
			</div>

			<div
				v-else-if="!addingGroup"
				class="border border-ink-200 py-8 text-center"
				style="border-radius: 8px"
			>
				<div class="text-sm text-ink-700 mb-1">No groups yet.</div>
				<div class="text-xs text-ink-500 mb-3">
					Create a group first, then map items under it — same as a BOQ.
				</div>
				<button type="button" class="desk-save-btn !text-xs" @click="startAddGroup">
					+ Add group
				</button>
			</div>
		</DeskSection>

		<Teleport to="body">
			<div
				v-if="editing"
				class="fixed inset-0 bg-ink-900/40 z-[60] flex items-center justify-center p-6"
				@click.self="cancelEdit"
			>
				<div
					class="bg-white border border-ink-200 w-full max-w-2xl shadow-fp-lg flex flex-col"
					style="border-radius: 12px; max-height: calc(100vh - 3rem)"
					@click.stop
				>
					<header
						class="px-5 py-3 border-b border-ink-200 flex items-center justify-between flex-shrink-0 bg-white"
						style="border-radius: 12px 12px 0 0"
					>
						<div class="min-w-0 flex-1">
							<h2 class="text-sm font-semibold text-ink-900">Edit template</h2>
							<p class="text-[11px] text-ink-500 mt-0.5 truncate">
								{{ doc.template_name }}
							</p>
						</div>
						<button
							type="button"
							class="text-ink-500 hover:text-ink-900 text-lg leading-none"
							aria-label="Close"
							@click="cancelEdit"
						>
							×
						</button>
					</header>

					<div class="p-5 overflow-y-auto flex-1">
						<DeskSection title="Basic">
							<DeskField
								label="Code"
								hint="The template's identifier — not editable."
							>
								<span class="text-sm font-mono text-ink-700">{{
									doc.template_code
								}}</span>
							</DeskField>
							<DeskField label="Name" required :error="errors.templateName">
								<DeskInput v-model="form.templateName" />
							</DeskField>
							<DeskField label="Project Category tag" hint="Empty = universal.">
								<DeskLinkPicker
									v-model="form.projectType"
									doctype="Project Category"
									label-field="name"
									value-field="name"
									placeholder="— Universal —"
								/>
							</DeskField>
							<DeskField label="Enabled">
								<label class="inline-flex items-center gap-2 text-sm text-ink-800">
									<input type="checkbox" v-model="form.enabled" />
									<span>Available in pickers</span>
								</label>
							</DeskField>
							<DeskField label="Description">
								<DeskTextarea v-model="form.description" :rows="3" />
							</DeskField>
						</DeskSection>
					</div>

					<footer
						class="px-5 py-3 border-t border-ink-200 flex items-center justify-end gap-2 flex-shrink-0 bg-white"
						style="border-radius: 0 0 12px 12px"
					>
						<button
							type="button"
							class="text-xs px-3 py-1.5 border border-ink-200 bg-white hover:bg-ink-50 text-ink-700"
							style="border-radius: 6px"
							:disabled="saving"
							@click="cancelEdit"
						>
							Cancel
						</button>
						<button
							type="button"
							class="desk-save-btn"
							:disabled="saving"
							@click="saveEdit"
						>
							{{ saving ? "Saving…" : "Save" }}
						</button>
					</footer>
				</div>
			</div>
		</Teleport>
	</DeskPage>

	<div v-else class="px-3 py-2 text-sm text-ink-500">Loading estimate template…</div>
</template>
