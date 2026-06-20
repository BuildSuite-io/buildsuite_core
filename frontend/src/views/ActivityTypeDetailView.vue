<script setup>
// Activity Type — detail/edit view. Desk-styled (CLAUDE.md §12.4). Master DocType
// from §13.3 item 16. Renamed in Session 31 from "Task Type" — see CLAUDE.md §1
// reconciliation rule. Five sections: Basic / Default labour mix / Default
// productivity / Default checklist (child table) / Applicable project types.
// Skilled and Unskilled ratios are mirrored — editing one auto-recomputes the
// other via store.updateActivityType so they always sum to 1.

import { ref, computed, watch } from "vue";
import { useRouter, RouterLink } from "vue-router";
import { useDataStore } from "@/stores";
import { useConfirm } from "@/composables/useConfirm";
import DeskPage from "@/components/desk/DeskPage.vue";
import DeskForm from "@/components/desk/DeskForm.vue";
import DeskActionBar from "@/components/desk/DeskActionBar.vue";
import DeskSection from "@/components/desk/DeskSection.vue";
import DeskField from "@/components/desk/DeskField.vue";
import DeskInput from "@/components/desk/DeskInput.vue";
import DeskSelect from "@/components/desk/DeskSelect.vue";
import DeskTextarea from "@/components/desk/DeskTextarea.vue";
import DeskLink from "@/components/desk/DeskLink.vue";

const props = defineProps({ id: String });
const router = useRouter();
const store = useDataStore();
const confirmDialog = useConfirm();

const CATEGORIES = ["Structural", "Finishing", "MEP", "Earthwork", "Other"];
const PROJECT_TYPES = ["Commercial", "Residential", "Infrastructure", "Industrial", "Renovation"];

const activityType = computed(() => store.activityTypeById(props.id));
const editing = ref(false);
const form = ref({});

// `form` is a deep-cloned working copy so cancelling edit reverts cleanly and
// the checklist child-table edits don't mutate the store record before save.
watch(
	activityType,
	(at) => {
		if (at) form.value = JSON.parse(JSON.stringify(at));
	},
	{ immediate: true }
);

function startEdit() {
	form.value = JSON.parse(JSON.stringify(activityType.value));
	editing.value = true;
}
function cancelEdit() {
	form.value = JSON.parse(JSON.stringify(activityType.value));
	editing.value = false;
}
function saveEdit() {
	// Strip any blank checklist rows the user may have added but not filled.
	const cleanChecklist = (form.value.defaultChecklist || []).filter(
		(c) => c && c.item && c.item.trim()
	);
	store.updateActivityType(props.id, {
		...form.value,
		defaultChecklist: cleanChecklist,
	});
	editing.value = false;
}
function onPrimary() {
	editing.value ? saveEdit() : startEdit();
}

function addChecklistRow() {
	if (!Array.isArray(form.value.defaultChecklist)) form.value.defaultChecklist = [];
	form.value.defaultChecklist.push({ item: "" });
}
function removeChecklistRow(idx) {
	form.value.defaultChecklist.splice(idx, 1);
}

function toggleProjectType(t) {
	const list = form.value.applicableProjectTypes || [];
	const i = list.indexOf(t);
	if (i === -1) list.push(t);
	else list.splice(i, 1);
	form.value.applicableProjectTypes = list;
}

// Skilled ↔ Unskilled mirroring in the edit form. The store also enforces this
// at save time, but mirroring live in the form gives immediate feedback.
function onSkilledChange() {
	const v = Number(form.value.defaultSkilledRatio);
	const safe = Number.isFinite(v) ? Math.min(1, Math.max(0, v)) : 0;
	form.value.defaultSkilledRatio = safe;
	form.value.defaultUnskilledRatio = Number((1 - safe).toFixed(2));
}

async function deleteActivityType() {
	const ok = await confirmDialog({
		title: "Delete Activity Type",
		message: `Delete Activity Type "${activityType.value.name}"?\n\nTasks that reference it will keep the link as a dangling reference (treated as no-link by the UI).`,
		confirmLabel: "Delete",
		destructive: true,
	});
	if (!ok) return;
	store.deleteActivityType(props.id);
	router.push("/activity-types");
}

const linkedTaskCount = computed(
	() => store.tasks.filter((t) => t.activityType === props.id).length
);

