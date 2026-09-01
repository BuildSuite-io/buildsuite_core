<script setup>
// The "Records" group for a workspace — DocType shortcut tiles configured in
// Workspace Setting, each opening the generic /records list + form. Server-gated
// per DocType (a persona who can't read a DocType never gets its tile), so this
// simply renders whatever get_workspace_doctypes returns for the slug.
import { ref, onMounted } from "vue";
import WorkspaceShortcut from "@/components/WorkspaceShortcut.vue";
import { getWorkspaceDoctypes } from "@/data/workspaceSettingApi";

const props = defineProps({ workspace: { type: String, required: true } });

const records = ref([]);
onMounted(async () => {
	try {
		records.value = await getWorkspaceDoctypes(props.workspace);
	} catch {
		records.value = [];
	}
});
</script>

<template>
	<div v-if="records.length" class="mb-8">
		<h2 class="text-[11px] font-semibold uppercase tracking-wider text-ink-700 mb-2">Records</h2>
		<div class="border-t border-ink-200 mb-3"></div>
		<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
			<WorkspaceShortcut
				v-for="(d, i) in records"
				:key="i"
				:icon="d.icon"
				:label="d.label"
				:description="d.description"
				:to="d.route"
			>
				<template #badge>
					<span
						class="text-[9px] px-1 py-0.5 bg-ink-100 text-ink-600 font-medium uppercase tracking-wider"
						style="border-radius: 2px"
						>Records</span
					>
				</template>
			</WorkspaceShortcut>
		</div>
	</div>
</template>
