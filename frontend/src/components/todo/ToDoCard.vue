<script setup>
// One to-do, on the board (card) or in the list (row) — one component, two shapes, so a card and a
// row can never disagree. Ported from the prototype (S365); the enriched todo carries its own
// assignee name + reference label, so no store lookups here.
import { computed } from "vue";
import { todoTitle, todoDue, todoReference, TODO_BOARD_STATUSES, TODO_DONE_STATUSES } from "@/data/todo";
import UserAvatar from "@/components/UserAvatar.vue";
import WorkspaceIcon from "@/components/WorkspaceIcon.vue";
import StatusBadge from "@/components/StatusBadge.vue";
import { fmtDate } from "@/utils/format";

const props = defineProps({
	todo: { type: Object, required: true },
	variant: { type: String, default: "card" }, // 'card' (board) | 'row' (list)
	today: { type: String, required: true },
});
const emit = defineEmits(["advance", "open", "dragstart", "dragend"]);

const title = computed(() => todoTitle(props.todo, props.variant === "row" ? 140 : 90));
const due = computed(() => todoDue(props.todo, props.today));
const reference = computed(() => todoReference(props.todo));
const isDone = computed(() => TODO_DONE_STATUSES.includes(props.todo.status));

const PRIORITY_EDGE = { High: "bg-danger-500", Medium: "bg-warning-500", Low: "bg-ink-300" };
const edge = computed(() => PRIORITY_EDGE[props.todo.priority] || "bg-ink-300");

const DUE_TONE = {
	overdue: "bg-danger-50 text-danger-700",
	today: "bg-warning-50 text-warning-700",
	soon: "bg-ink-100 text-ink-600",
	later: "bg-ink-100 text-ink-600",
};

const nextStatus = computed(() => {
	const i = TODO_BOARD_STATUSES.indexOf(props.todo.status);
	if (i === -1 || i === TODO_BOARD_STATUSES.length - 1) return null;
	return TODO_BOARD_STATUSES[i + 1];
});
</script>

<template>
	<article
		class="group relative bg-white border border-ink-200 rounded-lg overflow-hidden hover:border-brand-400 transition-colors"
		:class="[
			variant === 'row' ? 'flex items-center gap-3 pl-3 pr-2 py-2.5' : 'p-3 pl-4',
			isDone ? 'opacity-70' : '',
		]"
		draggable="true"
		@dragstart="emit('dragstart', todo)"
		@dragend="emit('dragend')"
	>
		<span class="absolute left-0 inset-y-0 w-1" :class="edge" :title="`${todo.priority} priority`"></span>

		<!-- ROW -->
		<template v-if="variant === 'row'">
			<button
				type="button"
				class="flex-1 min-w-0 text-left flex flex-col justify-center min-h-[40px]"
				@click="emit('open', todo)"
			>
				<div class="text-sm text-ink-900 font-medium truncate" :class="isDone ? 'line-through decoration-ink-400' : ''">{{ title }}</div>
				<div class="flex items-center gap-2 mt-0.5 text-[11px] text-ink-500 min-w-0">
					<span v-if="due" class="px-1.5 py-0.5 rounded-full shrink-0" :class="DUE_TONE[due.tone]">{{ due.text || todo.date }}</span>
					<span v-else-if="todo.date" class="shrink-0">{{ fmtDate(todo.date) }}</span>
					<RouterLink
						v-if="reference"
						:to="reference.to || ''"
						class="flex items-center gap-1 min-w-0 shrink hover:text-brand-700"
						@click.stop
					>
						<WorkspaceIcon :slug="reference.icon" :size="11" class="shrink-0" />
						<span class="truncate">{{ reference.label }}</span>
					</RouterLink>
				</div>
			</button>
			<StatusBadge :status="todo.status" size="xs" class="shrink-0 hidden sm:inline-flex" />
			<UserAvatar v-if="todo.allocated_to" :user-id="todo.allocated_to" size="xs" class="shrink-0" :title="todo.allocated_to_name" />
			<button
				v-if="nextStatus"
				type="button"
				class="shrink-0 w-9 h-9 flex items-center justify-center rounded-lg text-ink-500 hover:text-brand-700 hover:bg-brand-50"
				:title="`Move to ${nextStatus}`"
				:aria-label="`Move to ${nextStatus}`"
				@click.stop="emit('advance', todo)"
			>
				<WorkspaceIcon slug="check-circle" :size="16" />
			</button>
		</template>

		<!-- CARD -->
		<template v-else>
			<button type="button" class="w-full text-left" @click="emit('open', todo)">
				<div class="text-sm text-ink-900 leading-snug" :class="isDone ? 'line-through decoration-ink-400' : ''">{{ title }}</div>
				<div v-if="reference" class="flex items-center gap-1 mt-2 text-[11px] text-ink-500 min-w-0">
					<WorkspaceIcon :slug="reference.icon" :size="11" class="shrink-0" />
					<span class="truncate">{{ reference.label }}</span>
				</div>
			</button>
			<div class="flex items-center gap-2 mt-2.5">
				<span v-if="due" class="text-[11px] px-1.5 py-0.5 rounded-full shrink-0" :class="DUE_TONE[due.tone]">{{ due.text || todo.date }}</span>
				<span class="flex-1"></span>
				<UserAvatar v-if="todo.allocated_to" :user-id="todo.allocated_to" size="xs" class="shrink-0" :title="todo.allocated_to_name" />
				<button
					v-if="nextStatus"
					type="button"
					class="shrink-0 w-8 h-8 flex items-center justify-center rounded-lg text-ink-500 hover:text-brand-700 hover:bg-brand-50"
					:title="`Move to ${nextStatus}`"
					:aria-label="`Move to ${nextStatus}`"
					@click.stop="emit('advance', todo)"
				>
					<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" /></svg>
				</button>
			</div>
		</template>
	</article>
</template>
