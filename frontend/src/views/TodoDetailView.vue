<script setup>
// To-do — one to-do, as a page (S365). A route rather than a modal: a notification can link
// straight at it, and a full page beats a dialog on a phone. Shows the to-do's Frappe activity
// timeline (creation, tracked field changes, comments) from api.todo.get_todo.
import { ref, computed, watch } from "vue";
import { useRouter } from "vue-router";
import { showToast } from "@/utils/appToast";
import { useConfirm } from "@/composables/useConfirm";
import { TODO_STATUSES, todoTitle, todoBody, todoDue, todoReference } from "@/data/todo";
import { getTodo, setTodoStatus, deleteTodo } from "@/data/todoApi";
import { __ } from "@/utils/translate";
import { fmtDate } from "@/utils/format";
import { useDataStore } from "@/stores";
import ToDoFormModal from "@/components/todo/ToDoFormModal.vue";
import StatusBadge from "@/components/StatusBadge.vue";
import UserAvatar from "@/components/UserAvatar.vue";
import WorkspaceIcon from "@/components/WorkspaceIcon.vue";

const props = defineProps({ id: { type: String, required: true } });

const router = useRouter();
const confirmDialog = useConfirm();
const store = useDataStore();

const todo = ref(null);
const activity = ref([]);
const loading = ref(true);
const notFound = ref(false);
const editOpen = ref(false);
const savingStatus = ref(false);

