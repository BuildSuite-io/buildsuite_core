<script setup>
// Project Template editor — edits the default Work Packages, Stages and Tasks a
// project inherits when it's created under this Project Category. Each task is a
// template-type task assigned to a Work Package and a Stage, so importing a
// project seeds those tasks into the matching stage plans. Admin / BSA only.

import { reactive, ref, computed, onMounted } from "vue";
import { useRouter } from "vue-router";
import { useDataStore } from "@/stores";
import { showToast } from "@/utils/appToast";
import { getProjectTemplate, saveProjectTemplate } from "@/utils/projectTemplateApi";
import DeskPage from "@/components/desk/DeskPage.vue";
import DeskForm from "@/components/desk/DeskForm.vue";
import DeskActionBar from "@/components/desk/DeskActionBar.vue";
import DeskSection from "@/components/desk/DeskSection.vue";
import DeskInput from "@/components/desk/DeskInput.vue";
import DeskSelect from "@/components/desk/DeskSelect.vue";

const props = defineProps({ id: { type: String, required: true } });
const router = useRouter();
const store = useDataStore();

const PRIORITIES = ["Low", "Medium", "High", "Urgent"];

const workPackages = reactive([]);
const stages = reactive([]);
const tasks = reactive([]);
const saving = ref(false);
const loading = ref(true);

const wpCodes = computed(() => workPackages.map((w) => w.code).filter(Boolean));
const stageNames = computed(() => stages.map((s) => s.stage_name).filter(Boolean));

function addWorkPackage() {
	workPackages.push({
		code: "",
		work_package_name: "",
		budget: 0,
		sort_order: workPackages.length + 1,
		description: "",
	});
}
function addStage() {
	stages.push({
		stage_name: "",
		offset_start_days: 0,
		offset_end_days: 0,
		planned_task_count: 0,
		planned_completion_pct: 100,
		description: "",
	});
}
function addTask() {
	tasks.push({
		subject: "",
		priority: "Medium",
		hours: 0,
		work_package_code: wpCodes.value[0] || "",
		stage: stageNames.value[0] || "",
	});
}
function removeRow(list, i) {
	list.splice(i, 1);
}

async function load() {
	loading.value = true;
	try {
		const data = await getProjectTemplate(props.id);
		workPackages.splice(0, workPackages.length, ...(data?.work_packages || []));
		stages.splice(0, stages.length, ...(data?.stages || []));
		tasks.splice(0, tasks.length, ...(data?.tasks || []));
	} catch (err) {
		showToast(err.message || "Failed to load template", "error");
	} finally {
		loading.value = false;
	}
}

async function save() {
	if (saving.value) return;
	// A task must point at a stage/WP that still exists in the lists above.
	const badTask = tasks.find(
		(t) =>
			!t.subject.trim() ||
			(t.stage && !stageNames.value.includes(t.stage)) ||
			(t.work_package_code && !wpCodes.value.includes(t.work_package_code)),
	);
	if (badTask) {
		showToast("Each task needs a subject and a valid Work Package / Stage.", "error");
		return;
	}
	saving.value = true;
	try {
		const data = await saveProjectTemplate(props.id, {
			workPackages: workPackages.map((w, i) => ({
				...w,
				sort_order: w.sort_order || i + 1,
			})),
			stages,
			tasks,
		});
		workPackages.splice(0, workPackages.length, ...(data?.work_packages || []));
		stages.splice(0, stages.length, ...(data?.stages || []));
		tasks.splice(0, tasks.length, ...(data?.tasks || []));
		showToast("Template saved");
	} catch (err) {
		showToast(err.message || "Failed to save template", "error");
	} finally {
		saving.value = false;
	}
}
function cancel() {
	router.push(`/settings/project-categories/${props.id}`);
}

const breadcrumbs = computed(() => [
	{ label: "BuildSuite Core", to: "/" },
	{ label: "Settings", to: "/settings" },
	{ label: "Project Categories", to: "/settings/project-categories" },
	{ label: props.id, to: `/settings/project-categories/${props.id}` },
	{ label: "Template" },
]);

onMounted(() => {
	if (!store.isAdmin && !store.isBSA) {
		router.replace("/settings");
		return;
	}
	load();
});
</script>

