<script setup>
// CostCodePicker — reusable cost-code field for Work Order SOV lines.
//
// One field pointing at "the level the user chose to code to": a BOQ
// GROUP is the coarse default; an ITEM is optional finer precision.
// Group is derived from whatever node is picked (an item carries its
// parent group_code), never a separate field.
//
// Unlike the prototype (which walked the local BOQ store), this reads a
// flat cost-code list from the backend — buildsuite_core.api.subcontract
// .get_project_cost_codes — and rebuilds the group → item tree client-side.
//
// Props:
//   modelValue        — current selection ({ type, group_code, item_code,
//                       label } | null | legacy string).
//   projectId         — the project whose BOQ the codes come from.
//   placeholder       — control's empty-state label.
//
// Emits:
//   update:modelValue → { type:'group'|'item', group_code, item_code, label } | null

import { ref, computed, watch } from "vue";
import { getProjectCostCodes } from "@/data/subcontractApi";

const props = defineProps({
	modelValue: { type: [Object, String], default: null },
	projectId: { type: String, default: "" },
	placeholder: { type: String, default: "— Pick cost code —" },
});
const emit = defineEmits(["update:modelValue"]);

const open = ref(false);
const search = ref("");
const expanded = ref(new Set());
const loading = ref(false);
const codes = ref([]); // flat [{ type, group_code, item_code, label }]

// Fetch the project's cost codes whenever the project changes.
watch(
	() => props.projectId,
	async (project) => {
		codes.value = [];
		if (!project) return;
		loading.value = true;
		try {
			codes.value = (await getProjectCostCodes(project)) || [];
		} catch {
			codes.value = [];
		} finally {
			loading.value = false;
		}
	},
	{ immediate: true },
);

// Rebuild the group → item tree from the flat list.
const groups = computed(() =>
	codes.value
		.filter((c) => c.type === "Group")
		.map((g) => ({
			code: g.group_code,
			name: (g.label || "").split(" · ").slice(1).join(" · "),
			label: g.label,
		})),
);

function itemsForGroup(groupCode) {
	return codes.value.filter((c) => c.type === "Item" && c.group_code === groupCode);
}

const filteredGroups = computed(() => {
	const term = search.value.trim().toLowerCase();
	if (!term) return groups.value;
	return groups.value.filter((g) => {
		const inGroup = (g.label || "").toLowerCase().includes(term);
		if (inGroup) return true;
		return itemsForGroup(g.code).some((it) => (it.label || "").toLowerCase().includes(term));
	});
});

function filteredItemsForGroup(groupCode) {
	const items = itemsForGroup(groupCode);
	const term = search.value.trim().toLowerCase();
	if (!term) return items;
	const g = groups.value.find((g) => g.code === groupCode);
	const groupMatched = g && (g.label || "").toLowerCase().includes(term);
	if (groupMatched) return items;
	return items.filter((it) => (it.label || "").toLowerCase().includes(term));
}

watch(search, (v) => {
	if (!v.trim()) return;
	const next = new Set(expanded.value);
	filteredGroups.value.forEach((g) => next.add(g.code));
	expanded.value = next;
});

function toggleExpanded(groupCode) {
	const next = new Set(expanded.value);
	if (next.has(groupCode)) next.delete(groupCode);
	else next.add(groupCode);
	expanded.value = next;
}

function pickGroup(g) {
	emit("update:modelValue", {
		type: "group",
		group_code: g.code,
		item_code: null,
		label: g.label,
	});
	closePicker();
}

function pickItem(it) {
	emit("update:modelValue", {
		type: "item",
		group_code: it.group_code,
		item_code: it.item_code,
		label: it.label,
	});
	closePicker();
}

function clearSelection() {
	emit("update:modelValue", null);
	closePicker();
}

const displayLabel = computed(() => {
	const v = props.modelValue;
	if (!v) return "";
	if (typeof v === "string") return v;
	return v.label || v.group_code || "";
});

const displayType = computed(() => {
	const v = props.modelValue;
	if (!v || typeof v === "string") return null;
	return v.type || null;
});

function openPicker() {
	if (!props.projectId) return;
	open.value = true;
}
function closePicker() {
	open.value = false;
	search.value = "";
}
</script>

