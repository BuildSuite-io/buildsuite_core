<script setup>
// New Stage Planning — 2-step wizard, Desk-styled (CLAUDE.md §12.4).
//
// STEP 1 — Stage details: name, project (locked via ?projectId=), planned
//   start/end, description, dependencies (sibling stages multi-select; surfaces only after project).
// STEP 2 — Add tasks: embedded <StageTaskPicker mode="embedded"> for picking
//   the tasks that belong in the stage.

import { reactive, ref, computed, watch, nextTick } from "vue";
import { useRouter, useRoute } from "vue-router";
import { useDataStore } from "@/stores";
import { showToast } from "@/utils/appToast";
import { useFormErrors } from "@/composables/useFormErrors";
import { usePermissions } from "@/composables/usePermissions";
import { createDataAdapter } from "@/data/adapters";
import DeskPage from "@/components/desk/DeskPage.vue";
import DeskForm from "@/components/desk/DeskForm.vue";
import DeskActionBar from "@/components/desk/DeskActionBar.vue";
import DeskSection from "@/components/desk/DeskSection.vue";
import DeskField from "@/components/desk/DeskField.vue";
import DeskInput from "@/components/desk/DeskInput.vue";
import DeskTextarea from "@/components/desk/DeskTextarea.vue";
import DeskLinkPicker from "@/components/desk/DeskLinkPicker.vue";
import StageTaskPicker from "@/components/StageTaskPicker.vue";

const router = useRouter();
const route = useRoute();
const store = useDataStore();
const { canCreate } = usePermissions();
const adapter = createDataAdapter(store);

const form = reactive({
	stageName: "",
	project: route.query.projectId || "",
	plannedStart: "",
	plannedEnd: "",
	description: "",
	dependencies: [],
});

const { errors, applyServerErrors, setErrors, clearError } = useFormErrors({
	stage_name: "stageName",
	project: "project",
	planned_start: "plannedStart",
	planned_end: "plannedEnd",
	description: "description",
});

const saving = ref(false);
const lockedProject = computed(() => !!route.query.projectId);

// Wizard step — 1 (details) or 2 (tasks).
const step = ref(1);

// Picker ref so we can grab the current selection at save time.
const pickerRef = ref(null);

function toArray(data) {
	if (Array.isArray(data)) return data;
	if (Array.isArray(data?.value)) return data.value;
	return [];
}

const stagesResource = ref(null);

watch(
	() => form.project,
	(newProject, oldProject) => {
		if (newProject !== oldProject) {
			form.dependencies = [];
			clearError("project");
		}
		if (!newProject) {
			stagesResource.value = null;
			return;
		}
		stagesResource.value = adapter.list("Stage Planning", {
			fields: ["name", "stage_name", "project"],
			filters: [["project", "=", newProject]],
			pageLength: 100,
			cache: `buildsuite-project-stages:${newProject}`,
			transform(rows) {
				return rows.map((r) => ({
					id: r.name,
					stageName: r.stage_name,
					project: r.project,
				}));
			},
		});
	},
	{ immediate: true }
);

// Sibling stages = existing stages on the same project, eligible as dependencies.
const siblingStages = computed(() => toArray(stagesResource.value?.data));

function toggleDependency(id) {
	const i = form.dependencies.indexOf(id);
	if (i === -1) form.dependencies.push(id);
	else form.dependencies.splice(i, 1);
}

function validate() {
	const e = {};
	if (!form.stageName.trim()) e.stageName = "Stage name is required";
	if (!form.project) e.project = "Project is required";
	if (form.plannedEnd && form.plannedStart && form.plannedEnd < form.plannedStart) {
		e.plannedEnd = "End must be on or after start";
	}
	setErrors(e);
	return Object.keys(e).length === 0;
}

function goToStep2() {
	if (!validate()) return;
	step.value = 2;
}

function goBackToStep1() {
	step.value = 1;
}

async function save() {
	if (!validate()) {
		step.value = 1;
		return;
	}
	saving.value = true;
	try {
		const pickerPayload = pickerRef.value ? pickerRef.value.getCurrentSelection() : null;
		const childRows = (pickerPayload?.newChildRows || []).map((r) => ({
			task: r.task,
			planned_start: r.plannedStart || null,
			planned_end: r.plannedEnd || null,
			planned_qty: Number(r.plannedQty) || 0,
			qty_unit: r.qtyUnit || "%",
		}));

		const res = await adapter.create("Stage Planning", {
			stage_name: form.stageName.trim(),
			project: form.project,
			planned_start: form.plannedStart || null,
			planned_end: form.plannedEnd || null,
			planned_task_count: childRows.length,
			planned_completion_pct: 100,
			description: form.description,
			dependencies: form.dependencies.map((dep) => ({ stage: dep })),
			stage_planning_tasks: childRows,
		});

		const createdStageId =
			res?.name ||
			res?.id ||
			res?.message?.name ||
			res?.message?.id ||
			res?.data?.name ||
			res?.data?.id ||
			"";

		if (!createdStageId) {
			showToast("Stage created, but could not resolve its ID for navigation", "error");
			await router.push("/stage-plannings");
			return;
		}

		await router.push(`/stage-plannings/${createdStageId}`);
		await nextTick();
		showToast("Stage created");
	} catch (err) {
		showToast(applyServerErrors(err) ?? "Failed to create stage", "error");
	} finally {
		saving.value = false;
	}
}

function cancel() {
	router.back();
}

