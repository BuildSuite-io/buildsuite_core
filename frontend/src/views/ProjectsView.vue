<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import DeskPage from '@/components/desk/DeskPage.vue'
import DeskSelect from '@/components/desk/DeskSelect.vue'
import DeskFilterChip from '@/components/desk/DeskFilterChip.vue'
import DeskLink from '@/components/desk/DeskLink.vue'
import UserAvatar from '@/components/UserAvatar.vue'
import DocTypeListView from '@/components/doctype/DocTypeListView.vue'
import { fmtCompactINR } from '@/utils/format'
import { useDocTypeList } from '@/composables/useDocTypeList'

const router = useRouter()

const statusFilter = ref('')
const typeFilter = ref('')
const companyFilter = ref('')

const companiesResource = useDocTypeList('Company', {
  fields: ['name', 'abbr'],
  orderBy: 'name asc',
  cache: 'buildsuite-companies-for-project-list',
  transform(companies) {
    return companies.map((c) => ({
      id: c.name,
      name: c.name,
      abbr: c.abbr || '',
    }))
  },
})

const isMultiCompany = computed(() => (companiesResource.data?.length ?? 0) > 1)

const filterValues = computed(() => ({
  status: statusFilter.value,
  type: typeFilter.value,
  company: companyFilter.value,
}))

function companyName(id) {
  return companiesResource.data?.find((c) => c.id === id)?.name || id
}

const breadcrumbs = [
  { label: 'BuildSuite Core', to: '/' },
  { label: 'Project' },
]

function onRowClick(row) {
  router.push(`/app/projects/${row.name}`)
}
</script>

<template>
  <DeskPage title="Project" :breadcrumbs="breadcrumbs">
    <template #actions>
      <RouterLink to="/app/projects/new" class="desk-save-btn">+ New</RouterLink>
    </template>

    <DocTypeListView
      doctype="Project"
      :field-order="[
        'custom_project_id',
        'project_name',
        'customer',
        'project_type',
        'status',
        'estimated_costing',
        'percent_complete',
        'expected_start_date',
        'expected_end_date',
        'owner',
        'company',
      ]"
      :columns="[
        { key: 'custom_project_id', label: 'Project ID' },
        { key: 'project_name', label: 'Project Name' },
        { key: 'customer', label: 'Client' },
        { key: 'project_type', label: 'Project Type' },
        { key: 'status', label: 'Status', preset: 'status' },
        { key: 'estimated_costing', label: 'Budget' },
        { key: 'percent_complete', label: 'Progress', preset: 'progress' },
        { key: 'timeline', label: 'Timeline', preset: 'timeline', fields: ['expected_start_date', 'expected_end_date'] },
        { key: 'owner', label: 'Owner' },
        { key: 'company', label: 'Company' },
      ]"
      :search-fields="['project_name', 'custom_project_id', 'customer', 'name']"
      :base-filters="[['is_group', '=', 1]]"
      :filter-values="filterValues"
      :filter-field-map="{ status: 'status', type: 'project_type', company: 'company' }"
      cache-key="buildsuite-project-list-generic"
      row-key="name"
      search-placeholder="Search by name, code, client…"
      @row-click="onRowClick"
    >
      <template #filter-chips>
        <DeskSelect v-model="statusFilter" class="!w-32">
          <option value="">Status: Any</option>
          <option>Open</option>
          <option>Working</option>
          <option>Completed</option>
          <option>On Hold</option>
          <option>Cancelled</option>
        </DeskSelect>

        <DeskSelect v-model="typeFilter" class="!w-40">
          <option value="">Type: Any</option>
          <option>Commercial</option>
          <option>Residential</option>
          <option>Infrastructure</option>
          <option>Industrial</option>
          <option>Renovation</option>
        </DeskSelect>

        <template v-if="isMultiCompany">
          <DeskSelect v-if="!companyFilter" v-model="companyFilter" class="!w-44">
            <option value="">Company: Any</option>
            <option v-for="c in companiesResource.data" :key="c.id" :value="c.id">{{ c.name }}</option>
          </DeskSelect>
          <DeskFilterChip
            v-else
            label="Company"
            :value="companyName(companyFilter)"
            @remove="companyFilter = ''"
          />
        </template>
      </template>

      <template #cell-custom_project_id="{ row }">
        <DeskLink :to="`/app/projects/${row.name}`" @click.stop class="font-mono text-xs">
          {{ row.custom_project_id || row.name }}
        </DeskLink>
      </template>

      <template #cell-project_name="{ row }">
        <span class="text-ink-900 font-medium">{{ row.project_name || row.name }}</span>
      </template>

      <template #cell-estimated_costing="{ row }">
        <span class="tabular-nums">{{ fmtCompactINR(row.estimated_costing || 0) }}</span>
      </template>

      <template #cell-owner="{ row }">
        <UserAvatar :user-id="row.owner" size="xs" />
      </template>

      <template #empty>
        <div class="text-sm text-ink-500">
          No projects match your filters ·
          <DeskLink to="/app/projects/new">Create one →</DeskLink>
        </div>
      </template>
    </DocTypeListView>
  </DeskPage>
</template>
