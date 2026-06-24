<script setup>
// New Project — Desk-styled (CLAUDE.md §12.4). Behavior preserved exactly: same
// validate() rules, same store.addProject call, parentId pre-fill from the route
// query for the "+ Add Subproject" entry point.

import { reactive, ref, computed, watch } from "vue";
import { useRouter, useRoute } from "vue-router";
import { useDataStore } from "@/stores";
import { showToast } from "@/utils/appToast";
import { useFormErrors } from "@/composables/useFormErrors";
import { usePermissions } from "@/composables/usePermissions";
import { createDataAdapter } from "@/data/adapters";
import { endBeforeStartError, outOfParentBoundsError } from "@/utils/dateBounds";
import { fetchProjectBounds } from "@/utils/projectBounds";
import DeskPage from "@/components/desk/DeskPage.vue";
import DeskForm from "@/components/desk/DeskForm.vue";
import DeskActionBar from "@/components/desk/DeskActionBar.vue";
import DeskSection from "@/components/desk/DeskSection.vue";
import DeskField from "@/components/desk/DeskField.vue";
import DeskInput from "@/components/desk/DeskInput.vue";
import DeskSelect from "@/components/desk/DeskSelect.vue";
import DeskTextarea from "@/components/desk/DeskTextarea.vue";
import DeskLinkPicker from "@/components/desk/DeskLinkPicker.vue";
import CustomerCreateModal from "@/components/CustomerCreateModal.vue";

const router = useRouter();
const route = useRoute();
const store = useDataStore();
const { canCreate } = usePermissions();
const adapter = createDataAdapter(store);

// Inline customer create from the Client picker. customerPickerKey is bumped on
// create so the DeskLinkPicker re-instantiates and can resolve the new value.
const customerModalOpen = ref(false);
const customerPickerKey = ref(0);
function onCustomerCreated(name) {
	form.client = name;
	clearError("client");
	customerPickerKey.value++;
}

function firstResourceRow(resource) {
	if (resource?.doc) return resource.doc;
	const raw = resource?.data;
	if (Array.isArray(raw)) return raw[0] || null;
	if (Array.isArray(raw?.value)) return raw.value[0] || null;
	if (raw && typeof raw === "object" && "value" in raw) return raw.value || null;
	return raw || null;
}

// §14 — company is NOT collected on this form. It's inferred server-side from the
// creating user's company (top-level) or the parent project (subproject), and is
// only displayed read-only on the Project detail view. The parent is still fetched
// from the backend for the breadcrumb / subtitle / subproject template note (the
// local Pinia store is empty in remote mode).
const parentId = route.query.parentId || null;
const parentResource = parentId
	? adapter.read("Project", parentId, {
			nameField: "name",
			fields: ["name", "project_name"],
			cache: `buildsuite-new-project-parent:${parentId}`,
			transform: (rows) =>
				rows.map((r) => ({
					id: r?.name,
					name: r?.project_name || r?.name || "",
				})),
	  })
	: null;
const fetchedParent = computed(() => firstResourceRow(parentResource));

const form = reactive({
	code: "",
	name: "",
	client: "",
	company: "",
	status: "New",
	priority: "Medium",
	type: "",
	startDate: new Date().toISOString().slice(0, 10),
	endDate: "",
	budget: "",
	pm: "",
	location: "",
	description: "",
	parentId: route.query.parentId || null,
	// Group project by default. Turning this off makes the project a child
	// record under a selected parent (is_group = 0).
	allowSubprojects: !route.query.parentId,
	// Seed stages from the matching BuildSuite Project Template on create.
	// Default ON for top-level projects, OFF for subprojects.
	seedDefaultStages: !route.query.parentId,
	// Import project-level tasks from the template. Off by default; disabled
	// entirely for subprojects since the parent owns the breakdown.
	seedDefaultTasks: false,
});
const { errors, applyServerErrors, setErrors, clearError } = useFormErrors({
	project_name: "name",
	custom_project_id: "code",
	customer: "client",
	company: "company",
	project_type: "type",
	expected_end_date: "endDate",
	expected_start_date: "startDate",
	project_manager: "pm",
});
const saving = ref(false);

// §14 — Company is chosen once, on create. Default to the site's default company.
// Subprojects inherit the parent's company, so the field is hidden for them and
// the value isn't sent. Company is locked after create. Uses a BuildSuite helper
// rather than get_value on the Global Defaults Single (which 403s for non-admins).
async function loadDefaultCompany() {
	if (route.query.parentId) return; // subproject — inherits parent's company
	try {
		const res = await fetch("/api/method/buildsuite_core.api.company.get_default_company", {
			credentials: "include",
			headers: { "X-Frappe-CSRF-Token": window.csrf_token || "" },
		});
		const data = await res.json();
		form.company = data?.message || "";
	} catch (err) {
		console.warn("[NewProjectView] Failed to load default company", err);
	}
}
loadDefaultCompany();

