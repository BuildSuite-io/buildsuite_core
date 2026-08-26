<script setup>
// Insights (first layer) — ask a plain question, get a report built from live
// data, then reshape it with a follow-up or the viz switcher.
//
// The "AI" here is a LOCAL parser (data/insightEngine.js) that maps a prompt to
// a QuerySpec, run by an executor over the Core-5 datasets (useInsightsData).
// No model call, so nothing is invented — every figure is a real record, and an
// unrecognised prompt says so. In production the parser is the one piece a model
// replaces, returning the same spec.
import { ref, computed, onMounted } from "vue";
import { useRoute, useRouter } from "vue-router";

import { useDataStore } from "@/stores";
import DeskPage from "@/components/desk/DeskPage.vue";
import { fmtINR, fmtCompactINR } from "@/utils/format";
import { useInsightsData } from "@/composables/useInsightsData";
import {
	VIZ,
	SUGGESTIONS,
	availableDatasets,
	availablePresets,
	parsePrompt,
	refineWithStore,
	runSpec,
	describeSpec,
} from "@/data/insightEngine";

const store = useDataStore();
const route = useRoute();
const router = useRouter();
const { ctx, loading } = useInsightsData();

// First layer: leadership only (Director / PM / Administrator). Each dataset also
// respects the persona's own read permissions, so users only see allowed numbers.
const LEADERSHIP = ["director", "pm", "admin", "bsa"];
const canUseInsights = computed(() => LEADERSHIP.includes(store.role));

const breadcrumbs = [{ label: "BuildSuite Core", to: "/" }, { label: "Insights" }];

const prompt = ref("");
const refinePrompt = ref("");
const spec = ref(null);
const notice = ref("");
const noticeTone = ref("info");
const history = ref([]);
const presetsOpen = ref(true);
const page = ref(0);
const PAGE_SIZE = 25;

function setNotice(msg, tone = "info") {
	notice.value = msg;
	noticeTone.value = tone;
}

const PRESETS = computed(() => availablePresets(ctx.value));
const datasetNames = computed(() => availableDatasets(ctx.value).map(([, d]) => d.label.toLowerCase()));

function ask() {
	const text = prompt.value.trim();
	if (!text) return;
	const s = parsePrompt(text, ctx.value);
	if (!s) {
		setNotice(`Couldn't tell which records you mean. Try naming one: ${datasetNames.value.join(", ")}.`, "warn");
		return;
	}
	history.value = [];
	spec.value = s;
	page.value = 0;
	presetsOpen.value = false;
	setNotice(`Read as: ${(s.understood || []).join(" · ")}`);
	refinePrompt.value = "";
}

function refine() {
	const text = refinePrompt.value.trim();
	if (!text || !spec.value) return;
	const next = refineWithStore(spec.value, text, ctx.value);
	if (!next) {
		setNotice('Nothing in that changed the report. Try "as a pie", "top 5", "by month", "over 10000", "show all", or "clear filters".', "warn");
		return;
	}
	history.value.push(JSON.parse(JSON.stringify(spec.value)));
	spec.value = next;
	page.value = 0;
	setNotice(`Applied: ${(next.understood || []).join(" · ")}`);
	refinePrompt.value = "";
}

function undo() {
	const prev = history.value.pop();
	if (prev) {
		spec.value = prev;
		page.value = 0;
		setNotice("Reverted the last change.");
	}
}

function runPreset(p) {
	history.value = [];
	spec.value = JSON.parse(JSON.stringify(p.spec));
	prompt.value = p.prompt;
	page.value = 0;
	presetsOpen.value = false;
	setNotice(`Read as: ${describeSpec(p.spec)}`);
}

function clearReport() {
	spec.value = null;
	prompt.value = "";
	refinePrompt.value = "";
	presetsOpen.value = true;
	setNotice("");
}

function setViz(v) {
	if (!spec.value) return;
	spec.value = { ...spec.value, viz: v, mode: v === "table" && spec.value.mode === "list" ? "list" : "aggregate" };
}

const result = computed(() => {
	if (!spec.value || loading.value) return null;
	try {
		return runSpec(spec.value, ctx.value, { offset: page.value * PAGE_SIZE, pageSize: PAGE_SIZE });
	} catch {
		return null;
	}
});
const isMoney = computed(() => spec.value?.measure === "amount");
function fmtVal(v) {
	return isMoney.value ? fmtINR(v) : Number(v || 0).toLocaleString();
}
function fmtValShort(v) {
	return isMoney.value ? fmtCompactINR(v) : Number(v || 0).toLocaleString();
}

