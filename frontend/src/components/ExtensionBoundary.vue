<script setup>
// Contains a failing extension component: if it throws while rendering, only it disappears (and
// the failure is logged); the page around it keeps working.
import { ref, onErrorCaptured } from "vue";

const props = defineProps({ extension: { type: String, default: "" } });
const failed = ref(false);

onErrorCaptured((error) => {
	failed.value = true;
	console.warn(`[buildsuite] extension "${props.extension}" failed while rendering`, error);
	return false; // handled here — do not propagate to the host page
});
</script>

<template>
	<slot v-if="!failed" />
</template>