const parentProject = computed(
	() => fetchedParent.value || (form.parentId ? store.projectById(form.parentId) : null)
);

// The "Allow subprojects" toggle only controls is_group on a top-level project —
// it no longer touches parentId (subprojects come solely from the ?parentId=
// route) nor template seeding (the user controls that via the preview checkbox).

// Template preview — fetches the matching BuildSuite Project Template for the
// selected Project Type. Since Stage Plan Template is autonamed by stage_name,
// each stage_plans row's `stage_plan` field value IS the stage name.
const templateLoading = ref(false);
// Summary from the backend: { exists, stage_names, stage_count, task_count }.
// task_count is the TOTAL — project-level tasks PLUS tasks nested in every
// stage plan — which is exactly what "Import default tasks" seeds.
const templateSummary = ref(null);

const templateStageNames = computed(() => templateSummary.value?.stage_names || []);
const templateTaskCount = computed(() => templateSummary.value?.task_count || 0);

async function loadTemplateForType(projectType) {
	templateSummary.value = null;
	if (!projectType) return;
	templateLoading.value = true;
	try {
		const res = await fetch(
			"/api/method/buildsuite_core.utils.project.get_project_template_summary?" +
				new URLSearchParams({ project_type: projectType }),
			{ credentials: "include", headers: { "X-Frappe-CSRF-Token": window.csrf_token || "" } }
		);
		const data = await res.json();
		const summary = data?.message || null;
		templateSummary.value = summary && summary.exists ? summary : null;
	} catch (err) {
		console.warn(
			"[NewProjectView] Failed to load template summary for type",
			projectType,
			err
		);
	} finally {
		templateLoading.value = false;
	}
}

watch(
	() => form.type,
	(type) => loadTemplateForType(type)
);

function validate() {
	const e = {};
	if (!form.name) e.name = "Project name is required";
	if (!form.code) e.code = "Project ID is required";
	const endErr = endBeforeStartError(form.startDate, form.endDate);
	if (endErr) e.endDate = endErr;
	setErrors(e);
	return Object.keys(e).length === 0;
}

async function save() {
	if (!validate()) return;
	if (form.parentId) {
		const b = await fetchProjectBounds(form.parentId);
		const boundsErr = outOfParentBoundsError(
			form.startDate,
			form.endDate,
			b.start,
			b.end,
			"parent project"
		);
		if (boundsErr) {
			setErrors(
				boundsErr.startsWith("Start") ? { startDate: boundsErr } : { endDate: boundsErr }
			);
			return;
		}
	}
	saving.value = true;
	try {
		const res = await adapter.create("Project", {
			project_name: form.name,
			custom_project_id: form.code,
			// parent_project only ever comes from the ?parentId= route (the "+ Add
			// Subproject" entry on a parent). A subproject is always a leaf (is_group=0);
			// a top-level project is a group iff "Allow subprojects" is on.
			parent_project: form.parentId || null,
			is_group: form.parentId ? 0 : form.allowSubprojects ? 1 : 0,
			project_status: form.status,
			priority: form.priority,
			location: form.location || null,
			// Company is chosen on the form for top-level projects; subprojects omit it
			// and inherit the parent's company server-side (enforce_company_rules).
			company: form.parentId ? null : form.company || null,
			expected_start_date: form.startDate,
			expected_end_date: form.endDate,
			customer: form.client,
			project_type: form.type,
			estimated_costing: Number(form.budget),
			project_manager: form.pm || null,
			notes: form.description,
			custom_seed_default_stages: form.seedDefaultStages ? 1 : 0,
			custom_seed_default_tasks: form.seedDefaultTasks ? 1 : 0,
		});
		showToast("Project created");
		router.push(`/projects/${res.name}`);
	} catch (err) {
		showToast(applyServerErrors(err) ?? "Failed to create project", "error");
	} finally {
		saving.value = false;
	}
}
function cancel() {
	router.back();
}

const subtitle = computed(() =>
	parentProject.value ? `Subproject under ${parentProject.value.name}` : "Top-level project"
);