const today = computed(() => {
	const d = new Date();
	const p = (n) => String(n).padStart(2, "0");
	return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`;
});

const title = computed(() => todoTitle(todo.value, 200));
const body = computed(() => todoBody(todo.value));
const due = computed(() => todoDue(todo.value, today.value));
const reference = computed(() => todoReference(todo.value));

// Activity newest-first — the latest thing that happened reads first.
const timeline = computed(() => [...activity.value].reverse());

// WorkspaceIcon slug per activity action (all confirmed present in the app's icon set).
const ACTION_ICON = {
	created: "flag",
	status: "check-circle",
	due: "calendar",
	assigned: "users-2",
	edited: "pencil",
	comment: "message-circle",
	info: "pencil",
};

// Datetimes come back as "YYYY-MM-DD HH:MM:SS" — normalise to ISO so every browser parses it.
function when(dt) {
	return dt ? fmtDate(String(dt).replace(" ", "T")) : "";
}

async function load() {
	loading.value = true;
	notFound.value = false;
	try {
		const res = await getTodo(props.id);
		todo.value = res.todo;
		activity.value = res.activity || [];
		// Opening a to-do marks it read server-side (its _seen) — refresh the top-nav badge.
		store.loadTodoCount?.();
	} catch {
		notFound.value = true;
		todo.value = null;
	} finally {
		loading.value = false;
	}
}
watch(() => props.id, load, { immediate: true });

async function onStatus(e) {
	const status = e.target.value;
	savingStatus.value = true;
	try {
		await setTodoStatus(props.id, status);
		await load();
	} catch (err) {
		showToast(err.message || "Could not update the to-do", "error");
	} finally {
		savingStatus.value = false;
	}
}

function onEdited() {
	editOpen.value = false;
	load();
}

async function remove() {
	const ok = await confirmDialog({
		title: __("Delete this to-do"),
		message: __(
			'Delete "{0}"?\n\nThis removes it for everyone, including whoever it\'s assigned to. If you only want to stop work on it, cancel it instead — that keeps the record that it was raised.',
			[title.value]
		),
		confirmLabel: __("Delete"),
		destructive: true,
	});
	if (!ok) return;
	try {
		await deleteTodo(props.id);
		store.loadTodoCount?.();
		router.push({ name: "todo" });
	} catch (err) {
		showToast(err.message || __("Could not delete the to-do"), "error");
	}
}
</script>

<template>
	<div class="max-w-3xl mx-auto px-3 sm:px-5 py-4 sm:py-6">
		<RouterLink
			:to="{ name: 'todo' }"
			class="inline-flex items-center gap-1.5 text-xs text-ink-600 hover:text-ink-900 mb-3"
		>
			<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
				<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
			</svg>
			{{ __("All to-dos") }}
		</RouterLink>

		<div v-if="loading" class="text-sm text-ink-500 px-1 py-14 text-center">{{ __("Loading…") }}</div>

		<div
			v-else-if="notFound || !todo"
			class="border border-dashed border-ink-200 rounded-xl px-4 py-14 text-center"
		>
			<div class="text-sm text-ink-700">{{ __("That to-do is not here.") }}</div>
			<div class="text-xs text-ink-500 mt-1">
				{{ __("It may have been deleted, or it belongs to someone else.") }}
			</div>
		</div>

		<template v-else>
			<!-- Head -->
			<div class="bg-white border border-ink-200 rounded-xl overflow-hidden">
				<div class="px-4 sm:px-5 py-4">
					<div class="flex flex-wrap items-center gap-2 mb-2">
						<StatusBadge :status="todo.status" size="xs" />
						<StatusBadge :status="todo.priority" size="xs" />
						<span
							v-if="due"
							class="text-[11px] px-2 py-0.5 rounded-full"
							:class="
								due.tone === 'overdue'
									? 'bg-danger-50 text-danger-700'
									: due.tone === 'today'
										? 'bg-warning-50 text-warning-700'
										: 'bg-ink-100 text-ink-600'
							"
						>
							{{ due.text || fmtDate(todo.date) }}
						</span>
						<span class="text-[11px] text-ink-500 font-mono ml-auto">{{ todo.name }}</span>
					</div>

					<h1 class="text-base sm:text-lg font-semibold text-ink-900 leading-snug">
						{{ title }}
					</h1>
					<p
						v-if="body"
						class="text-sm text-ink-700 whitespace-pre-line leading-relaxed mt-2"
					>
						{{ body }}
					</p>

					<RouterLink
						v-if="reference && reference.to"
						:to="reference.to"
						class="inline-flex items-center gap-2 mt-3 text-xs bg-ink-50 border border-ink-200 rounded-lg px-3 py-2 hover:border-brand-400"
					>
						<WorkspaceIcon :slug="reference.icon" :size="14" class="text-ink-500 shrink-0" />
						<span class="text-ink-900 font-medium truncate">{{ reference.label }}</span>
						<span class="text-ink-500 shrink-0">{{ __(reference.type) }} →</span>
					</RouterLink>
				</div>

				<!-- Facts -->
				<dl
					class="px-4 sm:px-5 py-3 border-t border-ink-100 grid grid-cols-2 sm:grid-cols-4 gap-y-3 gap-x-4"
				>
					<div>
						<dt class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">
							{{ __("Assigned to") }}
						</dt>
						<dd class="flex items-center gap-1.5 mt-1 min-w-0">
							<UserAvatar
								v-if="todo.allocated_to"
								:user-id="todo.allocated_to"
								size="xs"
								class="shrink-0"
							/>
							<span class="text-sm text-ink-900 truncate">
								{{ todo.allocated_to_name || __("Nobody") }}
							</span>
						</dd>
					</div>
					<div>
						<dt class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">
							{{ __("Raised by") }}
						</dt>
						<dd class="flex items-center gap-1.5 mt-1 min-w-0">
							<UserAvatar
								v-if="todo.assigned_by"
								:user-id="todo.assigned_by"
								size="xs"
								class="shrink-0"
							/>
							<span class="text-sm text-ink-900 truncate">
								{{ todo.assigned_by_name || "—" }}
							</span>
						</dd>
					</div>
					<div>
						<dt class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">
							{{ __("Due") }}
						</dt>
						<dd class="text-sm text-ink-900 mt-1">
							{{ todo.date ? fmtDate(todo.date) : __("No due date") }}
						</dd>
					</div>
					<div>
						<dt class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">
							{{ __("Raised") }}
						</dt>
						<dd class="text-sm text-ink-900 mt-1">{{ when(todo.created_at) }}</dd>
					</div>
				</dl>

				<!-- Actions. Status first: it's what people come here to change. -->
				<div
					class="px-4 sm:px-5 py-3 border-t border-ink-100 flex flex-wrap items-center gap-2"
				>
					<label class="text-xs text-ink-600 shrink-0" for="todo-status">{{ __("Status") }}</label>
					<select
						id="todo-status"
						class="desk-input !w-auto"
						:value="todo.status"
						:disabled="savingStatus"
						@change="onStatus"
					>
						<option v-for="s in TODO_STATUSES" :key="s" :value="s">{{ __(s) }}</option>
					</select>
					<button
						type="button"
						class="ml-auto text-xs font-medium px-3 py-1.5 border border-ink-200 bg-white text-ink-700 hover:bg-ink-50 rounded-md"
						@click="editOpen = true"
					>
						{{ __("Edit") }}
					</button>
					<button
						type="button"
						class="text-xs font-medium px-3 py-1.5 border border-danger-200 text-danger-700 hover:bg-danger-50 rounded-md"
						@click="remove"
					>
						{{ __("Delete") }}
					</button>
				</div>
			</div>

			<!-- Activity -->
			<section class="mt-4 bg-white border border-ink-200 rounded-xl overflow-hidden">
				<header
					class="px-4 sm:px-5 py-2.5 bg-gradient-to-r from-brand-50 to-white border-b border-ink-100"
				>
					<h2 class="text-[11px] uppercase tracking-wider text-ink-600 font-medium">
						{{ __("Activity") }}
					</h2>
				</header>
				<div v-if="!timeline.length" class="px-4 sm:px-5 py-6 text-sm text-ink-500">
					{{ __("Nothing has happened to this to-do yet.") }}
				</div>
				<ul v-else class="divide-y divide-ink-100">
					<li v-for="a in timeline" :key="a.id" class="px-4 sm:px-5 py-3 flex gap-3">
						<span
							class="w-7 h-7 rounded-lg flex items-center justify-center shrink-0 mt-0.5"
							:class="a.is_comment ? 'bg-brand-50 text-brand-700' : 'bg-ink-50 text-ink-600'"
						>
							<WorkspaceIcon :slug="ACTION_ICON[a.action] || 'pencil'" :size="13" />
						</span>
						<div class="min-w-0 flex-1">
							<div
								class="text-sm"
								:class="a.is_comment ? 'text-ink-900 whitespace-pre-line' : 'text-ink-700'"
							>
								<span class="font-medium text-ink-900">{{ a.by_name || __("Someone") }}</span>
								<template v-if="!a.is_comment"> {{ a.text }}</template>
							</div>
							<div
								v-if="a.is_comment"
								class="text-sm text-ink-700 whitespace-pre-line mt-0.5"
							>
								{{ a.text }}
							</div>
							<div class="text-[11px] text-ink-500 mt-0.5">{{ when(a.at) }}</div>
						</div>
					</li>
				</ul>
			</section>

			<ToDoFormModal
				:open="editOpen"
				:todo="todo"
				@close="editOpen = false"
				@saved="onEdited"
			/>
		</template>
	</div>
</template>
