<script setup>
// Project Settings — the site-wide standard tab template (level 1 of two). Which tabs every
// project's detail page offers by default; a project can overrule any of these for itself from
// its own "..." menu. Overview is always shown (the landing + fallback tab) and is not listed.
// Backed by the Project Settings Single (api.project_settings). Admin / BSA gated for edits.
import { ref, watch, computed } from "vue";
import { useDataStore } from "@/stores";
import { PROJECT_TABS } from "@/data/projectTabs";
import { showToast } from "@/utils/appToast";
import DeskPage from "@/components/desk/DeskPage.vue";
import DeskForm from "@/components/desk/DeskForm.vue";
import DeskActionBar from "@/components/desk/DeskActionBar.vue";
import DeskSection from "@/components/desk/DeskSection.vue";

const store = useDataStore();

const editing = ref(false);
const saving = ref(false);
const form = ref({ tabs: {} });

function snapshot() {
	const tabs = {};
	for (const t of PROJECT_TABS) tabs[t.id] = store.siteProjectTabVisible(t.id);
	return { tabs };
}
watch(() => store.projectSettings, () => { if (!editing.value) form.value = snapshot(); },
	{ immediate: true, deep: true });

function startEdit() { form.value = snapshot(); editing.value = true; }
function cancelEdit() { form.value = snapshot(); editing.value = false; }
async function saveEdit() {
	if (!store.isAdmin) return;
	saving.value = true;
	try {
		await store.updateProjectSettings({ ...form.value.tabs });
		editing.value = false;
		showToast("Project Settings saved", "success");
	} catch (e) {
		showToast(e.message || "Could not save Project Settings", "error");
	} finally {
		saving.value = false;
	}
}
function onPrimary() { editing.value ? saveEdit() : startEdit(); }

function setAll(on) {
	for (const t of PROJECT_TABS) form.value.tabs[t.id] = on;
}

const shownCount = computed(() => PROJECT_TABS.filter((t) => store.siteProjectTabVisible(t.id)).length);

const breadcrumbs = [
	{ label: "BuildSuite Core", to: "/" },
	{ label: "Settings", to: "/settings" },
	{ label: "Project Settings" },
];
</script>

<template>
	<DeskPage
		title="Project Settings"
		subtitle="Site-wide defaults for the Project record"
		:breadcrumbs="breadcrumbs"
	>
		<DeskForm>
			<template #action-bar>
				<DeskActionBar
					v-if="store.isAdmin"
					:save-label="editing ? (saving ? 'Saving…' : 'Save') : 'Edit'"
					:show-cancel="editing"
					:saving="saving"
					cancel-label="Cancel"
					@save="onPrimary"
					@cancel="cancelEdit"
				/>
				<div v-else class="px-3 py-2 bg-warning-50 border-b border-warning-100 text-xs text-warning-700">
					Read-only. Editing requires the Admin or BuildSuite Administrator role.
				</div>
			</template>

			<div class="max-w-3xl mx-auto">
				<DeskSection title="Project page tabs" :cols="1">
					<div class="text-xs text-ink-600 mb-3">
						Which tabs every project offers. Overview is always shown, so it is not listed here.
						Any project can overrule these for itself from its own "…" menu.
					</div>

					<div v-if="editing" class="flex items-center gap-2 mb-3">
						<button type="button" class="text-xs px-2.5 py-1 rounded-md border border-ink-200 text-ink-700 hover:bg-ink-50" @click="setAll(true)">Show all</button>
						<button type="button" class="text-xs px-2.5 py-1 rounded-md border border-ink-200 text-ink-700 hover:bg-ink-50" @click="setAll(false)">Hide all</button>
					</div>

					<div class="border border-ink-200 rounded-lg overflow-hidden">
						<div
							v-for="(t, i) in PROJECT_TABS"
							:key="t.id"
							class="flex items-start gap-3 px-4 py-3"
							:class="i ? 'border-t border-ink-100' : ''"
						>
							<div class="flex-1 min-w-0">
								<div class="text-sm font-medium text-ink-900">{{ t.label }}</div>
								<div class="text-[11px] text-ink-500 mt-0.5">{{ t.desc }}</div>
							</div>

							<div class="flex-shrink-0 pt-0.5">
								<label v-if="editing" class="flex items-center gap-2 text-xs cursor-pointer whitespace-nowrap">
									<input type="checkbox" v-model="form.tabs[t.id]" class="accent-brand-600" />
									<span :class="form.tabs[t.id] ? 'text-ink-900' : 'text-ink-500'">
										{{ form.tabs[t.id] ? "Shown" : "Hidden" }}
									</span>
								</label>
								<span
									v-else
									class="text-[11px] px-2 py-0.5 rounded-full whitespace-nowrap"
									:class="store.siteProjectTabVisible(t.id)
										? 'bg-success-50 text-success-700'
										: 'bg-ink-100 text-ink-600'"
								>
									{{ store.siteProjectTabVisible(t.id) ? "Shown" : "Hidden" }}
								</span>
							</div>
						</div>
					</div>

					<div class="text-[11px] text-ink-500 mt-2">
						{{ shownCount }} of {{ PROJECT_TABS.length }} tabs shown by default.
					</div>
				</DeskSection>
			</div>
		</DeskForm>
	</DeskPage>
</template>
