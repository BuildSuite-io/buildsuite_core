<script setup>
// To-dos — the list and the board (S365), one filtered set rendered two ways. Backed by Frappe's
// ToDo via api.todo; a to-do is visible when it's allocated to you or you raised it (directors /
// admins see everyone's). The top-nav badge (store.openTodoCount) refreshes on every change.
import { ref, computed, onMounted } from "vue";
import { useDataStore } from "@/stores";
import { showToast } from "@/utils/appToast";
import {
	TODO_STATUSES,
	TODO_BOARD_STATUSES,
	TODO_PRIORITIES,
	TODO_DONE_STATUSES,
	todoDue,
} from "@/data/todo";
import { listTodos, setTodoStatus } from "@/data/todoApi";
import ToDoCard from "@/components/todo/ToDoCard.vue";
import ToDoFormModal from "@/components/todo/ToDoFormModal.vue";
import DeskInput from "@/components/desk/DeskInput.vue";
import DeskSelect from "@/components/desk/DeskSelect.vue";
import DeskSearchableSelect from "@/components/desk/DeskSearchableSelect.vue";
import WorkspaceIcon from "@/components/WorkspaceIcon.vue";

const store = useDataStore();

const todos = ref([]);
const me = ref("");
const canSeeAll = ref(false);
const loading = ref(true);

