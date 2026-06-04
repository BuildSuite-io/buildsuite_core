import { computed, ref } from 'vue'

export function useProjectDetailListFilters({ project, subs, workPackages, tasks, scos, boqs }) {
  const subSearch = ref('')
  const wpSearch = ref('')
  const wpProjectFilter = ref('')
  const taskSearch = ref('')
  const taskProjectFilter = ref('')
  const scoSearch = ref('')
  const boqSearch = ref('')

  const wpProjectFilterOptions = computed(() => {
    const root = project.value
      ? [{ id: project.value.id, name: project.value.name || project.value.id }]
      : []
    const children = subs.value.map((p) => ({
      id: p.id,
      name: p.name || p.id,
    }))
    return [...root, ...children]
  })

  const taskProjectFilterOptions = computed(() => {
    const root = project.value
      ? [{ id: project.value.id, name: project.value.name || project.value.id }]
      : []
    const children = subs.value.map((p) => ({
      id: p.id,
      name: p.name || p.id,
    }))
    return [...root, ...children]
  })

  const taskProjectNameById = computed(() => {
    const map = new Map()
    for (const p of taskProjectFilterOptions.value) {
      map.set(p.id, p.name)
    }
    return map
  })

  function expandProjectFilterIds(selectedProjectId) {
    if (!selectedProjectId) return []
    const ids = [selectedProjectId]
    if (selectedProjectId === project.value?.id) {
      ids.push(...subs.value.map((p) => p.id).filter(Boolean))
    }
    return Array.from(new Set(ids))
  }

  const subsFiltered = computed(() => {
    const term = subSearch.value.trim().toLowerCase()
    if (!term) return subs.value
    return subs.value.filter(
      (s) => s.name.toLowerCase().includes(term) || s.code.toLowerCase().includes(term),
    )
  })

  const wpFiltered = computed(() => {
    const term = wpSearch.value.trim().toLowerCase()
    const allowedProjectIds = new Set(expandProjectFilterIds(wpProjectFilter.value))
    return workPackages.value.filter((w) => {
      if (wpProjectFilter.value && !allowedProjectIds.has(w.projectId)) return false
      if (!term) return true
      return w.name.toLowerCase().includes(term) || (w.code || '').toLowerCase().includes(term)
    })
  })

  const tasksFiltered = computed(() => {
    const term = taskSearch.value.trim().toLowerCase()
    const allowedProjectIds = new Set(expandProjectFilterIds(taskProjectFilter.value))
    return tasks.value.filter((t) => {
      if (taskProjectFilter.value && !allowedProjectIds.has(t.projectId)) return false
      if (!term) return true
      return t.name.toLowerCase().includes(term)
    })
  })

  const scosFiltered = computed(() => {
    const term = scoSearch.value.trim().toLowerCase()
    if (!term) return scos.value
    return scos.value.filter(
      (s) => s.title.toLowerCase().includes(term) || s.id.toLowerCase().includes(term),
    )
  })

  const boqsFiltered = computed(() => {
    const term = boqSearch.value.trim().toLowerCase()
    if (!term) return boqs.value
    return boqs.value.filter(
      (b) => b.title.toLowerCase().includes(term) || b.id.toLowerCase().includes(term),
    )
  })

  const wpProgress = computed(() => {
    const items = workPackages.value
    if (!items.length) return 0
    return Math.round(items.reduce((acc, item) => acc + item.progress, 0) / items.length)
  })

  const taskStats = computed(() => {
    const all = tasks.value
    return {
      total: all.length,
      completed: all.filter((t) => t.status === 'Completed').length,
      inProgress: all.filter((t) => t.status === 'In Progress').length,
      open: all.filter((t) => t.status === 'Open').length,
    }
  })

  return {
    boqSearch,
    boqsFiltered,
    scoSearch,
    scosFiltered,
    subSearch,
    subsFiltered,
    taskProjectFilter,
    taskProjectFilterOptions,
    taskProjectNameById,
    taskSearch,
    taskStats,
    tasksFiltered,
    wpFiltered,
    wpProgress,
    wpProjectFilter,
    wpProjectFilterOptions,
    wpSearch,
  }
}
