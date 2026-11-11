<script setup>
// A named place in a page where installed apps can add components. Pages (and DeskPage, for
// every page) declare one; extensions fill it with sdk.slots.add(name, component). Renders
// nothing when nothing is registered, so an empty slot costs nothing and shows nothing.
//
// Slot names read <area>.<name>.<position>, e.g. "page.quotation-detail.top". `context` is passed
// to each component as props.
import { computed } from "vue";
import ExtensionBoundary from "@/components/ExtensionBoundary.vue";
import { slotsFor } from "@/sdk/registry";

const props = defineProps({
	name: { type: String, required: true },
	context: { type: Object, default: () => ({}) },
});

function allowed(item) {
	if (!item.when) return true;
	try {
		return !!item.when(props.context);
	} catch (error) {
		console.warn(`[buildsuite] extension "${item.extension}" slot condition failed`, error);
		return false;
	}
}

const items = computed(() => slotsFor(props.name).filter(allowed));
</script>

<template>
	<template v-if="items.length">
		<ExtensionBoundary v-for="item in items" :key="item.id" :extension="item.extension">
			<component :is="item.component" v-bind="context" />
		</ExtensionBoundary>
	</template>
</template>