const breadcrumbs = [
	{ label: "BuildSuite Core", to: "/" },
	{ label: "Stage Planning", to: "/stage-plannings" },
	{ label: "New" },
];
</script>

<template>
	<DeskPage title="New Stage" :breadcrumbs="breadcrumbs">
		<div
			v-if="!canCreate('stagePlanning')"
			class="px-3 py-2 bg-warning-50 border border-warning-100 text-xs text-warning-700 dark:bg-ink-800 dark:border-ink-700"
			style="border-radius: 6px"
		>
			You don't have permission to create a stage.
		</div>
		<template v-else>
			<!-- Step indicator — bone-simple breadcrumb-style pills. -->
			<div class="px-5 pt-4 pb-2 flex items-center gap-2 text-xs">
				<span
					class="inline-flex items-center gap-1.5 px-2.5 py-1"
					:class="
						step === 1
							? 'bg-brand-700 text-white font-medium'
							: 'bg-ink-100 text-ink-600'
					"
					style="border-radius: 9999px"
				>
					<span class="tabular-nums">1.</span>
					<span>Details</span>
				</span>
				<span class="text-ink-400">›</span>
				<span
					class="inline-flex items-center gap-1.5 px-2.5 py-1"
					:class="
						step === 2
							? 'bg-brand-700 text-white font-medium'
							: 'bg-ink-100 text-ink-600'
					"
					style="border-radius: 9999px"
				>
					<span class="tabular-nums">2.</span>
					<span>Tasks</span>
				</span>
			</div>

			<!-- ============ STEP 1 — Stage details ============================== -->
			<DeskForm v-if="step === 1">
				<template #action-bar>
					<DeskActionBar
						save-label="Next: Add Tasks"
						@save="goToStep2"
						@cancel="cancel"
					/>
				</template>

				<!-- Full-width Layout -->
				<div class="pb-12">
					<DeskSection title="Stage details" :cols="1">
						<DeskField label="Stage name" required :error="errors.stageName">
							<DeskInput
								v-model="form.stageName"
								data-test="field-stage-name"
								placeholder="e.g. Substructure Stage"
							/>
						</DeskField>
						<DeskField
							label="Project"
							required
							:error="errors.project"
							:hint="lockedProject ? 'Pre-selected — locked.' : ''"
						>
							<DeskLinkPicker
								v-model="form.project"
								data-test="pick-project"
								doctype="Project"
								label-field="project_name"
								value-field="name"
								:search-fields="['project_name', 'custom_project_id', 'name']"
								:filters="[['is_group', '=', 1]]"
								:page-length="20"
								placeholder="— Select project —"
								:disabled="lockedProject"
								:error="errors.project"
							/>
						</DeskField>
					</DeskSection>

					<DeskSection title="Schedule" :cols="2">
						<DeskField label="Planned start">
							<DeskInput v-model="form.plannedStart" type="date" />
						</DeskField>
						<DeskField label="Planned end" :error="errors.plannedEnd">
							<DeskInput v-model="form.plannedEnd" type="date" />
						</DeskField>
					</DeskSection>

					<DeskSection title="Description" :cols="1">
						<DeskField label="Description">
							<DeskTextarea
								v-model="form.description"
								:rows="3"
								placeholder="Scope, gates, hand-off notes…"
							/>
						</DeskField>
					</DeskSection>

					<DeskSection title="Dependencies" v-if="form.project" :cols="1">
						<div class="md:col-span-1">
							<div v-if="siblingStages.length" class="flex flex-wrap gap-2">
								<label
									v-for="sib in siblingStages"
									:key="sib.id"
									class="inline-flex items-center gap-1.5 text-xs text-ink-800 cursor-pointer px-2 py-1 border border-ink-200 hover:bg-ink-50 dark:border-ink-700"
									style="border-radius: 2px"
								>
									<input
										type="checkbox"
										:checked="form.dependencies.includes(sib.id)"
										class="accent-brand-600"
										@change="toggleDependency(sib.id)"
									/>
									<span class="font-mono text-[10px] text-ink-500">{{
										sib.id
									}}</span>
									<span>{{ sib.stageName }}</span>
								</label>
							</div>
							<div v-else class="text-xs text-ink-400 italic">
								No other stages on this project yet · create them first, then come
								back to wire dependencies.
							</div>
							<div class="text-[11px] text-ink-500 mt-1.5">
								Optional · pick stages that must complete before this one can
								start.
							</div>
						</div>
					</DeskSection>
				</div>
			</DeskForm>

			<!-- ============ STEP 2 — Add tasks ================================== -->
			<DeskForm v-else>
				<template #action-bar>
					<DeskActionBar
						save-label="Create Stage"
						:saving="saving"
						saving-label="Creating stage…"
						@save="save"
						@cancel="cancel"
					>
						<template #left>
							<button
								type="button"
								class="text-xs px-3 py-1.5 border border-ink-200 bg-white hover:bg-ink-50 text-ink-700 dark:bg-ink-800 dark:border-ink-700 dark:text-ink-150 dark:hover:bg-ink-700"
								style="border-radius: 6px"
								@click="goBackToStep1"
							>
								← Back
							</button>
						</template>
					</DeskActionBar>
				</template>

				<!-- Full-width Layout -->
				<div class="px-5 pt-2 pb-12">
					<StageTaskPicker
						ref="pickerRef"
						mode="embedded"
						:project-id="form.project"
						:stage-name="form.stageName"
						:planned-start="form.plannedStart"
						:planned-end="form.plannedEnd"
					/>
				</div>
			</DeskForm>
		</template>
	</DeskPage>
</template>
