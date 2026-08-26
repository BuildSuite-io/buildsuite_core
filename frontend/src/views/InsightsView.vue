<script setup>
// Insights — ask a question, get a report built from live data, then reshape it
// with follow-up prompts or the controls. Layout + styling match the prototype.
//
// The "AI" is a LOCAL parser (data/insightEngine.js) mapping a prompt to a
// QuerySpec, run by an executor over the live datasets (useInsightsData). No model
// call, so nothing is invented — every figure is a real record, and an unrecognised
// prompt says so. In production the parser is the one piece a model replaces.
//
// Charts follow the data-viz method: bar / column / line are ONE series, so they use
// a single hue (length carries magnitude, not colour). Only the donut is categorical.
import { ref, computed, onMounted } from "vue";
import { useRouter, useRoute } from "vue-router";

import { useDataStore } from "@/stores";
import DeskSearchableSelect from "@/components/desk/DeskSearchableSelect.vue";
import { fmtINR, fmtCompactINR } from "@/utils/format";
import { useInsightsData } from "@/composables/useInsightsData";
import {
	DATASETS,
	SUGGESTIONS,
	VIZ,
	availableDatasets,
	availablePresets,
	dimensionValues,
	parsePrompt,
	refineWithStore,
	runSpec,
	describeSpec,
} from "@/data/insightEngine";

const router = useRouter();
const route = useRoute();
const store = useDataStore();
const { ctx, loading } = useInsightsData();

// First layer: leadership only. Each dataset also respects the persona's own read
// permissions (via ctx's canRead gates), so users only see allowed numbers.
const canUseInsights = computed(() => ["director", "pm", "admin", "bsa"].includes(store.role));

onMounted(() => {
	if (!canUseInsights.value) return router.replace("/");
	// The Assistant hands a question over via ?q=. Run it on arrival so the deep
	// link lands on the report, not on an empty prompt box.
	const q = route.query.q;
	if (typeof q === "string" && q.trim()) {
		prompt.value = q.trim();
		ask();
		router.replace({ path: "/insights" });
	}
});

// --- prompt state --------------------------------------------------------
const prompt = ref("");
const refinePrompt = ref("");
const spec = ref(null);
const notice = ref(""); // what was understood, or why nothing happened
const noticeTone = ref("info");
const history = ref([]); // lets a refine be undone
// Presets answer "what could I look at", which competes with the data once
// something is on screen. They collapse when a report renders and come back when
// it's cleared; the user can still toggle either way.
const presetsOpen = ref(true);

function setNotice(msg, tone = "info") {
	notice.value = msg;
	noticeTone.value = tone;
}

// Generating state. Locally this resolves instantly, but in production the round
// trip is a model call plus a query, so the transition needs to be visible. Control
// changes (viz, paging, filters) skip it — a real system wouldn't re-call the model.
const busy = ref(false);
const busyStep = ref("");
const STEPS = ["Reading your question…", "Selecting records…", "Building the report…"];
function withProgress(fn) {
	busy.value = true;
	let i = 0;
	busyStep.value = STEPS[0];
	const tick = setInterval(() => {
		i = Math.min(i + 1, STEPS.length - 1);
		busyStep.value = STEPS[i];
	}, 220);
	setTimeout(() => {
		clearInterval(tick);
		busy.value = false;
		busyStep.value = "";
		fn();
	}, 700);
}

// Only ever offers what the signed-in role may read; the "didn't understand"
// message lists exactly that, not everything that exists.
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
	withProgress(() => {
		history.value = [];
		spec.value = s;
		page.value = 0;
		presetsOpen.value = false;
		setNotice(`Read as: ${(s.understood || []).join(" · ")}`);
		refinePrompt.value = "";
	});
}

function refine() {
	const text = refinePrompt.value.trim();
	if (!text || !spec.value) return;
	const next = refineWithStore(spec.value, text, ctx.value);
	if (!next) {
		setNotice('Nothing in that changed the report. Try "as a pie", "top 5", "by month", "over 10000", "show all", or "clear filters".', "warn");
		return;
	}
	withProgress(() => {
		history.value.push(JSON.parse(JSON.stringify(spec.value)));
		spec.value = next;
		page.value = 0;
		setNotice(`Applied: ${(next.understood || []).join(" · ")}`);
		refinePrompt.value = "";
	});
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
	withProgress(() => {
		history.value = [];
		spec.value = JSON.parse(JSON.stringify(p.spec));
		prompt.value = p.prompt;
		page.value = 0;
		presetsOpen.value = false;
		setNotice(`Preset: ${p.title}`);
	});
}

function useSuggestion(s) {
	prompt.value = s;
	ask();
}
function clearReport() {
	spec.value = null;
	prompt.value = "";
	notice.value = "";
	history.value = [];
	presetsOpen.value = true;
}

