<script setup>
// A board — one column per stage, the cards in a slot, and optional drag-and-drop between
// columns (desktop). The column look matches the To-dos board; this is it as a shared component.
//
//   <DeskBoard :columns="[{ key: 'Open', label: __('Open'), items: [...], droppable: true }, …]"
//              :draggable="(item) => canMove(item)" @drop="({ item, to, column }) => …">
//     <template #card="{ item }"> … </template>
//   </DeskBoard>
//
// A drop on any column is emitted, droppable or not, so the page can say why a column refuses a
// card; only droppable columns light up as a target. `lockedText` labels the refusing columns
// while a card is being dragged (e.g. "Set by the system").
import { ref } from "vue";
import { __ } from "@/utils/translate";

const props = defineProps({
	columns: { type: Array, required: true }, // [{ key, label, items: [], droppable? }]
	itemKey: { type: String, default: "name" },
	draggable: { type: Function, default: null }, // (item) => bool; omit for a read-only board
	emptyText: { type: String, default: "" },
	lockedText: { type: String, default: "" },
});
const emit = defineEmits(["drop"]);

const dragging = ref(null);
const dropTarget = ref(null);

function canDrag(item) {
	return !!(props.draggable && props.draggable(item));
}

function onDragStart(event, item) {
	if (!canDrag(item)) return;
	dragging.value = item;
	event.dataTransfer.effectAllowed = "move";
	event.dataTransfer.setData("text/plain", String(item[props.itemKey]));
}

function onDragEnd() {
	dragging.value = null;
	dropTarget.value = null;
}

function onDrop(column) {
	const item = dragging.value;
	onDragEnd();
	if (item) emit("drop", { item, to: column.key, column });
}
</script>

<template>
	<div class="flex gap-3 overflow-x-auto snap-x snap-mandatory pb-2 -mx-3 px-3 sm:mx-0 sm:px-0">
		<section
			v-for="col in columns"
			:key="col.key"
			class="snap-start shrink-0 w-[82vw] sm:w-64 lg:w-auto lg:flex-1 lg:min-w-[10.5rem] flex flex-col rounded-xl border transition-colors"
			:class="
				dragging && dropTarget === col.key && col.droppable !== false
					? 'border-brand-400 bg-brand-50'
					: 'border-ink-200 bg-ink-100'
			"
			@dragover.prevent="dragging && (dropTarget = col.key)"
			@dragleave="dropTarget === col.key && (dropTarget = null)"
			@drop.prevent="onDrop(col)"
		>
			<header class="px-3 py-2.5 flex items-center gap-2 border-b border-ink-200">
				<span class="text-xs font-semibold uppercase tracking-wider text-ink-600">{{
					col.label
				}}</span>
				<span class="text-xs text-ink-600 tabular-nums ml-auto">{{
					col.items.length
				}}</span>
			</header>
			<p
				v-if="dragging && col.droppable === false && lockedText"
				class="px-3 pt-2 text-[11px] text-ink-500"
			>
				{{ lockedText }}
			</p>
			<div class="p-2 space-y-2 flex-1 min-h-[6rem]">
				<div
					v-for="item in col.items"
					:key="item[itemKey]"
					:draggable="canDrag(item)"
					@dragstart="onDragStart($event, item)"
					@dragend="onDragEnd"
				>
					<slot name="card" :item="item" :column="col" />
				</div>
				<p v-if="!col.items.length" class="text-xs text-ink-600 text-center py-6">
					{{ emptyText || __("Nothing here") }}
				</p>
			</div>
		</section>
	</div>
</template>