// --- chart geometry ---
const maxVal = computed(() => Math.max(1, ...(result.value?.rows || []).map((r) => r.value)));
const DONUT_COLORS = ["#16a34a", "#0ea5e9", "#f59e0b", "#8b5cf6", "#ef4444", "#14b8a6", "#ec4899", "#64748b"];
const donutArcs = computed(() => {
	const rows = result.value?.rows || [];
	const total = rows.reduce((a, r) => a + r.value, 0) || 1;
	let acc = 0;
	const C = 2 * Math.PI * 42;
	return rows.map((r, i) => {
		const frac = r.value / total;
		const arc = { ...r, color: DONUT_COLORS[i % DONUT_COLORS.length], dash: `${frac * C} ${C}`, offset: -acc * C, pct: frac * 100 };
		acc += frac;
		return arc;
	});
});
const linePoints = computed(() => {
	const rows = result.value?.rows || [];
	if (rows.length < 2) return "";
	const w = 640, h = 200, pad = 8;
	const max = Math.max(1, ...rows.map((r) => r.value));
	return rows
		.map((r, i) => {
			const x = pad + (i * (w - 2 * pad)) / (rows.length - 1);
			const y = h - pad - (r.value / max) * (h - 2 * pad);
			return `${x.toFixed(1)},${y.toFixed(1)}`;
		})
		.join(" ");
});

onMounted(() => {
	if (!canUseInsights.value) {
		router.replace("/");
		return;
	}
	const q = route.query.q;
	if (typeof q === "string" && q.trim()) {
		prompt.value = q.trim();
		ask();
	}
});
</script>

