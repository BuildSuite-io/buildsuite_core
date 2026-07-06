<script setup>
// Personas — settings list (backend-backed via the Persona master). Admin / BSA
// gated. A persona maps to one or more Frappe roles; assigning it to a user grants
// those roles (sync_persona_roles hook).

import { ref, computed, onMounted } from "vue";
import { useRouter } from "vue-router";
import { useDataStore } from "@/stores";
import { listPersonas } from "@/data/personaApi";
import DeskPage from "@/components/desk/DeskPage.vue";
import DeskList from "@/components/desk/DeskList.vue";
import DeskLink from "@/components/desk/DeskLink.vue";

const store = useDataStore();
const router = useRouter();

const personas = ref([]);
const loading = ref(true);
const loadError = ref("");
const search = ref("");

const columns = [
	{ key: "persona_name", label: "Persona" },
	{ key: "slug", label: "Slug" },
	{ key: "roles", label: "Roles" },
	{ key: "enabled", label: "Status" },
];

const items = computed(() => {
	const term = search.value.trim().toLowerCase();
	if (!term) return personas.value;
	return personas.value.filter((p) =>
		`${p.persona_name} ${p.slug} ${(p.roles || []).join(" ")}`.toLowerCase().includes(term),
	);
});

async function load() {
	loading.value = true;
	loadError.value = "";
	try {
		personas.value = await listPersonas();
	} catch (err) {
		loadError.value = err.message || "Could not load personas.";
	} finally {
		loading.value = false;
	}
}

function onRowClick(row) {
	router.push(`/settings/personas/${encodeURIComponent(row.name)}`);
}

const breadcrumbs = [
	{ label: "BuildSuite Core", to: "/" },
	{ label: "Settings", to: "/settings" },
	{ label: "Personas" },
];

onMounted(() => {
	if (!store.isAdmin && !store.isBSA) {
		router.replace("/settings");
		return;
	}
	load();
});
</script>

<template>
	<DeskPage title="Personas" :breadcrumbs="breadcrumbs">
		<template #actions>
			<DeskLink to="/settings/personas/new" class="desk-save-btn">+ New Persona</DeskLink>
		</template>

		<div
			v-if="loadError"
			class="mb-3 px-3 py-2 bg-danger-50 border border-danger-100 text-xs text-danger-700 dark:bg-ink-800 dark:border-ink-700"
			style="border-radius: 6px"
		>
			{{ loadError }}
		</div>

		<DeskList
			v-model="search"
			:rows="items"
			:columns="columns"
			row-key="name"
			search-placeholder="Search personas…"
			@row-click="onRowClick"
		>
			<template #cell-persona_name="{ row }">
				<span class="text-sm font-medium text-ink-900 dark:text-[#F5F5F5]">{{
					row.persona_name
				}}</span>
			</template>
			<template #cell-slug="{ row }">
				<span class="text-xs text-ink-500 font-mono">{{ row.slug || "—" }}</span>
			</template>
			<template #cell-roles="{ row }">
				<span class="flex flex-wrap gap-1">
					<span
						v-for="role in row.roles"
						:key="role"
						class="text-[10px] px-1.5 py-0.5 rounded-full font-medium bg-ink-100 text-ink-700"
						>{{ role }}</span
					>
					<span v-if="!row.roles || !row.roles.length" class="text-[10px] text-ink-400"
						>No roles</span
					>
				</span>
			</template>
			<template #cell-enabled="{ row }">
				<span
					class="text-[10px] px-1.5 py-0.5 font-medium"
					:class="
						row.enabled ? 'bg-success-50 text-success-700' : 'bg-ink-100 text-ink-500'
					"
					style="border-radius: 9999px"
					>{{ row.enabled ? "Enabled" : "Disabled" }}</span
				>
			</template>
		</DeskList>
	</DeskPage>
</template>
