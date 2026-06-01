<script setup>
// Select dropdown styled to Frappe Desk standards. Consumers provide <option> tags
// via the default slot. Accepts v-model.

defineProps({
  modelValue: { type: [String, Number, null], default: '' },
  disabled: { type: Boolean, default: false },
  name: { type: String, default: '' },
})
defineEmits(['update:modelValue'])
</script>

<template>
  <select
    :value="modelValue"
    :disabled="disabled"
    :name="name"
    class="desk-input"
    @change="$emit('update:modelValue', $event.target.value)"
  >
    <slot />
  </select>
</template>
