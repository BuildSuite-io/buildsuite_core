<script setup>
// The dynamic "Add filter" editor, anchored under the list toolbar. Pairs with useDynamicFilters
// and DeskList's @add-filter; place it inside a `relative` wrapper around the DeskList (the same
// placement DocTypeListView uses).
import DeskFilterEditor from "@/components/desk/DeskFilterEditor.vue";

defineProps({ filters: { type: Object, required: true } });
</script>

<template>
	<template v-if="filters.editorOpen.value">
		<div class="fixed inset-0 z-30" @click="filters.closeEditor()"></div>
		<div class="absolute left-0 top-12 z-40">
			<DeskFilterEditor
				:fields="filters.fields.value"
				:initial="
					filters.editingIndex.value >= 0
						? filters.filters.value[filters.editingIndex.value]
						: null
				"
				@apply="filters.apply"
				@cancel="filters.closeEditor()"
			/>
		</div>
	</template>
</template>