// --- scope + viz controls (the same edits, as controls) -------------------
const projectOptions = computed(() => ctx.value.rootProjects.map((p) => ({ value: p.id, label: p.name, hint: p.code })));
const scopeProject = computed({
	get: () => spec.value?.filters?.project || "",
	set: (v) => {
		if (!spec.value) return;
		const n = { ...spec.value, filters: { ...spec.value.filters } };
		if (v) n.filters.project = v;
		else delete n.filters.project;
		spec.value = n;
	},
});
function setViz(v) {
	if (spec.value) spec.value = { ...spec.value, viz: v };
}
function setDimension(d) {
	if (spec.value) spec.value = { ...spec.value, dimension: d };
}
const dimensionChoices = computed(() => {
	if (!spec.value) return [];
	return Object.entries(DATASETS[spec.value.source].dims).map(([k, v]) => ({ key: k, label: v.label }));
});

// --- filters (controls; the prompt sets the same fields) ------------------
function patchFilters(patch) {
	if (!spec.value) return;
	const f = { ...spec.value.filters, ...patch };
	for (const k of Object.keys(patch)) if (patch[k] === "" || patch[k] == null) delete f[k];
	spec.value = { ...spec.value, filters: f };
	page.value = 0;
}
const dimValues = computed(() => (spec.value ? dimensionValues(spec.value.source, ctx.value) : {}));
const filterDim = ref("");
const filterVal = ref("");
function addValueFilter() {
	if (!filterDim.value || !filterVal.value) return;
	patchFilters({ values: { ...(spec.value.filters.values || {}), [filterDim.value]: filterVal.value } });
	filterDim.value = "";
	filterVal.value = "";
}
function removeValueFilter(k) {
	const v = { ...(spec.value.filters.values || {}) };
	delete v[k];
	patchFilters({ values: Object.keys(v).length ? v : null });
}
// Every active filter as a removable chip, so nothing narrows the data invisibly —
// a report that silently excludes rows is a wrong report.
const activeChips = computed(() => {
	if (!spec.value) return [];
	const f = spec.value.filters || {};
	const out = [];
	if (f.project) out.push({ key: "project", label: `Project: ${ctx.value.projectById(f.project)?.name || f.project}` });
	if (f.from) out.push({ key: "from", label: `From ${f.from}` });
	if (f.to) out.push({ key: "to", label: `To ${f.to}` });
	if (f.min != null) out.push({ key: "min", label: `Over ${fmtINR(f.min)}` });
	if (f.max != null) out.push({ key: "max", label: `Under ${fmtINR(f.max)}` });
	if (f.q) out.push({ key: "q", label: `Contains "${f.q}"` });
	for (const [k, v] of Object.entries(f.values || {})) {
		out.push({ key: `v:${k}`, label: `${dimValues.value[k]?.label || k}: ${v}` });
	}
	return out;
});
function removeChip(key) {
	if (key.startsWith("v:")) return removeValueFilter(key.slice(2));
	patchFilters({ [key]: null });
}
function clearFilters() {
	if (!spec.value) return;
	spec.value = { ...spec.value, filters: {} };
	page.value = 0;
}

// --- paging ---------------------------------------------------------------
const page = ref(0);
const pageSize = ref(25);
const PAGE_SIZES = [25, 50, 100, 200];

// --- result ---------------------------------------------------------------
const result = computed(() => {
	if (!spec.value || loading.value) return null;
	try {
		return runSpec(spec.value, ctx.value, { offset: page.value * pageSize.value, pageSize: pageSize.value });
	} catch {
		return null;
	}
});
const pageCount = computed(() => {
	if (!result.value || result.value.mode !== "list") return 1;
	return Math.max(1, Math.ceil(result.value.recordCount / pageSize.value));
});
const rangeStart = computed(() => (result.value?.recordCount ? page.value * pageSize.value + 1 : 0));
const rangeEnd = computed(() => Math.min((page.value + 1) * pageSize.value, result.value?.recordCount || 0));
const title = computed(() => (spec.value ? describeSpec(spec.value) : ""));
const isMoney = computed(() => result.value?.measure === "amount");
function fmtValue(v) {
	return isMoney.value ? fmtINR(v) : Number.isInteger(v) ? v : v.toFixed(1);
}
function fmtValueShort(v) {
	return isMoney.value ? fmtCompactINR(v) : Number.isInteger(v) ? String(v) : v.toFixed(1);
}

// --- chart geometry -------------------------------------------------------
const maxValue = computed(() => Math.max(1, ...(result.value?.rows || []).map((r) => r.value)));
const hovered = ref(null);