const breadcrumbs = computed(() => [
	{ label: "BuildSuite Core", to: "/" },
	{ label: "Activity Type", to: "/activity-types" },
]);

function pct(n) {
	return Math.round((Number(n) || 0) * 100);
}
</script>

<template>
	<DeskPage
		v-if="activityType"
		:title="activityType.name"
		:subtitle="`${activityType.id} · ${activityType.category}`"
		:breadcrumbs="breadcrumbs"
	>
		<DeskForm>
			<template #action-bar>
				<DeskActionBar
					:save-label="editing ? 'Save' : 'Edit'"
					:show-cancel="editing"
					cancel-label="Cancel"
					@save="onPrimary"
					@cancel="cancelEdit"
				>
					<template #left>
						<span v-if="linkedTaskCount" class="text-[11px] text-ink-500">
							{{ linkedTaskCount }} task{{ linkedTaskCount === 1 ? "" : "s" }} linked
						</span>
					</template>
					<template #menu>
						<button
							type="button"
							class="text-xs px-2 py-1 border border-ink-200 bg-white hover:bg-ink-50"
							style="border-radius: 2px; color: #b91c1c"
							@click="deleteActivityType"
						>
							Delete
						</button>
					</template>
				</DeskActionBar>
			</template>

			<!-- Basic -->
			<DeskSection title="Basic" v-if="!editing">
				<DeskField label="Name">
					<div class="text-sm text-ink-900 py-1">{{ activityType.name }}</div>
				</DeskField>
				<DeskField label="Category">
					<div class="text-sm text-ink-900 py-1">{{ activityType.category }}</div>
				</DeskField>
				<DeskField label="Description">
					<div class="text-sm text-ink-700 py-1 whitespace-pre-line">
						{{ activityType.description || "—" }}
					</div>
				</DeskField>
			</DeskSection>
			<DeskSection title="Basic" v-else>
				<DeskField label="Name" required>
					<DeskInput v-model="form.name" />
				</DeskField>
				<DeskField label="Category" required>
					<DeskSelect v-model="form.category">
						<option v-for="c in CATEGORIES" :key="c">{{ c }}</option>
					</DeskSelect>
				</DeskField>
				<DeskField label="Description">
					<DeskTextarea v-model="form.description" :rows="3" />
				</DeskField>
			</DeskSection>

			<!-- Default labour mix -->
			<DeskSection title="Default labour mix" v-if="!editing" :cols="2">
				<DeskField
					label="Skilled ratio"
					hint="Of every man-day, this fraction is skilled labour."
				>
					<div class="text-sm text-ink-900 py-1 tabular-nums">
						{{ pct(activityType.defaultSkilledRatio) }}%
					</div>
				</DeskField>
				<DeskField label="Unskilled ratio" hint="Auto-computed as 100 − skilled.">
					<div class="text-sm text-ink-500 py-1 tabular-nums">
						{{ pct(activityType.defaultUnskilledRatio) }}%
					</div>
				</DeskField>
			</DeskSection>
			<DeskSection title="Default labour mix" v-else :cols="2">
				<DeskField
					label="Skilled ratio (0–1)"
					required
					hint="0.3 = 30% skilled. Unskilled auto-fills."
				>
					<DeskInput
						v-model="form.defaultSkilledRatio"
						type="number"
						step="0.05"
						min="0"
						max="1"
						@change="onSkilledChange"
						@blur="onSkilledChange"
					/>
				</DeskField>
				<DeskField label="Unskilled ratio" hint="Read-only · auto-computed.">
					<DeskInput :model-value="form.defaultUnskilledRatio" disabled />
				</DeskField>
			</DeskSection>

			<!-- Default productivity -->
			<DeskSection title="Default productivity" v-if="!editing" :cols="2">
				<DeskField label="Per man-day">
					<div class="text-sm text-ink-900 py-1 tabular-nums">
						{{ activityType.expectedProductivityPerManDay }}
						{{ activityType.productivityUnit }}
					</div>
				</DeskField>
				<DeskField label="Unit">
					<div class="text-sm text-ink-700 py-1">
						{{ activityType.productivityUnit || "—" }}
					</div>
				</DeskField>
			</DeskSection>
			<DeskSection title="Default productivity" v-else :cols="2">
				<DeskField
					label="Expected per man-day"
					hint="Quantity one worker is expected to complete in one day."
				>
					<DeskInput
						v-model="form.expectedProductivityPerManDay"
						type="number"
						step="0.1"
						min="0"
					/>
				</DeskField>
				<DeskField label="Productivity unit" hint="e.g. m³, m², ton, m, nos">
					<DeskInput v-model="form.productivityUnit" placeholder="m³" />
				</DeskField>
			</DeskSection>

			<!-- Default checklist -->
			<DeskSection title="Default checklist">
				<div class="md:col-span-2">
					<div v-if="!editing">
						<ol
							v-if="
								activityType.defaultChecklist &&
								activityType.defaultChecklist.length
							"
							class="space-y-1.5"
						>
							<li
								v-for="(c, i) in activityType.defaultChecklist"
								:key="i"
								class="flex items-start gap-2 text-sm text-ink-800"
							>
								<span class="text-ink-400 tabular-nums w-5 text-right"
									>{{ i + 1 }}.</span
								>
								<span>{{ c.item }}</span>
							</li>
						</ol>
						<div v-else class="text-xs text-ink-400 italic">
							No checklist items defined.
						</div>
					</div>
					<div v-else>
						<ol class="space-y-1.5">
							<li
								v-for="(c, i) in form.defaultChecklist"
								:key="i"
								class="flex items-center gap-2"
							>
								<span class="text-ink-400 tabular-nums w-5 text-right text-sm"
									>{{ i + 1 }}.</span
								>
								<DeskInput
									v-model="c.item"
									placeholder="Checklist item…"
									class="flex-1"
								/>
								<button
									type="button"
									class="text-xs px-2 py-1 border border-ink-200 bg-white hover:bg-ink-50"
									style="border-radius: 2px; color: #b91c1c"
									@click="removeChecklistRow(i)"
									title="Remove row"
								>
									✕
								</button>
							</li>
						</ol>
						<button
							type="button"
							class="mt-2 text-xs px-2 py-1 border border-ink-200 bg-white hover:bg-ink-50"
							style="border-radius: 2px"
							@click="addChecklistRow"
						>
							+ Add row
						</button>
					</div>
				</div>
			</DeskSection>

			<!-- Applicable project types -->
			<DeskSection title="Applicable project types">
				<div class="md:col-span-2">
					<div v-if="!editing" class="flex flex-wrap gap-1.5">
						<span
							v-for="t in activityType.applicableProjectTypes || []"
							:key="t"
							class="text-[11px] px-2 py-0.5 bg-brand-50 text-brand-700 font-medium"
							style="border-radius: 2px"
							>{{ t }}</span
						>
						<span
							v-if="
								!(
									activityType.applicableProjectTypes &&
									activityType.applicableProjectTypes.length
								)
							"
							class="text-xs text-ink-400 italic"
							>Universal · applies to all project types</span
						>
					</div>
					<div v-else>
						<div class="flex flex-wrap gap-2">
							<label
								v-for="t in PROJECT_TYPES"
								:key="t"
								class="inline-flex items-center gap-1.5 text-xs text-ink-800 cursor-pointer px-2 py-1 border border-ink-200 hover:bg-ink-50"
								style="border-radius: 2px"
							>
								<input
									type="checkbox"
									:checked="(form.applicableProjectTypes || []).includes(t)"
									class="accent-brand-600"
									@change="toggleProjectType(t)"
								/>
								{{ t }}
							</label>
						</div>
						<div class="text-[11px] text-ink-500 mt-1.5">
							Leave all unchecked to mark as universal (applies to every project
							type).
						</div>
					</div>
				</div>
			</DeskSection>

			<!-- Footer stub -->
			<section class="mt-8 pt-4 border-t border-ink-200">
				<div class="flex items-center gap-6 text-xs text-ink-500 flex-wrap">
					<div class="flex items-center gap-1.5">
						<span>🔗</span>
						<span
							>Linked tasks —
							<span class="font-medium text-ink-700">{{
								linkedTaskCount
							}}</span></span
						>
					</div>
					<div class="flex items-center gap-1.5">
						<span>💬</span>
						<span>Comments — <span class="font-medium text-ink-700">0</span></span>
						<span class="text-ink-400 italic ml-1">stub</span>
					</div>
				</div>
			</section>
		</DeskForm>
	</DeskPage>

	<div v-else class="px-6 py-20 text-center text-sm text-ink-400">
		Activity Type not found ·
		<RouterLink to="/activity-types" class="desk-link">Back to list →</RouterLink>
	</div>
</template>
