<script setup>
import { onMounted, watch } from 'vue'
import { useDataStore } from '@/stores'

const store = useDataStore()
onMounted(() => store.hydrate())

// Apply the `dark` class on <html> based on store.theme. Watch immediate so
// the class lands on first paint after hydrate; subsequent flips persist via
// store.setTheme which writes to localStorage.
function applyThemeClass(theme) {
  const root = document.documentElement
  if (theme === 'dark') root.classList.add('dark')
  else root.classList.remove('dark')
}
watch(() => store.theme, (t) => applyThemeClass(t), { immediate: true })
</script>

<template>
  <router-view v-slot="{ Component }">
    <transition name="fade" mode="out-in">
      <component :is="Component" />
    </transition>
  </router-view>
</template>

<style>
.fade-enter-active, .fade-leave-active { transition: opacity 0.15s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>
