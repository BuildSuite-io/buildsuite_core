<script setup>
import { ref, computed } from "vue";
import { RouterLink } from "vue-router";
import { useDataStore } from "@/stores";
import StatusBadge from "@/components/StatusBadge.vue";

const store = useDataStore();
const selectedProject = ref(store.rootProjects[0]?.id || "");
const view = ref("work-packages"); // 'work-packages' or 'tasks'

// Get all items (WP or tasks) for selected project + subprojects
const items = computed(() => {
	if (!selectedProject.value) return [];
	if (view.value === "work-packages") {
		return store
			.workPackagesByProject(selectedProject.value)
			.filter((wp) => wp.startDate && wp.endDate);
	} else {
		return store.tasksByProject(selectedProject.value).filter((t) => t.startDate && t.endDate);
	}
});

// Compute date range
const range = computed(() => {
	if (!items.value.length) return null;
	let min = Infinity,
		max = -Infinity;
	for (const i of items.value) {
		const s = new Date(i.startDate).getTime();
		const e = new Date(i.endDate).getTime();
		if (s < min) min = s;
		if (e > max) max = e;
	}
	// Pad with a few days
	min -= 86400000 * 3;
	max += 86400000 * 3;
	return { min, max, span: max - min };
});

function pct(d) {
	if (!range.value) return 0;
	return ((new Date(d).getTime() - range.value.min) / range.value.span) * 100;
}
function width(s, e) {
	if (!range.value) return 0;
	return ((new Date(e).getTime() - new Date(s).getTime()) / range.value.span) * 100;
}

// Month headers
const months = computed(() => {
	if (!range.value) return [];
	const out = [];
	const start = new Date(range.value.min);
	start.setDate(1);
	const end = new Date(range.value.max);
	const cursor = new Date(start);
	while (cursor <= end) {
		const monthStart = new Date(cursor.getFullYear(), cursor.getMonth(), 1);
		const monthEnd = new Date(cursor.getFullYear(), cursor.getMonth() + 1, 0);
		out.push({
			label: monthStart.toLocaleDateString("en-IN", { month: "short", year: "2-digit" }),
			start: pct(monthStart),
			width: width(monthStart, monthEnd),
		});
		cursor.setMonth(cursor.getMonth() + 1);
	}
	return out;
});

const today = computed(() => pct(new Date().toISOString().slice(0, 10)));

function barColor(item) {
	if (item.status === "Completed") return "bg-success-500";
	if (item.status === "In Progress") return "bg-brand-500";
	if (item.status === "On Hold") return "bg-warning-500";
	if (item.status === "Cancelled") return "bg-ink-400";
	return "bg-ink-300";
}
</script>

<template>
	<div class="px-6 py-4">
		<div class="flex items-center justify-between mb-4">
			<div>
				<h1 class="text-lg font-semibold text-ink-900">Schedule</h1>
				<p class="text-xs text-ink-500 mt-0.5">Gantt-style timeline view</p>
			</div>
		</div>

		<!-- Controls -->
		<div class="card rounded-b-none border-b-0 px-3 py-2 flex items-center gap-3 flex-wrap">
			<div class="flex items-center gap-2">
				<label class="text-xs text-ink-500">Project</label>
				<select
					v-model="selectedProject"
					class="text-xs px-2 py-1.5 border border-ink-200 rounded bg-white"
				>
					<option v-for="p in store.rootProjects" :key="p.id" :value="p.id">
						{{ p.name }}
					</option>
				</select>
			</div>
			<div class="flex border border-ink-200 rounded overflow-hidden">
				<button
					@click="view = 'work-packages'"
					:class="
						view === 'work-packages'
							? 'bg-brand-50 text-brand-700'
							: 'bg-white text-ink-600'
					"
					class="px-3 py-1 text-xs"
				>
					Work Packages
				</button>
				<button
					@click="view = 'tasks'"
					:class="
						view === 'tasks' ? 'bg-brand-50 text-brand-700' : 'bg-white text-ink-600'
					"
					class="px-3 py-1 text-xs border-l border-ink-200"
				>
					Tasks
				</button>
			</div>
			<div class="ml-auto text-xs text-ink-500">{{ items.length }} items</div>
		</div>

		<!-- Gantt -->
		<div class="card rounded-t-none overflow-hidden">
			<div v-if="!items.length" class="p-10 text-center text-sm text-ink-400">
				No scheduled items for this view.
			</div>
			<div v-else>
				<!-- Month headers -->
				<div class="flex border-b border-ink-200 bg-ink-50 h-8 relative">
					<div
						class="w-72 flex-shrink-0 border-r border-ink-200 px-3 py-1.5 text-[11px] uppercase tracking-wider text-ink-500 font-medium"
					>
						Item
					</div>
					<div class="flex-1 relative">
						<div
							v-for="(m, i) in months"
							:key="i"
							class="absolute top-0 bottom-0 border-r border-ink-200 px-2 py-1.5 text-[11px] text-ink-500 font-medium overflow-hidden whitespace-nowrap"
							:style="`left:${m.start}%; width:${m.width}%`"
						>
							{{ m.label }}
						</div>
					</div>
				</div>

				<!-- Rows -->
				<div class="divide-y divide-ink-100">
					<div
						v-for="item in items"
						:key="item.id"
						class="flex hover:bg-ink-50 h-10 items-center"
					>
						<div
							class="w-72 flex-shrink-0 border-r border-ink-200 px-3 truncate text-sm text-ink-900"
						>
							{{ item.name }}
						</div>
						<div class="flex-1 relative h-full">
							<!-- Today line -->
							<div
								class="absolute top-0 bottom-0 w-px bg-danger-500/40 z-10"
								:style="`left:${today}%`"
							></div>
							<!-- Bar -->
							<div
								class="absolute top-1.5 bottom-1.5 rounded flex items-center text-[10px] text-white px-1.5 overflow-hidden font-medium"
								:class="barColor(item)"
								:style="`left:${pct(item.startDate)}%; width:${width(
									item.startDate,
									item.endDate
								)}%`"
								:title="`${item.name} · ${item.startDate} → ${item.endDate} · ${item.progress}%`"
							>
								<span class="truncate">{{ item.progress }}%</span>
							</div>
						</div>
					</div>
				</div>

				<!-- Legend -->
				<div
					class="px-4 py-2 bg-ink-50 border-t border-ink-200 flex items-center gap-4 text-xs text-ink-600"
				>
					<div class="flex items-center gap-1.5">
						<span class="w-3 h-3 rounded bg-success-500"></span>Completed
					</div>
					<div class="flex items-center gap-1.5">
						<span class="w-3 h-3 rounded bg-brand-500"></span>In Progress
					</div>
					<div class="flex items-center gap-1.5">
						<span class="w-3 h-3 rounded bg-ink-300"></span>Planned / Open
					</div>
					<div class="flex items-center gap-1.5">
						<span class="w-3 h-3 rounded bg-warning-500"></span>On Hold
					</div>
					<div class="ml-auto flex items-center gap-1.5">
						<span class="w-px h-3 bg-danger-500/60"></span>Today
					</div>
				</div>
			</div>
		</div>
	</div>
</template>