const breadcrumbs = computed(() => {
	const out = [
		{ label: "BuildSuite Core", to: "/" },
		{ label: "Project", to: "/projects" },
	];
	if (parentProject.value)
		out.push({ label: parentProject.value.name, to: `/projects/${parentProject.value.id}` });
	out.push({ label: "New" });
	return out;
});
</script>

<template>
	<DeskPage title="New Project" :subtitle="subtitle" :breadcrumbs="breadcrumbs">
		<div
			v-if="!canCreate('project')"
			class="px-3 py-2 bg-warning-50 border border-warning-100 text-xs text-warning-700 dark:bg-ink-800 dark:border-ink-700"
			style="border-radius: 6px"
		>
			You don't have permission to create a project.
		</div>
		<DeskForm v-else>
			<template #action-bar>
				<DeskActionBar
					:save-label="saving ? 'Creating…' : 'Create project'"
					:saving="saving"
					@save="save"
					@cancel="cancel"
				/>
			</template>

			<!-- Narrow centered column so the form doesn't feel sprawling. Save bar
           above stays full-width (matches Frappe Desk's form layout). Same
           pattern as NewTaskView and NewTaskProgressEntryView. -->
			<div class="max-w-3xl mx-auto">
				<DeskSection title="Basic information">
					<DeskField label="Project name" required :error="errors.name">
						<DeskInput
							v-model="form.name"
							data-test="field-name"
							placeholder="e.g. Bangalore Tech Park Phase 2"
						/>
					</DeskField>
					<DeskField
						label="Project ID"
						required
						:error="errors.code"
						hint="Short unique identifier — used as a code in lists and URLs."
					>
						<DeskInput
							v-model="form.code"
							data-test="field-code"
							placeholder="e.g. BTP-P2"
						/>
					</DeskField>
					<!-- Session 40: Client is now a Link field onto the Customer master
             (ERPNext-native Customer DocType). The stored value is the
             customer's `name` so existing project records (whose client was
             plain text) still resolve. -->
					<DeskField
						label="Client"
						:error="errors.client"
						:hint="errors.client ? '' : 'Pick a customer, or create one inline.'"
					>
						<div class="flex items-center gap-2">
							<div class="flex-1 min-w-0">
								<DeskLinkPicker
									:key="customerPickerKey"
									v-model="form.client"
									data-test="pick-customer"
									doctype="Customer"
									placeholder="Select customer"
									label-field="customer_name"
									value-field="name"
									:search-fields="['customer_name', 'name']"
									order-by="modified desc"
									:page-length="20"
									:error="errors.client"
									@change="clearError('client')"
								/>
							</div>
							<button
								type="button"
								class="text-xs px-2.5 py-1 border border-ink-200 bg-white hover:bg-ink-50 text-ink-700 whitespace-nowrap"
								style="border-radius: 6px"
								@click="customerModalOpen = true"
							>
								+ New
							</button>
						</div>
					</DeskField>
					<DeskField label="Project type" :error="errors.type">
						<DeskLinkPicker
							v-model="form.type"
							data-test="pick-project-type"
							doctype="Project Type"
							placeholder="Select project type"
							label-field="name"
							value-field="name"
							:search-fields="['name']"
							order-by="modified desc"
							:page-length="20"
							:error="errors.type"
							@change="clearError('type')"
						/>
						<!-- Template preview: fetched from BuildSuite Project Template where
               project_type matches the selected type. Reacts as type changes. -->
						<div
							v-if="templateLoading"
							class="mt-1.5 px-2 py-1.5 bg-ink-50 border border-ink-200 text-[11px] text-ink-500 italic"
							style="border-radius: 6px"
						>
							Loading template…
						</div>
						<div
							v-else-if="templateSummary"
							class="mt-1.5 px-2 py-1.5 bg-ink-50 border border-ink-200 text-[11px] text-ink-700 space-y-1.5"
							style="border-radius: 6px"
						>
							<div class="flex items-center justify-between gap-2 flex-wrap">
								<div>
									Template seeds
									<span class="font-medium text-ink-900"
										>{{ templateStageNames.length }} default stages</span
									>:
									<span class="text-ink-600">{{
										templateStageNames.join(" → ")
									}}</span>
								</div>
								<label
									class="inline-flex items-center gap-1.5 cursor-pointer whitespace-nowrap"
								>
									<input
										type="checkbox"
										v-model="form.seedDefaultStages"
										class="accent-brand-600"
									/>
									<span class="text-ink-700">Seed default stages</span>
								</label>
							</div>
							<div
								v-if="!parentProject && templateTaskCount > 0"
								class="flex items-center justify-between gap-2 flex-wrap pt-1.5 border-t border-ink-100"
							>
								<div>
									<span class="font-medium text-ink-900"
										>{{ templateTaskCount }} tasks</span
									>
									from this template can also be imported.
								</div>
								<label
									class="inline-flex items-center gap-1.5 cursor-pointer whitespace-nowrap"
								>
									<input
										type="checkbox"
										v-model="form.seedDefaultTasks"
										class="accent-brand-600"
									/>
									<span class="text-ink-700">Import default tasks</span>
								</label>
							</div>
							<div v-if="parentProject" class="text-[10px] text-ink-500 italic">
								Subproject — stage and task defaults are off; the parent project
								owns the timeline.
							</div>
						</div>
						<div
							v-else-if="form.type"
							class="mt-1.5 px-2 py-1.5 bg-ink-50 border border-ink-200 text-[11px] text-ink-500 italic"
							style="border-radius: 6px"
						>
							No template configured for
							<span class="font-medium text-ink-700">{{ form.type }}</span
							>. You'll plan stages manually after create.
						</div>
					</DeskField>
					<!-- §14 — Company is chosen once on create (defaults to the site's default
             company). Hidden for subprojects, which inherit the parent's company.
             Locked after create (enforced server-side). -->
					<DeskField
						v-if="!route.query.parentId"
						label="Company"
						:error="errors.company"
						:hint="
							errors.company
								? ''
								: 'Defaults to your default company. This is locked after the project is created.'
						"
					>
						<DeskLinkPicker
							v-model="form.company"
							data-test="pick-company"
							doctype="Company"
							placeholder="Select company"
							label-field="company_name"
							value-field="name"
							:search-fields="['company_name', 'abbr', 'name']"
							order-by="company_name asc"
							:page-length="20"
							:error="errors.company"
							@change="clearError('company')"
						/>
					</DeskField>
					<DeskField label="Location">
						<DeskInput v-model="form.location" placeholder="Site address" />
					</DeskField>
					<DeskField label="Description">
						<DeskTextarea
							v-model="form.description"
							:rows="3"
							placeholder="Brief description of project scope"
						/>
					</DeskField>
					<DeskField
						v-if="!route.query.parentId"
						label="Subprojects"
						hint="Turn on to break this project into subprojects (e.g. Block A / Block B / Tower 1)."
					>
						<label class="inline-flex items-center gap-2 cursor-pointer select-none">
							<input
								type="checkbox"
								v-model="form.allowSubprojects"
								class="accent-brand-600"
							/>
							<span class="text-sm text-ink-700"
								>Allow subprojects under this project</span
							>
						</label>
					</DeskField>
				</DeskSection>

				<DeskSection title="Schedule &amp; cost">
					<DeskField label="Start date" :error="errors.startDate">
						<DeskInput v-model="form.startDate" type="date" />
					</DeskField>
					<DeskField label="Expected end date" :error="errors.endDate">
						<DeskInput v-model="form.endDate" type="date" />
					</DeskField>
					<DeskField label="Project budget (₹)">
						<DeskInput v-model="form.budget" type="number" placeholder="0" />
					</DeskField>
					<DeskField label="Priority">
						<DeskSelect v-model="form.priority">
							<option>Low</option>
							<option>Medium</option>
							<option>High</option>
						</DeskSelect>
					</DeskField>
				</DeskSection>

				<DeskSection title="Team &amp; status">
					<DeskField label="Project Manager" :error="errors.pm">
						<DeskLinkPicker
							v-model="form.pm"
							doctype="User"
							placeholder="Select project manager"
							label-field="full_name"
							value-field="name"
							:search-fields="['full_name', 'name', 'email']"
							:filters="[['enabled', '=', 1]]"
							order-by="full_name asc"
							:page-length="20"
							:error="errors.pm"
							@change="clearError('pm')"
						/>
					</DeskField>
					<DeskField label="Initial status">
						<DeskSelect v-model="form.status">
							<option>New</option>
							<option>Ongoing</option>
							<option>Delayed</option>
							<option>Completed</option>
						</DeskSelect>
					</DeskField>
				</DeskSection>

				<!-- Hierarchy section removed (Session 38). New projects created from the
           main Projects list are always top-level. Subprojects are created via
           the "+ Add Subproject" entry inside Project Detail, which passes
           ?parentId= on the route — form.parentId picks that up from the route
           query during init and the subproject path still works. -->
			</div>
		</DeskForm>

		<CustomerCreateModal
			:open="customerModalOpen"
			@close="customerModalOpen = false"
			@created="onCustomerCreated"
		/>
	</DeskPage>
</template>
