<script setup>
// BuildSuite brand icon — renders the literal logo image from public/buildsuite-logo.png.
// Previously drawn as an inline SVG path approximation of the angular B; switched to
// <img> against the user-provided image for pixel-perfect fidelity (S18 follow-up).
// The brand color (#16A34A / brand-600) and the icon's geometry are the single source
// of visual truth for BuildSuite throughout the prototype.

defineProps({
  size: { type: [String, Number], default: 28 },
})
</script>

<template>
  <img
    src="/buildsuite-logo.png"
    alt="BuildSuite"
    :width="size"
    :height="size"
    :style="`width:${size}px;height:${size}px;`"
    class="block"
  />
</template>
