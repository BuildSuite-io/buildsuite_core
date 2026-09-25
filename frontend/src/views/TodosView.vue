<script setup>
// The user's personal to-do list — Frappe's ToDo doctype, surfaced in the SPA. Add, tick off,
// edit and delete your own to-dos. The top-nav badge (store.openTodoCount) refreshes on every
// change. A to-do is "mine" when it's allocated to me or I created it (backend api.todo).
import { ref, computed, onMounted } from "vue";
import { useDataStore } from "@/stores";
import { showToast } from "@/utils/appToast";
import { useConfirm } from "@/composables/useConfirm";
import { listMyTodos, saveTodo, setTodoStatus, deleteTodo } from "@/data/todoApi";
import DeskPage from "@/components/desk/DeskPage.vue";
import DeskSelect from "@/components/desk/DeskSelect.vue";

const store = useDataStore();
const confirmDialog = useConfirm();

const todos = ref([]);
const loading = ref(true);

const newText = ref("");
const newPriority = ref("Medium");
const newDate = ref("");
const saving = ref(false);

const editId = ref(null);
const editText = ref("");
const editPriority = ref("Medium");
const editDate = ref("");

async function load() {
	loading.value = true;
	try {
		todos.value = await listMyTodos();
	} catch (e) {
		showToast(e.message || "Failed to load to-dos", "error");
	} finally {
		loading.value = false;
	}
	store.loadTodoCount();
}
onMounted(load);

const openTodos = computed(() => todos.value.filter((t) => t.status === "Open"));
const doneTodos = computed(() => todos.value.filter((t) => t.status !== "Open"));

async function addTodo() {
	if (!newText.value.trim() || saving.value) return;
	saving.value = true;
	try {
		await saveTodo({
			description: newText.value.trim(),
			priority: newPriority.value,
			date: newDate.value || undefined,
		});
		newText.value = "";
		newPriority.value = "Medium";
		newDate.value = "";
		await load();
	} catch (e) {
		showToast(e.message || "Could not add the to-do", "error");
	} finally {
		saving.value = false;
	}
}

async function toggle(t) {
	try {
		await setTodoStatus(t.name, t.status === "Open" ? "Closed" : "Open");
		await load();
	} catch (e) {
		showToast(e.message || "Could not update the to-do", "error");
	}
}

function startEdit(t) {
	editId.value = t.name;
	editText.value = t.description;
	editPriority.value = t.priority || "Medium";
	editDate.value = t.date || "";
}
function cancelEdit() {
	editId.value = null;
}
async function saveEdit(t) {
	if (!editText.value.trim()) return;
	try {
		await saveTodo({
			name: t.name,
			description: editText.value.trim(),
			priority: editPriority.value,
			date: editDate.value || undefined,
		});
		editId.value = null;
		await load();
	} catch (e) {
		showToast(e.message || "Could not save the to-do", "error");
	}
}

async function remove(t) {
	const ok = await confirmDialog({
		title: "Delete to-do?",
		message: `Delete “${t.description}”? This can't be undone.`,
		confirmLabel: "Delete",
		destructive: true,
	});
	if (!ok) return;
	try {
		await deleteTodo(t.name);
		await load();
	} catch (e) {
		showToast(e.message || "Could not delete the to-do", "error");
	}
}

const PRIORITY_TONE = {
	High: "bg-danger-50 text-danger-700",
	Medium: "bg-warning-50 text-warning-700",
	Low: "bg-ink-100 text-ink-600",
};
const breadcrumbs = [{ label: "BuildSuite Core", to: "/" }, { label: "To-dos" }];
</script>

