<script setup>
// Editor for a persona's roles: selected roles as removable pills + an "add role"
// dropdown of the still-assignable roles. v-model is an array of role names.

import { computed } from "vue";
import DeskSelect from "@/components/desk/DeskSelect.vue";

const props = defineProps({
	modelValue: { type: Array, default: () => [] },
	available: { type: Array, default: () => [] },
});
const emit = defineEmits(["update:modelValue"]);

const addable = computed(() => props.available.filter((r) => !props.modelValue.includes(r)));

function addRole(role) {
	if (role && !props.modelValue.includes(role)) {
		emit("update:modelValue", [...props.modelValue, role]);
	}
}
function removeRole(role) {
	emit(
		"update:modelValue",
		props.modelValue.filter((r) => r !== role),
	);
}
</script>

<template>
	<div>
		<div v-if="modelValue.length" class="flex flex-wrap gap-1.5 mb-2">
			<span
				v-for="role in modelValue"
				:key="role"
				class="inline-flex items-center gap-1 text-xs px-2 py-1 rounded-full bg-ink-100 text-ink-700"
			>
				{{ role }}
				<button
					type="button"
					class="text-ink-400 hover:text-danger-600 leading-none"
					aria-label="Remove role"
					@click="removeRole(role)"
				>
					×
				</button>
			</span>
		</div>
		<p v-else class="text-xs text-ink-400 mb-2">No roles yet — add at least one below.</p>

		<DeskSelect v-if="addable.length" :model-value="''" @update:model-value="addRole">
			<option value="">+ Add role…</option>
			<option v-for="role in addable" :key="role" :value="role">{{ role }}</option>
		</DeskSelect>
		<p v-else class="text-xs text-ink-400">All assignable roles added.</p>
	</div>
</template>