const BAR_H = 26;
const barChart = computed(() => {
	const rows = result.value?.rows || [];
	return { rows, height: Math.max(60, rows.length * BAR_H + 8) };
});

const COL_W = 46;
const colChart = computed(() => {
	const rows = result.value?.rows || [];
	return { rows, width: Math.max(240, rows.length * COL_W + 40), height: 200 };
});

const lineChart = computed(() => {
	const rows = result.value?.rows || [];
	const w = Math.max(320, rows.length * 64);
	const h = 200,
		padL = 8,
		padR = 8,
		padT = 12,
		padB = 26;
	const innerW = w - padL - padR,
		innerH = h - padT - padB;
	const step = rows.length > 1 ? innerW / (rows.length - 1) : 0;
	const pts = rows.map((r, i) => ({
		...r,
		x: padL + (rows.length > 1 ? i * step : innerW / 2),
		y: padT + innerH - (r.value / maxValue.value) * innerH,
	}));
	return {
		rows: pts,
		w,
		h,
		padT,
		innerH,
		path: pts.map((p, i) => `${i ? "L" : "M"}${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(" "),
	};
});

// Donut — the only categorical form. Folds past 6 into "Other" rather than
// generating hues, and every slice is direct-labelled in the legend.
const CAT_SLOTS = ["var(--viz-c1)", "var(--viz-c2)", "var(--viz-c3)", "var(--viz-c4)", "var(--viz-c5)", "var(--viz-c6)"];
const donutData = computed(() => {
	const rows = (result.value?.rows || []).filter((r) => r.value > 0);
	let slices = rows;
	if (rows.length > 6) {
		const head = rows.slice(0, 5);
		const tail = rows.slice(5);
		slices = [...head, { label: `Other (${tail.length})`, value: +tail.reduce((a, r) => a + r.value, 0).toFixed(2) }];
	}
	const total = slices.reduce((a, r) => a + r.value, 0) || 1;
	let angle = -Math.PI / 2;
	const R = 78,
		r0 = 46,
		cx = 90,
		cy = 90;
	return slices.map((s, i) => {
		const frac = s.value / total;
		const gap = Math.min(0.045, frac * Math.PI * 0.25);
		const a0 = angle + gap / 2;
		const a1 = angle + frac * Math.PI * 2 - gap / 2;
		angle += frac * Math.PI * 2;
		const large = a1 - a0 > Math.PI ? 1 : 0;
		const p = (a, r) => `${(cx + r * Math.cos(a)).toFixed(2)},${(cy + r * Math.sin(a)).toFixed(2)}`;
		return {
			...s,
			pct: frac * 100,
			color: CAT_SLOTS[i % CAT_SLOTS.length],
			d: a1 <= a0 ? "" : `M${p(a0, R)} A${R},${R} 0 ${large} 1 ${p(a1, R)} L${p(a1, r0)} A${r0},${r0} 0 ${large} 0 ${p(a0, r0)} Z`,
		};
	});
});

const VIZ_LABEL = { bar: "Bar", column: "Column", line: "Line", donut: "Donut", table: "Table", kpi: "Figure" };
</script>

<template>
	<div class="bg-white min-h-full viz-root">
		<div v-if="!canUseInsights" class="max-w-6xl mx-auto px-6 py-16 text-center text-sm text-ink-500">
			Insights is available to leadership roles.
		</div>
		<div v-else class="max-w-6xl mx-auto px-6 py-8">
			<!-- Title -->
			<div class="mb-6">
				<div class="text-[11px] uppercase tracking-wider text-ink-500 font-medium mb-1">Insights</div>
				<h1 class="text-2xl font-semibold text-ink-900 tracking-tight">Ask your data</h1>
				<p class="text-sm text-ink-500 mt-1">Describe the report you want. Reshape it afterwards in plain language.</p>
			</div>

			<!-- Prompt -->
			<div class="bg-brand-50 border border-brand-200 rounded-xl p-4 mb-4">
				<div class="flex items-start gap-3">
					<span class="w-9 h-9 rounded-lg bg-brand-600 text-white flex items-center justify-center flex-shrink-0">
						<svg
							class="w-4 h-4"
							viewBox="0 0 24 24"
							fill="none"
							stroke="currentColor"
							stroke-width="1.75"
							stroke-linecap="round"
							stroke-linejoin="round"
						>
							<polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
						</svg>
					</span>
					<div class="flex-1 min-w-0">
						<div class="flex flex-col sm:flex-row gap-2">
							<input
								v-model="prompt"
								type="text"
								class="flex-1 text-sm px-3 py-2 border border-ink-200 rounded-lg bg-white text-ink-900 focus:outline-none focus:ring-2 focus:ring-brand-200 focus:border-brand-400"
								placeholder="e.g. supplier bill value by supplier, top 5"
								@keyup.enter="ask"
							/>
							<button type="button" class="desk-save-btn !text-sm whitespace-nowrap" @click="ask">Build report</button>
						</div>
						<!-- Examples are for finding your footing; once a report is on screen the
						     refine box below it is the relevant control. -->
						<div v-if="!spec" class="flex flex-wrap gap-1.5 mt-2">
							<button
								v-for="s in SUGGESTIONS"
								:key="s"
								type="button"
								class="text-[11px] px-2 py-1 rounded-full bg-white border border-ink-200 text-ink-600 hover:border-brand-400 hover:text-brand-700 transition-colors"
								@click="useSuggestion(s)"
							>
								{{ s }}
							</button>
						</div>
					</div>
				</div>
			</div>

			<!-- What it understood, or why it couldn't -->
			<div
				v-if="notice"
				class="text-[11px] rounded-lg px-3 py-2 mb-4 border"
				:class="noticeTone === 'warn' ? 'bg-warning-50 border-warning-200 text-warning-700' : 'bg-info-50 border-info-200 text-info-700'"
			>
				{{ notice }}
			</div>

			<!-- Generating -->
			<div v-if="busy" class="bg-white border border-ink-200 rounded-xl p-6 mb-6">
				<div class="flex items-center gap-3 mb-4">
					<span class="w-4 h-4 rounded-full border-2 border-brand-200 border-t-brand-600 animate-spin flex-shrink-0"></span>
					<span class="text-sm text-ink-700">{{ busyStep }}</span>
				</div>
				<div class="space-y-2.5">
					<div v-for="i in 5" :key="i" class="flex items-center gap-3">
						<span class="h-3 rounded bg-ink-100 animate-pulse" :style="`width:${[30, 22, 26, 18, 24][i - 1]}%`"></span>
						<span class="h-3 flex-1 rounded bg-ink-100 animate-pulse" :style="`opacity:${1 - i * 0.12}`"></span>
					</div>
				</div>
			</div>

			<!-- Data still loading on first arrival -->
			<div v-else-if="spec && loading" class="bg-white border border-ink-200 rounded-xl p-6 mb-6 text-sm text-ink-500 italic">
				Loading data…
			</div>

			<!-- ===== Report ===== -->
			<div v-else-if="spec && result" class="bg-white border border-ink-200 rounded-xl overflow-hidden mb-6">
				<header class="px-4 py-3 border-b border-ink-200 flex flex-wrap items-center gap-3">
					<div class="min-w-0">
						<h2 class="text-sm font-semibold text-ink-900 capitalize">{{ title }}</h2>
						<p class="text-[11px] text-ink-500 mt-0.5">
							{{ result.recordCount }} record{{ result.recordCount === 1 ? "" : "s" }}
							<template v-if="result.mode === 'aggregate'">
								· {{ result.rows.length }} {{ result.dimensionLabel.toLowerCase() }} group{{ result.rows.length === 1 ? "" : "s" }}
							</template>
							<template v-if="result.truncated"> · {{ result.truncated }} more not shown</template>
						</p>
					</div>
					<div class="ml-auto flex items-center gap-2">
						<button v-if="history.length" type="button" class="text-xs text-ink-600 hover:text-ink-900" @click="undo">Undo</button>
						<button type="button" class="text-xs text-ink-500 hover:text-ink-900" @click="clearReport">Clear</button>
					</div>
				</header>

				<!-- Controls — the same edits the prompt makes, as controls -->
				<div class="px-4 py-2.5 border-b border-ink-100 flex flex-wrap items-center gap-3 bg-ink-50/60">
					<!-- Records vs rollup. Some questions want the lines, not a summary of them. -->
					<div class="flex border border-ink-200 rounded-md overflow-hidden bg-white">
						<button
							v-for="m in [['aggregate', 'Summary'], ['list', 'Records']]"
							:key="m[0]"
							type="button"
							class="px-2.5 py-1 text-[11px] border-l border-ink-200 first:border-l-0"
							:class="spec.mode === m[0] ? 'bg-brand-50 text-brand-700 font-medium' : 'text-ink-600 hover:bg-ink-50'"
							@click="spec = { ...spec, mode: m[0] }"
						>
							{{ m[1] }}
						</button>
					</div>
					<div v-if="spec.mode === 'aggregate'" class="flex border border-ink-200 rounded-md overflow-hidden bg-white">
						<button
							v-for="v in VIZ"
							:key="v"
							type="button"
							class="px-2.5 py-1 text-[11px] border-l border-ink-200 first:border-l-0"
							:class="spec.viz === v ? 'bg-brand-50 text-brand-700 font-medium' : 'text-ink-600 hover:bg-ink-50'"
							@click="setViz(v)"
						>
							{{ VIZ_LABEL[v] }}
						</button>
					</div>
					<div v-if="spec.mode === 'aggregate'" class="flex items-center gap-1.5">
						<span class="text-[10px] uppercase tracking-wider text-ink-500 font-medium">Group by</span>
						<select
							:value="spec.dimension"
							class="text-xs px-2 py-1 border border-ink-200 rounded-md bg-white text-ink-900"
							@change="setDimension($event.target.value)"
						>
							<option v-for="d in dimensionChoices" :key="d.key" :value="d.key">{{ d.label }}</option>
						</select>
					</div>
					<div class="w-56">
						<DeskSearchableSelect v-model="scopeProject" :options="projectOptions" allow-clear placeholder="All projects" search-placeholder="Search projects…" />
					</div>
					<span class="ml-auto text-xs text-ink-600 tabular-nums">
						Total <span class="font-semibold text-ink-900">{{ fmtValue(result.total) }}</span>
					</span>
				</div>

				<!-- Filters. A large register needs narrowing beyond project + date, and every
				     one of these is also settable from the prompt. -->
				<div class="px-4 py-2.5 border-b border-ink-100 flex flex-wrap items-center gap-2">
					<input
						:value="spec.filters.q || ''"
						type="text"
						placeholder="Search records…"
						class="text-xs px-2.5 py-1.5 border border-ink-200 rounded-md bg-white text-ink-900 w-44 focus:outline-none focus:ring-2 focus:ring-brand-200 focus:border-brand-400"
						@change="patchFilters({ q: $event.target.value })"
					/>
					<input
						:value="spec.filters.from || ''"
						type="date"
						title="From"
						class="text-xs px-2 py-1.5 border border-ink-200 rounded-md bg-white text-ink-900"
						@change="patchFilters({ from: $event.target.value })"
					/>
					<input
						:value="spec.filters.to || ''"
						type="date"
						title="To"
						class="text-xs px-2 py-1.5 border border-ink-200 rounded-md bg-white text-ink-900"
						@change="patchFilters({ to: $event.target.value })"
					/>
					<input
						:value="spec.filters.min ?? ''"
						type="number"
						min="0"
						:placeholder="`Min ${result.measureLabel.toLowerCase()}`"
						class="text-xs px-2 py-1.5 border border-ink-200 rounded-md bg-white text-ink-900 w-28"
						@change="patchFilters({ min: $event.target.value === '' ? null : Number($event.target.value) })"
					/>
					<!-- Filter on any dimension's actual values -->
					<span class="flex items-center gap-1">
						<select v-model="filterDim" class="text-xs px-2 py-1.5 border border-ink-200 rounded-md bg-white text-ink-900">
							<option value="">Field…</option>
							<option v-for="(d, k) in dimValues" :key="k" :value="k">{{ d.label }}</option>
						</select>
						<select v-if="filterDim" v-model="filterVal" class="text-xs px-2 py-1.5 border border-ink-200 rounded-md bg-white text-ink-900 max-w-44">
							<option value="">Value…</option>
							<option v-for="v in dimValues[filterDim]?.values || []" :key="v" :value="v">{{ v }}</option>
						</select>
						<button v-if="filterDim && filterVal" type="button" class="text-xs px-2 py-1.5 border border-ink-200 bg-white hover:bg-ink-50 rounded-md" @click="addValueFilter">Add</button>
					</span>
				</div>

				<!-- Active filters, always visible -->
				<div v-if="activeChips.length" class="px-4 py-2 border-b border-ink-100 flex flex-wrap items-center gap-1.5">
					<span
						v-for="c in activeChips"
						:key="c.key"
						class="inline-flex items-center gap-1 text-[11px] px-2 py-0.5 rounded-full bg-brand-50 text-brand-700"
					>
						{{ c.label }}
						<button type="button" class="hover:text-brand-900" @click="removeChip(c.key)">✕</button>
					</span>
					<button type="button" class="text-[11px] text-ink-500 hover:text-ink-900 ml-1" @click="clearFilters">Clear all</button>
				</div>

				<div class="p-4">
					<!-- Record list — the dataset supplies its own columns. -->
					<div v-if="result.mode === 'list'">
						<div v-if="!result.records.length" class="py-12 text-center text-sm text-ink-400 italic">No records match this scope.</div>
						<div v-else class="border border-ink-200 rounded-lg overflow-x-auto">
							<table class="w-full text-xs">
								<thead class="bg-ink-50 text-ink-500 uppercase tracking-wider text-[10px]">
									<tr>
										<th v-for="c in result.columns" :key="c.key" class="px-3 py-2 whitespace-nowrap" :class="c.align === 'right' ? 'text-right' : 'text-left'">{{ c.label }}</th>
									</tr>
								</thead>
								<tbody>
									<tr v-for="rec in result.records" :key="rec._k" class="border-t border-ink-100">
										<td
											v-for="c in result.columns"
											:key="c.key"
											class="px-3 py-2"
											:class="[c.align === 'right' ? 'text-right tabular-nums text-ink-800' : 'text-ink-800', c.key === result.columns[0].key ? 'text-ink-900' : '']"
										>
											{{ c.money ? fmtINR(rec[c.key]) : rec[c.key] === "" || rec[c.key] == null ? "—" : rec[c.key] }}
										</td>
									</tr>
								</tbody>
							</table>
						</div>
						<!-- Paging — only the visible page is mapped and rendered. -->
						<div v-if="result.recordCount" class="flex flex-wrap items-center gap-3 mt-3 text-[11px] text-ink-600">
							<span class="flex items-center gap-1.5">
								<span class="text-ink-500">Rows</span>
								<select v-model.number="pageSize" class="text-[11px] px-1.5 py-1 border border-ink-200 rounded-md bg-white text-ink-900" @change="page = 0">
									<option v-for="s in PAGE_SIZES" :key="s" :value="s">{{ s }}</option>
								</select>
							</span>
							<span class="tabular-nums">Showing {{ rangeStart }}–{{ rangeEnd }} of {{ result.recordCount }}</span>
							<span class="ml-auto flex items-center gap-1.5">
								<button type="button" class="px-2 py-1 border border-ink-200 rounded-md bg-white hover:bg-ink-50 disabled:opacity-40 disabled:cursor-not-allowed" :disabled="page === 0" @click="page--">‹ Prev</button>
								<span class="tabular-nums text-ink-500">Page {{ page + 1 }} of {{ pageCount }}</span>
								<button type="button" class="px-2 py-1 border border-ink-200 rounded-md bg-white hover:bg-ink-50 disabled:opacity-40 disabled:cursor-not-allowed" :disabled="page + 1 >= pageCount" @click="page++">Next ›</button>
							</span>
						</div>
					</div>

					<div v-else-if="!result.rows.length" class="py-12 text-center text-sm text-ink-400 italic">No records match this scope.</div>

					<!-- Figure — a single headline number is not a one-bar chart -->
					<div v-else-if="spec.viz === 'kpi'" class="py-6 text-center">
						<div class="text-4xl font-semibold text-ink-900 tabular-nums">{{ fmtValue(result.total) }}</div>
						<div class="text-xs text-ink-500 mt-1.5">{{ result.measureLabel }} of {{ result.datasetLabel.toLowerCase() }}</div>
					</div>

					<!-- Bar — horizontal, best for long category names -->
					<div v-else-if="spec.viz === 'bar'" class="relative">
						<div
							v-for="(r, i) in barChart.rows"
							:key="r.label"
							class="flex items-center gap-3 group"
							:style="`height:${BAR_H}px`"
							@mouseenter="hovered = i"
							@mouseleave="hovered = null"
						>
							<span class="w-40 sm:w-52 flex-shrink-0 text-[11px] text-ink-600 truncate text-right" :title="r.label">{{ r.label }}</span>
							<span class="flex-1 min-w-0 relative h-4">
								<span
									class="absolute inset-y-0 left-0 viz-bar"
									:style="`width:${Math.max(1.5, (r.value / maxValue) * 100)}%`"
									:class="hovered === i ? 'viz-bar-hi' : ''"
								></span>
							</span>
							<span class="w-24 flex-shrink-0 text-[11px] tabular-nums text-ink-800 text-right">{{ fmtValueShort(r.value) }}</span>
						</div>
					</div>

					<!-- Column -->
					<div v-else-if="spec.viz === 'column'" class="overflow-x-auto">
						<svg :width="colChart.width" :height="colChart.height + 30" class="block">
							<line :x1="0" :y1="colChart.height" :x2="colChart.width" :y2="colChart.height" class="viz-axis-line" />
							<g v-for="(r, i) in colChart.rows" :key="r.label">
								<rect
									:x="20 + i * COL_W"
									:y="colChart.height - Math.max(2, (r.value / maxValue) * (colChart.height - 20))"
									:width="COL_W - 14"
									:height="Math.max(2, (r.value / maxValue) * (colChart.height - 20))"
									rx="4"
									class="viz-fill"
									:class="hovered === i ? 'viz-fill-hi' : ''"
									@mouseenter="hovered = i"
									@mouseleave="hovered = null"
								>
									<title>{{ r.label }}: {{ fmtValue(r.value) }}</title>
								</rect>
								<text :x="20 + i * COL_W + (COL_W - 14) / 2" :y="colChart.height + 14" text-anchor="middle" class="viz-tick">{{ r.label.length > 8 ? r.label.slice(0, 7) + "…" : r.label }}</text>
								<text :x="20 + i * COL_W + (COL_W - 14) / 2" :y="colChart.height + 26" text-anchor="middle" class="viz-tick-strong">{{ fmtValueShort(r.value) }}</text>
							</g>
						</svg>
					</div>

					<!-- Line — 2px stroke, markers -->
					<div v-else-if="spec.viz === 'line'" class="overflow-x-auto">
						<svg :width="lineChart.w" :height="lineChart.h + 16" class="block">
							<line :x1="0" :y1="lineChart.padT + lineChart.innerH" :x2="lineChart.w" :y2="lineChart.padT + lineChart.innerH" class="viz-axis-line" />
							<path :d="lineChart.path" fill="none" class="viz-line" />
							<g v-for="(p, i) in lineChart.rows" :key="p.label">
								<circle :cx="p.x" :cy="p.y" r="4.5" class="viz-dot" :class="hovered === i ? 'viz-dot-hi' : ''" @mouseenter="hovered = i" @mouseleave="hovered = null">
									<title>{{ p.label }}: {{ fmtValue(p.value) }}</title>
								</circle>
								<text :x="p.x" :y="lineChart.h + 6" text-anchor="middle" class="viz-tick">{{ p.label }}</text>
								<text v-if="hovered === i" :x="p.x" :y="p.y - 10" text-anchor="middle" class="viz-tick-strong">{{ fmtValueShort(p.value) }}</text>
							</g>
						</svg>
					</div>

					<!-- Donut — categorical, direct-labelled legend beside it -->
					<div v-else-if="spec.viz === 'donut'" class="flex flex-col sm:flex-row items-center gap-6">
						<svg width="180" height="180" viewBox="0 0 180 180" class="flex-shrink-0">
							<path
								v-for="(s, i) in donutData"
								:key="s.label"
								:d="s.d"
								:fill="s.color"
								:opacity="hovered === null || hovered === i ? 1 : 0.45"
								@mouseenter="hovered = i"
								@mouseleave="hovered = null"
							>
								<title>{{ s.label }}: {{ fmtValue(s.value) }}</title>
							</path>
							<text x="90" y="86" text-anchor="middle" class="viz-donut-value">{{ fmtValueShort(result.total) }}</text>
							<text x="90" y="102" text-anchor="middle" class="viz-tick">total</text>
						</svg>
						<div class="flex-1 min-w-0 w-full space-y-1.5">
							<div v-for="(s, i) in donutData" :key="s.label" class="flex items-center gap-2 text-xs" @mouseenter="hovered = i" @mouseleave="hovered = null">
								<span class="w-2.5 h-2.5 rounded-sm flex-shrink-0" :style="`background:${s.color}`"></span>
								<span class="text-ink-700 truncate flex-1 min-w-0">{{ s.label }}</span>
								<span class="tabular-nums text-ink-900">{{ fmtValueShort(s.value) }}</span>
								<span class="tabular-nums text-ink-400 w-10 text-right">{{ s.pct.toFixed(0) }}%</span>
							</div>
						</div>
					</div>

					<!-- Table — always reachable, with a Share column and a Total row -->
					<div v-else class="border border-ink-200 rounded-lg overflow-hidden">
						<table class="w-full text-xs">
							<thead class="bg-ink-50 text-ink-500 uppercase tracking-wider text-[10px]">
								<tr>
									<th class="text-left px-3 py-2">{{ result.dimensionLabel }}</th>
									<th class="text-right px-3 py-2">{{ result.measureLabel }}</th>
									<th class="text-right px-3 py-2 w-20">Share</th>
								</tr>
							</thead>
							<tbody>
								<tr v-for="r in result.rows" :key="r.label" class="border-t border-ink-100">
									<td class="px-3 py-2 text-ink-900">{{ r.label }}</td>
									<td class="px-3 py-2 text-right tabular-nums text-ink-800">{{ fmtValue(r.value) }}</td>
									<td class="px-3 py-2 text-right tabular-nums text-ink-500">{{ result.total ? ((r.value / result.total) * 100).toFixed(1) : "0.0" }}%</td>
								</tr>
								<tr class="border-t border-ink-200 bg-ink-50 font-medium">
									<td class="px-3 py-2 text-ink-900">Total</td>
									<td class="px-3 py-2 text-right tabular-nums text-ink-900">{{ fmtValue(result.total) }}</td>
									<td></td>
								</tr>
							</tbody>
						</table>
					</div>
				</div>

				<!-- Refine -->
				<footer class="px-4 py-3 border-t border-ink-200 bg-ink-50/60">
					<div class="flex flex-col sm:flex-row gap-2">
						<input
							v-model="refinePrompt"
							type="text"
							class="flex-1 text-sm px-3 py-1.5 border border-ink-200 rounded-lg bg-white text-ink-900 focus:outline-none focus:ring-2 focus:ring-brand-200 focus:border-brand-400"
							placeholder="Change it — e.g. show as a pie, top 5, group by month, all projects"
							@keyup.enter="refine"
						/>
						<button type="button" class="text-xs px-3 py-1.5 border border-ink-200 bg-white hover:bg-ink-50 text-ink-700 rounded-md whitespace-nowrap" @click="refine">Apply</button>
					</div>
				</footer>
			</div>

			<!-- ===== Presets — collapsed while a report is on screen ===== -->
			<section data-tour="insights-presets">
				<button type="button" class="w-full flex items-center gap-2 text-left mb-2 group" @click="presetsOpen = !presetsOpen">
					<h2 class="text-[11px] font-semibold uppercase tracking-wider text-ink-700">Preset reports</h2>
					<span class="text-[11px] text-ink-400 tabular-nums">{{ PRESETS.length }}</span>
					<svg
						class="w-3.5 h-3.5 text-ink-400 transition-transform"
						:class="presetsOpen ? '' : '-rotate-90'"
						viewBox="0 0 24 24"
						fill="none"
						stroke="currentColor"
						stroke-width="2.5"
						stroke-linecap="round"
						stroke-linejoin="round"
					>
						<polyline points="6 9 12 15 18 9" />
					</svg>
				</button>
				<div class="border-t border-ink-200 mb-3"></div>
				<div v-if="presetsOpen" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-2">
					<button
						v-for="p in PRESETS"
						:key="p.id"
						type="button"
						class="text-left bg-white border border-ink-200 hover:border-brand-400 hover:bg-brand-50 rounded-lg p-3 transition-colors group"
						@click="runPreset(p)"
					>
						<div class="text-sm font-medium text-ink-900 group-hover:text-brand-700 transition-colors">{{ p.title }}</div>
						<div class="text-[10px] text-ink-500 mt-0.5 truncate">{{ p.prompt }}</div>
					</button>
				</div>
			</section>

			<p v-if="!spec" class="text-[11px] text-ink-400 mt-6">
				Prompts are matched against BuildSuite's own data — every figure here comes from your records, and a question it can't map says so rather than guessing.
			</p>
		</div>
	</div>
</template>

<style>
/* Data-viz tokens. Bar / column / line carry ONE series, so they use a single hue;
   the six categorical slots are only for the donut. */
.viz-root {
	--viz-series: #2a78d6;
	--viz-axis: #c3c2b7;
	--viz-muted: #898781;
	--viz-ink: #0b0b0b;
	--viz-c1: #2a78d6;
	--viz-c2: #eb6834;
	--viz-c3: #1baf7a;
	--viz-c4: #eda100;
	--viz-c5: #e87ba4;
	--viz-c6: #008300;
}
html.dark .viz-root {
	--viz-series: #3987e5;
	--viz-axis: #383835;
	--viz-muted: #898781;
	--viz-ink: #ffffff;
	--viz-c1: #3987e5;
	--viz-c2: #d95926;
	--viz-c3: #199e70;
	--viz-c4: #c98500;
	--viz-c5: #d55181;
	--viz-c6: #008300;
}
.viz-root .viz-bar {
	background: var(--viz-series);
	border-radius: 0 4px 4px 0;
	transition: opacity 0.12s ease;
	opacity: 0.9;
}
.viz-root .viz-bar-hi {
	opacity: 1;
}
.viz-root .viz-fill {
	fill: var(--viz-series);
	opacity: 0.9;
	transition: opacity 0.12s ease;
}
.viz-root .viz-fill-hi {
	opacity: 1;
}
.viz-root .viz-line {
	stroke: var(--viz-series);
	stroke-width: 2;
	stroke-linejoin: round;
	stroke-linecap: round;
}
.viz-root .viz-dot {
	fill: var(--viz-series);
	stroke: #fff;
	stroke-width: 2;
}
html.dark .viz-root .viz-dot {
	stroke: #242424;
}
.viz-root .viz-dot-hi {
	r: 6;
}
.viz-root .viz-axis-line {
	stroke: var(--viz-axis);
	stroke-width: 1;
}
.viz-root .viz-tick {
	fill: var(--viz-muted);
	font-size: 10px;
}
.viz-root .viz-tick-strong {
	fill: var(--viz-ink);
	font-size: 10px;
	font-weight: 600;
}
.viz-root .viz-donut-value {
	fill: var(--viz-ink);
	font-size: 17px;
	font-weight: 600;
}
</style>