const today = computed(() => {
	const d = new Date();
	const p = (n) => String(n).padStart(2, "0");
	return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`;
});

const view = ref("list"); // 'list' | 'board'
const scope = ref("mine"); // 'mine' | 'raised' | 'all'
const search = ref("");
const statusFilter = ref("");
const priorityFilter = ref("");
const personFilter = ref("");
const filtersOpen = ref(false);

const newOpen = ref(false);
const editTodo = ref(null);

async function load() {
	loading.value = true;
	try {
		const res = (await listTodos()) || {};
		todos.value = res.todos || [];
		me.value = res.me || "";
		canSeeAll.value = !!res.can_see_all;
	} catch (e) {
		showToast(e.message || "Failed to load to-dos", "error");
	} finally {
		loading.value = false;
	}
	store.loadTodoCount();
}
onMounted(load);

const scoped = computed(() => {
	if (scope.value === "mine") return todos.value.filter((t) => t.allocated_to === me.value);
	if (scope.value === "raised")
		return todos.value.filter((t) => t.assigned_by === me.value && t.allocated_to !== me.value);
	return todos.value;
});

const peopleOptions = computed(() => {
	const seen = new Map();
	for (const t of scoped.value) {
		if (t.allocated_to && !seen.has(t.allocated_to))
			seen.set(t.allocated_to, t.allocated_to_name || t.allocated_to);
	}
	return [...seen.entries()]
		.map(([value, label]) => ({ value, label }))
		.sort((a, b) => a.label.localeCompare(b.label));
});

const filtered = computed(() => {
	const q = search.value.trim().toLowerCase();
	return scoped.value.filter((t) => {
		if (statusFilter.value && t.status !== statusFilter.value) return false;
		if (priorityFilter.value && t.priority !== priorityFilter.value) return false;
		if (personFilter.value && t.allocated_to !== personFilter.value) return false;
		if (!q) return true;
		return `${t.description} ${t.reference_label || ""} ${t.allocated_to_name || ""}`
			.toLowerCase()
			.includes(q);
	});
});

const PRIORITY_RANK = { High: 0, Medium: 1, Low: 2 };
function ordered(list) {
	return [...list].sort((a, b) => {
		const ad = TODO_DONE_STATUSES.includes(a.status) ? 1 : 0;
		const bd = TODO_DONE_STATUSES.includes(b.status) ? 1 : 0;
		if (ad !== bd) return ad - bd;
		if (!!a.date !== !!b.date) return a.date ? -1 : 1;
		if (a.date && b.date && a.date !== b.date) return a.date < b.date ? -1 : 1;
		const ap = PRIORITY_RANK[a.priority] ?? 1;
		const bp = PRIORITY_RANK[b.priority] ?? 1;
		if (ap !== bp) return ap - bp;
		return (b.created_at || "").localeCompare(a.created_at || "");
	});
}

const rows = computed(() => ordered(filtered.value));
const columns = computed(() =>
	TODO_BOARD_STATUSES.map((status) => ({
		status,
		items: ordered(filtered.value.filter((t) => t.status === status)),
	}))
);
const hiddenOnBoard = computed(
	() => filtered.value.filter((t) => !TODO_BOARD_STATUSES.includes(t.status)).length
);
const overdueCount = computed(
	() => rows.value.filter((t) => todoDue(t, today.value)?.tone === "overdue").length
);
const scopeNote = computed(() => {
	if (scope.value === "mine") return "assigned to you";
	if (scope.value === "raised") return "you raised for other people";
	return canSeeAll.value ? "everyone's" : "yours, and ones you raised";
});
const anyFilter = computed(
	() => !!(search.value || statusFilter.value || priorityFilter.value || personFilter.value)
);
const activeFilterCount = computed(
	() => [statusFilter.value, priorityFilter.value, personFilter.value].filter(Boolean).length
);
function clearFilters() {
	search.value = "";
	statusFilter.value = "";
	priorityFilter.value = "";
	personFilter.value = "";
}

function open(todo) {
	editTodo.value = todo;
}
async function advance(todo) {
	const i = TODO_BOARD_STATUSES.indexOf(todo.status);
	if (i === -1 || i === TODO_BOARD_STATUSES.length - 1) return;
	await move(todo, TODO_BOARD_STATUSES[i + 1]);
}
async function move(todo, status) {
	try {
		await setTodoStatus(todo.name, status);
		await load();
	} catch (e) {
		showToast(e.message || "Could not update the to-do", "error");
	}
}
function onSaved() {
	newOpen.value = false;
	editTodo.value = null;
	load();
}

// ---- drag, desktop only ----
const dragging = ref(null);
const dropTarget = ref(null);
function onDrop(status) {
	const t = dragging.value;
	dropTarget.value = null;
	dragging.value = null;
	if (t && t.status !== status) move(t, status);
}
</script>

<template>
	<div class="max-w-6xl mx-auto px-3 sm:px-5 py-4 sm:py-6">
		<!-- Header -->
		<div class="flex flex-wrap items-start gap-3 mb-4">
			<div class="min-w-0">
				<h1 class="text-lg font-semibold text-ink-900">To-dos</h1>
				<p class="text-xs text-ink-500 mt-0.5">
					{{ rows.length }} {{ rows.length === 1 ? "to-do" : "to-dos" }} · {{ scopeNote
					}}<template v-if="overdueCount">
						· <span class="text-danger-700 font-medium">{{ overdueCount }} overdue</span></template
					>
				</p>
			</div>
			<button type="button" class="desk-save-btn !h-9" @click="newOpen = true">+ New to-do</button>
			<div class="ml-auto flex items-center gap-1 bg-ink-100 rounded-lg p-0.5 shrink-0">
				<button
					v-for="v in [
						{ id: 'list', label: 'List', icon: 'clipboard-list' },
						{ id: 'board', label: 'Board', icon: 'layout-grid' },
					]"
					:key="v.id"
					type="button"
					class="flex items-center gap-1.5 px-2.5 h-8 rounded-md text-xs font-medium transition-colors"
					:class="view === v.id ? 'bg-white text-ink-900 shadow-sm' : 'text-ink-600 hover:text-ink-900'"
					:aria-pressed="view === v.id"
					:title="v.label"
					@click="view = v.id"
				>
					<WorkspaceIcon :slug="v.icon" :size="14" />
					<span class="hidden sm:inline">{{ v.label }}</span>
				</button>
			</div>
		</div>

		<!-- Scope + filters -->
		<div class="flex flex-wrap items-center gap-2 mb-4">
			<div class="flex items-center gap-1 bg-ink-100 rounded-lg p-0.5">
				<button
					v-for="s in [
						{ id: 'mine', label: 'Mine' },
						{ id: 'raised', label: 'I raised' },
						{ id: 'all', label: canSeeAll ? 'Everyone' : 'All' },
					]"
					:key="s.id"
					type="button"
					class="px-2.5 h-8 rounded-md text-xs font-medium transition-colors"
					:class="scope === s.id ? 'bg-white text-ink-900 shadow-sm' : 'text-ink-600 hover:text-ink-900'"
					:aria-pressed="scope === s.id"
					@click="scope = s.id"
				>
					{{ s.label }}
				</button>
			</div>

			<DeskInput v-model="search" class="!w-full sm:!w-56" placeholder="Search to-dos…" />

			<button
				type="button"
				class="sm:hidden flex items-center gap-1.5 px-2.5 h-8 rounded-lg border border-ink-200 bg-white text-xs font-medium text-ink-700"
				:aria-expanded="filtersOpen"
				@click="filtersOpen = !filtersOpen"
			>
				<span>Filters</span>
				<span v-if="activeFilterCount" class="text-[10px] tabular-nums px-1.5 py-0.5 rounded-full bg-brand-700 text-white">{{ activeFilterCount }}</span>
			</button>

			<DeskSelect v-model="statusFilter" class="!w-auto" :class="filtersOpen ? '' : 'hidden sm:block'">
				<option value="">Any status</option>
				<option v-for="s in TODO_STATUSES" :key="s" :value="s">{{ s }}</option>
			</DeskSelect>
			<DeskSelect v-model="priorityFilter" class="!w-auto" :class="filtersOpen ? '' : 'hidden sm:block'">
				<option value="">Any priority</option>
				<option v-for="p in TODO_PRIORITIES" :key="p" :value="p">{{ p }}</option>
			</DeskSelect>
			<DeskSearchableSelect
				v-if="scope !== 'mine' && peopleOptions.length > 1"
				v-model="personFilter"
				:options="peopleOptions"
				allow-clear
				touch
				class="!w-48"
				:class="filtersOpen ? '' : 'hidden sm:block'"
				placeholder="Anyone"
			/>
			<button v-if="anyFilter" type="button" class="text-xs text-brand-700 hover:underline px-1" @click="clearFilters">Clear filters</button>
		</div>

		<div v-if="loading" class="py-16 text-center text-sm text-ink-400">Loading…</div>

		<!-- Empty -->
		<div v-else-if="!rows.length" class="border border-dashed border-ink-200 rounded-xl px-4 py-14 text-center">
			<WorkspaceIcon slug="check-circle" :size="28" class="text-ink-300 mx-auto mb-3" />
			<div class="text-sm text-ink-700">
				{{ anyFilter ? "Nothing matches those filters." : scope === "mine" ? "Nothing on your plate." : "Nothing here yet." }}
			</div>
			<div class="text-xs text-ink-500 mt-1">
				{{ anyFilter ? "Clear them to see the rest." : "To-dos are the office jobs that aren't on a project." }}
			</div>
			<button v-if="!anyFilter" type="button" class="desk-save-btn !h-10 !px-4 mt-4" @click="newOpen = true">+ New to-do</button>
		</div>

		<!-- List -->
		<div v-else-if="view === 'list'" class="space-y-2">
			<ToDoCard
				v-for="t in rows"
				:key="t.name"
				:todo="t"
				:today="today"
				variant="row"
				@open="open"
				@advance="advance"
				@dragstart="dragging = $event"
				@dragend="dragging = null"
			/>
		</div>

		<!-- Board -->
		<div v-else>
			<div class="flex gap-3 overflow-x-auto snap-x snap-mandatory pb-2 -mx-3 px-3 sm:mx-0 sm:px-0 lg:overflow-x-visible">
				<section
					v-for="col in columns"
					:key="col.status"
					class="snap-start shrink-0 w-[82vw] sm:w-72 lg:w-auto lg:flex-1 flex flex-col rounded-xl border transition-colors"
					:class="dropTarget === col.status ? 'border-brand-400 bg-brand-50' : 'border-ink-200 bg-ink-100'"
					@dragover.prevent="dropTarget = col.status"
					@dragleave="dropTarget === col.status && (dropTarget = null)"
					@drop.prevent="onDrop(col.status)"
				>
					<header class="px-3 py-2.5 flex items-center gap-2 border-b border-ink-200">
						<span class="text-xs font-semibold uppercase tracking-wider text-ink-600">{{ col.status }}</span>
						<span class="text-xs text-ink-600 tabular-nums ml-auto">{{ col.items.length }}</span>
					</header>
					<div class="p-2 space-y-2 flex-1 min-h-[6rem]">
						<ToDoCard
							v-for="t in col.items"
							:key="t.name"
							:todo="t"
							:today="today"
							variant="card"
							@open="open"
							@advance="advance"
							@dragstart="dragging = $event"
							@dragend="dragging = null"
						/>
						<p v-if="!col.items.length" class="text-xs text-ink-600 text-center py-6">Nothing here</p>
					</div>
				</section>
			</div>
			<p v-if="hiddenOnBoard" class="text-xs text-ink-500 mt-3">
				{{ hiddenOnBoard }} cancelled {{ hiddenOnBoard === 1 ? "to-do is" : "to-dos are" }} not shown — switch to the list to see them.
			</p>
		</div>

		<ToDoFormModal :open="newOpen" @close="newOpen = false" @saved="onSaved" />
		<ToDoFormModal :open="!!editTodo" :todo="editTodo" @close="editTodo = null" @saved="onSaved" />
	</div>
</template>