<template>
	<div class="relative">
		<button
			type="button"
			class="w-full text-left bg-ink-50 border border-ink-200 rounded px-2 py-1 text-xs hover:border-ink-300 focus:outline-none focus:ring-1 focus:ring-brand-400 focus:bg-white inline-flex items-center gap-1.5"
			:disabled="!projectId"
			@click="openPicker"
		>
			<span v-if="displayLabel" class="text-ink-900 truncate flex-1">{{
				displayLabel
			}}</span>
			<span v-else class="text-ink-400 flex-1">{{ placeholder }}</span>
			<span
				v-if="displayType === 'item'"
				class="text-[9px] px-1 py-0.5 bg-brand-50 text-brand-700 rounded font-medium uppercase tracking-wider flex-shrink-0"
				>Item</span
			>
			<span
				v-else-if="displayType === 'group'"
				class="text-[9px] px-1 py-0.5 bg-info-50 text-info-700 rounded font-medium uppercase tracking-wider flex-shrink-0"
				>Group</span
			>
		</button>

		<Teleport to="body">
			<div
				v-if="open"
				class="fixed inset-0 bg-ink-900/40 z-[60] flex items-start justify-center p-6"
				@click.self="closePicker"
			>
				<div
					class="bg-white border border-ink-200 w-full max-w-2xl shadow-lg flex flex-col"
					style="border-radius: 12px; max-height: 80vh"
					@click.stop
				>
					<header
						class="px-4 py-3 border-b border-ink-200 flex items-center justify-between gap-3 flex-shrink-0"
					>
						<div class="flex-1">
							<h2 class="text-sm font-semibold text-ink-900">Pick cost code</h2>
							<p class="text-[11px] text-ink-500 mt-0.5">
								Pick a group, or expand and drill to an item.
							</p>
						</div>
						<button
							type="button"
							class="text-ink-400 hover:text-ink-900"
							@click="closePicker"
							aria-label="Close"
						>
							✕
						</button>
					</header>

					<div class="px-4 py-2 border-b border-ink-100 flex-shrink-0">
						<input
							v-model="search"
							type="text"
							placeholder="Search code or description (e.g. slab, flooring, D.02)…"
							class="w-full text-xs px-2 py-1.5 border border-ink-200 rounded focus:outline-none focus:ring-2 focus:ring-brand-200 focus:border-brand-400"
						/>
					</div>

					<div class="flex-1 overflow-y-auto">
						<div
							v-if="loading"
							class="px-4 py-12 text-center text-xs text-ink-400 italic"
						>
							Loading cost codes…
						</div>
						<div
							v-else-if="!codes.length"
							class="px-4 py-12 text-center text-xs text-ink-400 italic"
						>
							No BOQ found for this project yet. Cost coding is best done after the
							BOQ lands.
						</div>
						<div
							v-else-if="!filteredGroups.length"
							class="px-4 py-12 text-center text-xs text-ink-400 italic"
						>
							No matching cost codes.
						</div>
						<ul v-else>
							<li
								v-for="g in filteredGroups"
								:key="g.code"
								class="border-b border-ink-100"
							>
								<div class="flex items-center gap-1 hover:bg-brand-50/40">
									<button
										type="button"
										class="text-[10px] text-ink-500 hover:text-ink-900 w-7 py-2"
										@click="toggleExpanded(g.code)"
									>
										{{ expanded.has(g.code) ? "▾" : "▸" }}
									</button>
									<button
										type="button"
										class="flex-1 text-left text-xs flex items-baseline gap-2 py-2 pr-3"
										@click="pickGroup(g)"
									>
										<span class="font-mono text-info-700 font-medium">{{
											g.code
										}}</span>
										<span class="text-ink-900">{{ g.name }}</span>
										<span
											class="ml-auto text-[9px] text-info-700 bg-info-50 px-1.5 py-0.5 rounded uppercase tracking-wider"
											>Group</span
										>
									</button>
								</div>
								<ul v-if="expanded.has(g.code)" class="bg-ink-50/40">
									<li
										v-for="it in filteredItemsForGroup(g.code)"
										:key="it.item_code"
										class="border-t border-ink-100"
									>
										<button
											type="button"
											class="w-full text-left px-3 py-2 hover:bg-brand-50/40 text-xs flex items-baseline gap-2 pl-12"
											@click="pickItem(it)"
										>
											<span class="font-mono text-brand-700">{{
												it.item_code
											}}</span>
											<span class="text-ink-700 truncate flex-1">{{
												(it.label || "").split(" · ").slice(1).join(" · ")
											}}</span>
											<span
												class="text-[9px] text-brand-700 bg-brand-50 px-1.5 py-0.5 rounded uppercase tracking-wider whitespace-nowrap"
												>Item</span
											>
										</button>
									</li>
									<li
										v-if="!filteredItemsForGroup(g.code).length"
										class="px-3 py-2 pl-12 text-[11px] text-ink-400 italic"
									>
										No items match
									</li>
								</ul>
							</li>
						</ul>
					</div>

					<footer
						class="px-4 py-2 border-t border-ink-200 flex items-center justify-between gap-3 bg-ink-50/40 flex-shrink-0"
					>
						<span class="text-[11px] text-ink-500"
							>Group covers most cases. Items are optional precision.</span
						>
						<button
							v-if="modelValue"
							type="button"
							class="text-[11px] text-danger-700 hover:underline"
							@click="clearSelection"
						>
							Clear selection
						</button>
					</footer>
				</div>
			</div>
		</Teleport>
	</div>
</template>