<template>
	<DeskPage
		:title="`${props.id} template`"
		subtitle="Defaults imported when a project is created under this category"
		:breadcrumbs="breadcrumbs"
	>
		<DeskForm>
			<template #action-bar>
				<DeskActionBar
					:save-label="saving ? 'Saving…' : 'Save template'"
					:saving="saving"
					@save="save"
					@cancel="cancel"
				/>
			</template>

			<div v-if="loading" class="py-12 text-center text-sm text-ink-500">
				Loading template…
			</div>

			<div v-else class="space-y-6">
				<!-- Work Packages -->
				<DeskSection title="Work Packages" :cols="1">
					<div class="overflow-x-auto">
						<table class="w-full text-sm">
							<thead>
								<tr class="text-left text-ink-500 border-b border-ink-100">
									<th class="py-1.5 pr-2 font-medium">Code</th>
									<th class="py-1.5 pr-2 font-medium">Name</th>
									<th class="py-1.5 pr-2 font-medium w-32">Budget</th>
									<th class="py-1.5 pr-2 font-medium w-16">Sort</th>
									<th class="w-8"></th>
								</tr>
							</thead>
							<tbody>
								<tr
									v-for="(w, i) in workPackages"
									:key="i"
									class="border-b border-ink-50"
								>
									<td class="py-1 pr-2">
										<DeskInput v-model="w.code" placeholder="WP-XXX" />
									</td>
									<td class="py-1 pr-2">
										<DeskInput v-model="w.work_package_name" />
									</td>
									<td class="py-1 pr-2">
										<DeskInput v-model="w.budget" type="number" min="0" />
									</td>
									<td class="py-1 pr-2">
										<DeskInput v-model="w.sort_order" type="number" min="0" />
									</td>
									<td class="py-1 text-center">
										<button
											class="text-ink-400 hover:text-danger-600"
											@click="removeRow(workPackages, i)"
										>
											×
										</button>
									</td>
								</tr>
								<tr v-if="!workPackages.length">
									<td colspan="5" class="py-3 text-center text-ink-400">
										No work packages yet.
									</td>
								</tr>
							</tbody>
						</table>
					</div>
					<button
						class="mt-2 text-sm text-brand-600 hover:underline"
						@click="addWorkPackage"
					>
						+ Add work package
					</button>
				</DeskSection>

				<!-- Stages -->
				<DeskSection title="Stages" :cols="1">
					<div class="overflow-x-auto">
						<table class="w-full text-sm">
							<thead>
								<tr class="text-left text-ink-500 border-b border-ink-100">
									<th class="py-1.5 pr-2 font-medium">Stage name</th>
									<th class="py-1.5 pr-2 font-medium w-24">Start (day)</th>
									<th class="py-1.5 pr-2 font-medium w-24">End (day)</th>
									<th class="py-1.5 pr-2 font-medium w-28">Planned tasks</th>
									<th class="w-8"></th>
								</tr>
							</thead>
							<tbody>
								<tr
									v-for="(s, i) in stages"
									:key="i"
									class="border-b border-ink-50"
								>
									<td class="py-1 pr-2"><DeskInput v-model="s.stage_name" /></td>
									<td class="py-1 pr-2">
										<DeskInput
											v-model="s.offset_start_days"
											type="number"
											min="0"
										/>
									</td>
									<td class="py-1 pr-2">
										<DeskInput
											v-model="s.offset_end_days"
											type="number"
											min="0"
										/>
									</td>
									<td class="py-1 pr-2">
										<DeskInput
											v-model="s.planned_task_count"
											type="number"
											min="0"
										/>
									</td>
									<td class="py-1 text-center">
										<button
											class="text-ink-400 hover:text-danger-600"
											@click="removeRow(stages, i)"
										>
											×
										</button>
									</td>
								</tr>
								<tr v-if="!stages.length">
									<td colspan="5" class="py-3 text-center text-ink-400">
										No stages yet.
									</td>
								</tr>
							</tbody>
						</table>
					</div>
					<button class="mt-2 text-sm text-brand-600 hover:underline" @click="addStage">
						+ Add stage
					</button>
				</DeskSection>

				<!-- Tasks -->
				<DeskSection title="Tasks" :cols="1">
					<p class="text-sm text-ink-500 -mt-1">
						Each task is assigned to a Work Package and a Stage. On import it becomes a
						project task and lands in that stage's plan.
					</p>
					<div class="overflow-x-auto">
						<table class="w-full text-sm">
							<thead>
								<tr class="text-left text-ink-500 border-b border-ink-100">
									<th class="py-1.5 pr-2 font-medium">Subject</th>
									<th class="py-1.5 pr-2 font-medium w-28">Priority</th>
									<th class="py-1.5 pr-2 font-medium w-24">Hours</th>
									<th class="py-1.5 pr-2 font-medium w-40">Work Package</th>
									<th class="py-1.5 pr-2 font-medium w-40">Stage</th>
									<th class="w-8"></th>
								</tr>
							</thead>
							<tbody>
								<tr
									v-for="(t, i) in tasks"
									:key="i"
									class="border-b border-ink-50"
								>
									<td class="py-1 pr-2"><DeskInput v-model="t.subject" /></td>
									<td class="py-1 pr-2">
										<DeskSelect v-model="t.priority">
											<option v-for="p in PRIORITIES" :key="p" :value="p">
												{{ p }}
											</option>
										</DeskSelect>
									</td>
									<td class="py-1 pr-2">
										<DeskInput v-model="t.hours" type="number" min="0" />
									</td>
									<td class="py-1 pr-2">
										<DeskSelect v-model="t.work_package_code">
											<option value="">—</option>
											<option v-for="c in wpCodes" :key="c" :value="c">
												{{ c }}
											</option>
										</DeskSelect>
									</td>
									<td class="py-1 pr-2">
										<DeskSelect v-model="t.stage">
											<option value="">—</option>
											<option v-for="n in stageNames" :key="n" :value="n">
												{{ n }}
											</option>
										</DeskSelect>
									</td>
									<td class="py-1 text-center">
										<button
											class="text-ink-400 hover:text-danger-600"
											@click="removeRow(tasks, i)"
										>
											×
										</button>
									</td>
								</tr>
								<tr v-if="!tasks.length">
									<td colspan="6" class="py-3 text-center text-ink-400">
										No tasks yet.
									</td>
								</tr>
							</tbody>
						</table>
					</div>
					<button
						class="mt-2 text-sm text-brand-600 hover:underline disabled:opacity-40 disabled:no-underline"
						:disabled="!stageNames.length && !wpCodes.length"
						@click="addTask"
					>
						+ Add task
					</button>
				</DeskSection>
			</div>
		</DeskForm>
	</DeskPage>
</template>
