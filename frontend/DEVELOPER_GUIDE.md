# Frontend Developer Guide

This guide documents the current list-view stack used in BuildSuite frontend:

- `DeskList` (`src/components/desk/DeskList.vue`) — presentational list/table shell.
- `DocTypeListView` (`src/components/doctype/DocTypeListView.vue`) — Frappe-DocType-aware wrapper over `DeskList`.

Use `DocTypeListView` for generic DocType screens. Use `DeskList` directly when data does not come from a DocType resource.

## 1. Quick Start

Example using `DocTypeListView` (current Projects list pattern):

```vue
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
  search-placeholder="Search by name, code, client..."
  :paginated="true"
  :page-size="20"
  :page-size-options="[10, 20, 50, 100]"
  @row-click="onRowClick"
/>
```

Note: `DocTypeListView` does not take a `rows` prop. It fetches data from Frappe resources and internally passes rows to `DeskList`.

## 2. DeskList API

`DeskList` expects rows + columns already prepared by the parent.

Minimal direct `DeskList` usage:

```vue
<DeskList
  :rows="rows"
  :columns="columns"
  row-key="id"
  @row-click="onRowClick"
/>
```

### 2.1 Props

- `rows: Array` (required)
- `columns: Array` (required)
- `rowKey: String | Function` (default: `'id'`)
- `modelValue: String` (search text)
- `searchPlaceholder: String`
- `bulkSelect: Boolean` (default: `false`)
- `selected: Array` (selected row keys)
- `showSort: Boolean` (default: `true`)
- `showColumns: Boolean` (default: `true`)
- `showAddFilter: Boolean` (default: `true`)
- `paginated: Boolean` (default: `true`)
- `pageSize: Number` (default: `10`)
- `pageSizeOptions: Number[]` (default: `[10, 20, 50, 100]`)

### 2.2 Column shape

Each entry in `columns` can use:

- `key: string` (required)
- `label: string` (required)
- `align?: 'left' | 'right' | 'center'`
- `render?: (row) => string` (simple text rendering)
- `class?: string` (cell class)

### 2.3 Emits

- `update:modelValue`
- `update:selected`
- `row-click`
- `add-filter`
- `sort`
- `toggle-columns`

### 2.4 Slots

- `filter-chips` — inline controls next to search
- `pre-columns-controls` — controls inserted before the Columns button (used by grouped sort/order in `DocTypeListView`)
- `actions` — right-side action buttons
- `cell-<columnKey>` — scoped cell slot (`{ row, value }`)
- `empty`

## 3. DocTypeListView API

`DocTypeListView` fetches DocType data, metadata, and feeds `DeskList`.

### 3.1 Core props

- `doctype: String` (required)
- `fieldOrder: String[]` (required)
- `columns?: ColumnConfig[]` (optional renderer/config API)
- `searchFields?: String[]` (default: `['name']`)
- `baseFilters?: Array` (default: `[]`)
- `filterValues?: Record<string, any>`
- `filterFieldMap?: Record<string, string>`
- `pageLength?: Number` (server fetch size; default: `100`)
- `cacheKey?: String | Array`
- `initialOrderBy?: String` (example: `'creation desc'`)
- `rowKey?: String` (default: `'name'`)
- `searchPlaceholder?: String`
- `emptyMessage?: String`

### 3.2 Pagination props (forwarded to DeskList)

- `paginated?: Boolean` (default: `true`)
- `pageSize?: Number` (default: `10`)
- `pageSizeOptions?: Number[]` (default: `[10, 20, 50, 100]`)

### 3.3 Emits

- `row-click`

### 3.4 Slots

- `filter-chips` (scope: `{ resource, meta, metaLoading, fields }`)
- `cell-<columnKey>`
- `empty`

Slot precedence is intentional: if a cell slot is provided, it overrides any preset/renderer/default formatting.

## 4. Column Renderer API (`columns`)

`columns` is optional. If omitted, list columns are derived from `fieldOrder` + metadata.

### 4.1 ColumnConfig shape

- `key: string` (required)
- `label?: string`
- `align?: 'left' | 'right' | 'center'`
- `preset?: 'status' | 'progress' | 'timeline'`
- `fields?: string[]` (composite field backing; used by timeline)
- `renderer?: Component | string`
- `rendererProps?: Record<string, any>`

### 4.2 Built-in presets

- `status`
  - Uses `StatusBadge` with the column key value.
- `progress`
  - Renders a progress bar and clamped percent text.
- `timeline`
  - Renders a single timeline column from two fields.
  - Default fields fallback: `expected_start_date`, `expected_end_date`.

### 4.3 Custom renderer components

If `renderer` is a component, `DocTypeListView` renders it and passes:

- `row`
- `column`
- `value` (single field value or `fields[]` tuple)
- `meta` (field metadata by `column.key`, if available)
- `...rendererProps`

Example:

```vue
<DocTypeListView
  doctype="Task"
  :field-order="['name', 'status', 'exp_end_date']"
  :columns="[
    { key: 'name', label: 'Task' },
    { key: 'status', label: 'Status', renderer: TaskStatusPill, rendererProps: { compact: true } },
    { key: 'timeline', label: 'Timeline', preset: 'timeline', fields: ['creation', 'exp_end_date'] },
  ]"
/>
```

## 5. Sorting behavior

`DocTypeListView` includes a grouped sort control in the right action cluster (before Columns):

- left button toggles ascending/descending
- right select chooses sortable field

Sortable fields are derived from resolved fields + metadata types + `meta.sort_field` + `modified` fallback.

## 6. Filtering behavior

`DocTypeListView` combines filters as:

1. `baseFilters`
2. mapped values from `filterValues` using `filterFieldMap`

Only truthy filter values are appended.

## 7. Pagination behavior notes

- `pageLength` controls server fetch size from Frappe resource.
- `paginated/pageSize/pageSizeOptions` control client-side paging in the rendered table.
- Current implementation is client-side pagination over fetched rows.
- If server-side paging is needed later, keep this API and introduce resource-level page state.

## 8. Recommended patterns

- Use `columns` for reusable renderer config.
- Use `cell-<key>` slots for one-off screen-specific UI.
- Keep `fieldOrder` aligned with all fields needed by renderers and filters.
- For composite columns (like timeline), include all backing fields in `fieldOrder`.

## 9. Current production usage reference

- `ProjectsView` generic DocType list:
  - `src/views/ProjectsView.vue`
- Generic list wrapper:
  - `src/components/doctype/DocTypeListView.vue`
- Base desk table shell:
  - `src/components/desk/DeskList.vue`