<template>
	<DeskPage title="Insights" subtitle="Ask a question of your data" :breadcrumbs="breadcrumbs">
		<div v-if="!canUseInsights" class="text-sm text-ink-500 py-10 text-center">
			Insights is available to leadership roles.
		</div>
		<div v-else class="space-y-4 max-w-5xl">
			<!-- Ask box -->
			<div class="flex items-center gap-2">
				<input
					v-model="prompt"
					type="text"
					placeholder="e.g. subcontractor bill value by subcontractor, top 8"
					class="flex-1 border border-ink-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-brand-400"
					@keyup.enter="ask"
				/>
				<button type="button" class="desk-save-btn" @click="ask">Ask</button>
			</div>

			<!-- Notice -->
			<div
				v-if="notice"
				class="text-xs px-3 py-2 rounded-md border"
				:class="
					noticeTone === 'warn'
						? 'bg-warning-50 border-warning-200 text-warning-700'
						: 'bg-brand-50/60 border-brand-100 text-brand-700'
				"
			>
				{{ notice }}
			</div>

			<!-- Suggestions (empty state) -->
			<div v-if="!spec" class="text-xs text-ink-500 flex flex-wrap items-center gap-1.5">
				<span class="text-ink-400">Try:</span>
				<button
					v-for="s in SUGGESTIONS"
					:key="s"
					type="button"
					class="px-2 py-1 border border-ink-200 rounded-full hover:border-brand-400 hover:bg-brand-50"
					@click="((prompt = s), ask())"
				>
					{{ s }}
				</button>
			</div>

			<!-- Presets -->
			<section v-if="presetsOpen" class="bg-white border border-ink-200 rounded-lg overflow-hidden">
				<div class="px-4 py-2.5 bg-ink-50 border-b border-ink-200">
					<h3 class="text-xs uppercase tracking-wider font-semibold text-ink-700">Starter questions</h3>
				</div>
				<div class="p-3 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
					<button
						v-for="p in PRESETS"
						:key="p.id"
						type="button"
						class="border border-ink-200 hover:border-brand-400 hover:bg-brand-50/40 rounded-lg px-3 py-2.5 text-left transition-colors"
						@click="runPreset(p)"
					>
						<div class="text-sm font-medium text-ink-900">{{ p.title }}</div>
						<div class="text-[11px] text-ink-500 mt-0.5">{{ p.prompt }}</div>
					</button>
				</div>
			</section>

			<div v-if="loading && spec" class="text-sm text-ink-500 italic py-10 text-center">Loading data…</div>

			<!-- Report -->
			<section v-if="spec && result && !loading" class="bg-white border border-ink-200 rounded-lg overflow-hidden">
				<div class="px-4 py-2.5 border-b border-ink-200 flex items-center justify-between gap-3 flex-wrap">
					<div>
						<h3 class="text-sm font-semibold text-ink-900">{{ describeSpec(spec) }}</h3>
						<div class="text-[11px] text-ink-500">
							{{ result.recordCount }} record{{ result.recordCount === 1 ? "" : "s" }} ·
							{{ result.measureLabel }} total {{ fmtVal(result.total) }}
						</div>
					</div>
					<div class="flex items-center gap-1">
						<button
							v-for="v in VIZ"
							:key="v"
							type="button"
							class="text-[11px] px-2 py-1 border rounded-md capitalize"
							:class="spec.viz === v ? 'bg-brand-600 border-brand-600 text-white' : 'border-ink-200 text-ink-600 hover:bg-ink-50'"
							@click="setViz(v)"
						>
							{{ v }}
						</button>
						<button type="button" class="text-[11px] px-2 py-1 border border-ink-200 rounded-md text-ink-600 hover:bg-ink-50 ml-1" @click="clearReport">
							Clear
						</button>
					</div>
				</div>

				<div class="p-4">
					<!-- KPI -->
					<div v-if="spec.viz === 'kpi'" class="py-8 text-center">
						<div class="text-4xl font-bold tabular-nums text-ink-900">{{ fmtVal(result.total) }}</div>
						<div class="text-xs text-ink-500 mt-1">{{ result.measureLabel }} · {{ result.datasetLabel }}</div>
					</div>

					<!-- Bar (horizontal) -->
					<div v-else-if="spec.viz === 'bar'" class="space-y-1.5">
						<div v-for="r in result.rows" :key="r.label" class="flex items-center gap-2 text-xs">
							<span class="w-40 shrink-0 truncate text-ink-600" :title="r.label">{{ r.label }}</span>
							<div class="flex-1 bg-ink-50 rounded h-5 overflow-hidden">
								<div class="h-full bg-brand-500 rounded" :style="`width:${Math.max(2, (r.value / maxVal) * 100)}%`"></div>
							</div>
							<span class="w-24 shrink-0 text-right tabular-nums text-ink-900">{{ fmtValShort(r.value) }}</span>
						</div>
					</div>

					<!-- Column (vertical) -->
					<div v-else-if="spec.viz === 'column'" class="flex items-end gap-2 h-56 pt-2">
						<div v-for="r in result.rows" :key="r.label" class="flex-1 flex flex-col items-center gap-1 min-w-0">
							<span class="text-[10px] tabular-nums text-ink-700">{{ fmtValShort(r.value) }}</span>
							<div class="w-full bg-brand-500 rounded-t" :style="`height:${Math.max(2, (r.value / maxVal) * 100)}%`"></div>
							<span class="text-[10px] text-ink-500 truncate w-full text-center" :title="r.label">{{ r.label }}</span>
						</div>
					</div>

					<!-- Line -->
					<svg v-else-if="spec.viz === 'line'" viewBox="0 0 640 200" class="w-full h-56">
						<polyline :points="linePoints" fill="none" stroke="#16a34a" stroke-width="2" stroke-linejoin="round" />
						<g v-for="(r, i) in result.rows" :key="r.label">
							<text :x="8 + (i * 624) / Math.max(1, result.rows.length - 1)" y="196" font-size="9" fill="#94a3b8" text-anchor="middle">{{ r.label }}</text>
						</g>
					</svg>

					<!-- Donut -->
					<div v-else-if="spec.viz === 'donut'" class="flex items-center gap-6 flex-wrap">
						<svg viewBox="0 0 100 100" class="w-40 h-40 -rotate-90 shrink-0">
							<circle cx="50" cy="50" r="42" fill="none" stroke="#f1f5f9" stroke-width="12" />
							<circle
								v-for="a in donutArcs"
								:key="a.label"
								cx="50"
								cy="50"
								r="42"
								fill="none"
								:stroke="a.color"
								stroke-width="12"
								:stroke-dasharray="a.dash"
								:stroke-dashoffset="a.offset"
							/>
						</svg>
						<div class="flex-1 min-w-[200px] space-y-1">
							<div v-for="a in donutArcs" :key="a.label" class="flex items-center gap-2 text-xs">
								<span class="w-2.5 h-2.5 rounded-sm shrink-0" :style="`background:${a.color}`"></span>
								<span class="flex-1 truncate text-ink-700" :title="a.label">{{ a.label }}</span>
								<span class="tabular-nums text-ink-900">{{ fmtValShort(a.value) }}</span>
								<span class="w-10 text-right tabular-nums text-ink-400">{{ a.pct.toFixed(0) }}%</span>
							</div>
						</div>
					</div>

					<!-- Table (aggregate) -->
					<table v-else-if="result.mode === 'aggregate'" class="w-full text-xs">
						<thead class="text-ink-500 uppercase tracking-wider text-[10px] border-b border-ink-100">
							<tr>
								<th class="text-left px-3 py-2">{{ result.dimensionLabel }}</th>
								<th class="text-right px-3 py-2">{{ result.measureLabel }}</th>
							</tr>
						</thead>
						<tbody>
							<tr v-for="r in result.rows" :key="r.label" class="border-b border-ink-100 last:border-0">
								<td class="px-3 py-1.5 text-ink-800">{{ r.label }}</td>
								<td class="px-3 py-1.5 text-right tabular-nums text-ink-900">{{ fmtVal(r.value) }}</td>
							</tr>
						</tbody>
					</table>

					<!-- Table (list / records) -->
					<div v-else>
						<table class="w-full text-xs">
							<thead class="text-ink-500 uppercase tracking-wider text-[10px] border-b border-ink-100">
								<tr>
									<th v-for="c in result.columns" :key="c.key" class="px-3 py-2" :class="c.align === 'right' ? 'text-right' : 'text-left'">
										{{ c.label }}
									</th>
								</tr>
							</thead>
							<tbody>
								<tr v-for="rec in result.records" :key="rec._k" class="border-b border-ink-100 last:border-0">
									<td
										v-for="c in result.columns"
										:key="c.key"
										class="px-3 py-1.5"
										:class="c.align === 'right' ? 'text-right tabular-nums text-ink-900' : 'text-ink-800'"
									>
										{{ c.money ? fmtINR(rec[c.key]) : rec[c.key] }}
									</td>
								</tr>
							</tbody>
						</table>
						<div v-if="result.recordCount > PAGE_SIZE" class="flex items-center justify-between mt-3 text-xs text-ink-500">
							<span>{{ page * PAGE_SIZE + 1 }}–{{ Math.min((page + 1) * PAGE_SIZE, result.recordCount) }} of {{ result.recordCount }}</span>
							<span class="flex gap-2">
								<button type="button" class="px-2 py-1 border border-ink-200 rounded disabled:opacity-40" :disabled="page === 0" @click="page--">Prev</button>
								<button
									type="button"
									class="px-2 py-1 border border-ink-200 rounded disabled:opacity-40"
									:disabled="(page + 1) * PAGE_SIZE >= result.recordCount"
									@click="page++"
								>
									Next
								</button>
							</span>
						</div>
					</div>

					<p v-if="result.truncated" class="text-[11px] text-ink-400 mt-2">
						+{{ result.truncated }} more not shown — say "show all" to include them.
					</p>
				</div>

				<!-- Refine -->
				<div class="px-4 py-2.5 border-t border-ink-200 bg-ink-50/40 flex items-center gap-2">
					<input
						v-model="refinePrompt"
						type="text"
						placeholder='Refine: "as a pie", "top 5", "by month", "over 100000", "clear filters"…'
						class="flex-1 border border-ink-200 rounded-md px-2.5 py-1.5 text-xs bg-white focus:outline-none focus:border-brand-400"
						@keyup.enter="refine"
					/>
					<button type="button" class="text-xs px-2.5 py-1.5 border border-ink-200 rounded-md bg-white hover:bg-ink-50" @click="refine">Refine</button>
					<button v-if="history.length" type="button" class="text-xs px-2.5 py-1.5 border border-ink-200 rounded-md bg-white hover:bg-ink-50" @click="undo">Undo</button>
				</div>
			</section>
		</div>
	</DeskPage>
</template>