<template>
	<DeskPage title="To-dos" subtitle="Your personal to-do list" :breadcrumbs="breadcrumbs">
		<div class="max-w-2xl mx-auto">
			<!-- Add -->
			<form
				class="flex items-end gap-2 flex-wrap bg-ink-50 border border-ink-200 rounded-lg px-3 py-2.5 mb-4"
				@submit.prevent="addTodo"
			>
				<input
					v-model="newText"
					type="text"
					placeholder="Add a to-do…"
					class="flex-1 min-w-[12rem] text-sm px-2.5 py-1.5 border border-ink-200 rounded-md bg-white text-ink-900 focus:outline-none focus:ring-2 focus:ring-brand-200 focus:border-brand-400"
				/>
				<DeskSelect v-model="newPriority" class="!w-28">
					<option value="High">High</option>
					<option value="Medium">Medium</option>
					<option value="Low">Low</option>
				</DeskSelect>
				<input
					v-model="newDate"
					type="date"
					title="Due date (optional)"
					class="text-sm px-2 py-1.5 border border-ink-200 rounded-md bg-white text-ink-900 focus:outline-none focus:ring-2 focus:ring-brand-200"
				/>
				<button
					type="submit"
					class="desk-save-btn text-sm"
					:disabled="!newText.trim() || saving"
					:class="{ 'opacity-50 cursor-not-allowed': !newText.trim() || saving }"
				>
					{{ saving ? "Adding…" : "Add" }}
				</button>
			</form>

			<div v-if="loading" class="py-16 text-center text-sm text-ink-400">Loading…</div>

			<template v-else>
				<!-- Open -->
				<div v-if="openTodos.length" class="border border-ink-200 rounded-lg overflow-hidden mb-4">
					<div
						v-for="(t, i) in openTodos"
						:key="t.name"
						class="flex items-start gap-3 px-3 py-2.5"
						:class="i ? 'border-t border-ink-100' : ''"
					>
						<button
							type="button"
							class="mt-0.5 w-4 h-4 rounded border border-ink-300 hover:border-brand-500 shrink-0"
							title="Mark done"
							@click="toggle(t)"
						></button>

						<template v-if="editId === t.name">
							<div class="flex-1 flex items-end gap-2 flex-wrap">
								<input
									v-model="editText"
									type="text"
									class="flex-1 min-w-[10rem] text-sm px-2 py-1 border border-ink-200 rounded-md bg-white text-ink-900 focus:outline-none focus:ring-2 focus:ring-brand-200"
									@keyup.enter="saveEdit(t)"
								/>
								<DeskSelect v-model="editPriority" class="!w-24">
									<option value="High">High</option>
									<option value="Medium">Medium</option>
									<option value="Low">Low</option>
								</DeskSelect>
								<input v-model="editDate" type="date" class="text-xs px-2 py-1 border border-ink-200 rounded-md bg-white" />
								<button type="button" class="text-xs desk-save-btn" @click="saveEdit(t)">Save</button>
								<button type="button" class="text-xs text-ink-500 hover:underline" @click="cancelEdit">Cancel</button>
							</div>
						</template>

						<template v-else>
							<div class="flex-1 min-w-0">
								<div class="text-sm text-ink-900 break-words">{{ t.description }}</div>
								<div class="flex items-center gap-2 mt-1">
									<span class="text-[10px] px-1.5 py-0.5 rounded-full" :class="PRIORITY_TONE[t.priority] || PRIORITY_TONE.Medium">{{ t.priority || "Medium" }}</span>
									<span v-if="t.date" class="text-[11px] text-ink-500">Due {{ t.date }}</span>
									<span v-if="t.reference_type" class="text-[11px] text-ink-400">· {{ t.reference_type }} {{ t.reference_name }}</span>
								</div>
							</div>
							<div class="flex items-center gap-2 shrink-0">
								<button type="button" class="text-[11px] text-ink-500 hover:text-ink-900" @click="startEdit(t)">Edit</button>
								<button type="button" class="text-[11px] text-danger-600 hover:underline" @click="remove(t)">Delete</button>
							</div>
						</template>
					</div>
				</div>
				<div v-else class="text-sm text-ink-400 italic py-8 text-center">Nothing to do — you're all caught up.</div>

				<!-- Done -->
				<div v-if="doneTodos.length">
					<h2 class="text-[11px] font-semibold uppercase tracking-wider text-ink-500 mb-2">Done ({{ doneTodos.length }})</h2>
					<div class="border border-ink-200 rounded-lg overflow-hidden">
						<div
							v-for="(t, i) in doneTodos"
							:key="t.name"
							class="flex items-center gap-3 px-3 py-2"
							:class="i ? 'border-t border-ink-100' : ''"
						>
							<button
								type="button"
								class="w-4 h-4 rounded bg-brand-600 text-white flex items-center justify-center shrink-0 text-[10px]"
								title="Reopen"
								@click="toggle(t)"
							>✓</button>
							<div class="flex-1 min-w-0 text-sm text-ink-400 line-through break-words">{{ t.description }}</div>
							<button type="button" class="text-[11px] text-danger-600 hover:underline shrink-0" @click="remove(t)">Delete</button>
						</div>
					</div>
				</div>
			</template>
		</div>
	</DeskPage>
</template>
