<script setup>
// Minimal SVG renderer for a frappe-charts spec ({ type, data: { labels, datasets } })
// as returned by a Script Report's execute(). Supports bar (default) and line, multiple
// datasets, and negative values (bars grow from a zero baseline). No external chart lib —
// keeps the SPA bundle lean. Theme-aware via currentColor for axes/labels.
import { computed } from "vue";

const props = defineProps({
	chart: { type: Object, required: true },
});

// Distinct, colour-blind-friendly palette; cycles if there are more datasets.
const PALETTE = ["#6366f1", "#ef4444", "#f59e0b", "#10b981", "#3b82f6", "#ec4899", "#14b8a6"];

const W = 640;
const H = 240;
const PAD = { top: 12, right: 12, bottom: 26, left: 12 };

const labels = computed(() => props.chart?.data?.labels || []);
const datasets = computed(() =>
	(props.chart?.data?.datasets || []).map((d, i) => ({
		name: d.name || `Series ${i + 1}`,
		values: (d.values || []).map((v) => Number(v) || 0),
		color: PALETTE[i % PALETTE.length],
	}))
);
const type = computed(() => props.chart?.type || "bar");
const hasData = computed(() => labels.value.length && datasets.value.length);

const allValues = computed(() => datasets.value.flatMap((d) => d.values));
const yMax = computed(() => Math.max(0, ...allValues.value));
const yMin = computed(() => Math.min(0, ...allValues.value));
const span = computed(() => yMax.value - yMin.value || 1);

const plot = computed(() => ({
	left: PAD.left,
	right: W - PAD.right,
	top: PAD.top,
	bottom: H - PAD.bottom,
}));
function yFor(v) {
	const p = plot.value;
	return p.top + ((yMax.value - v) / span.value) * (p.bottom - p.top);
}
const zeroY = computed(() => yFor(0));

// Compact number label (K / L / Cr for the Indian scale the reports use).
function compact(v) {
	const n = Number(v) || 0;
	const a = Math.abs(n);
	const sign = n < 0 ? "-" : "";
	if (a >= 1e7) return `${sign}${(a / 1e7).toFixed(2)}Cr`;
	if (a >= 1e5) return `${sign}${(a / 1e5).toFixed(2)}L`;
	if (a >= 1e3) return `${sign}${(a / 1e3).toFixed(1)}K`;
	return `${sign}${a}`;
}

const groupWidth = computed(
	() => (plot.value.right - plot.value.left) / (labels.value.length || 1)
);

// Bar geometry: bars sit side-by-side within each label group.
const bars = computed(() => {
	if (type.value === "line") return [];
	const out = [];
	const gw = groupWidth.value;
	const n = datasets.value.length;
	const inner = gw * 0.7;
	const bw = inner / n;
	const showLabels = allValues.value.length <= 12;
	labels.value.forEach((_, li) => {
		const gx = plot.value.left + li * gw + (gw - inner) / 2;
		datasets.value.forEach((d, di) => {
			const v = d.values[li] ?? 0;
			const y = yFor(v);
			const x = gx + di * bw;
			out.push({
				x: x + 1,
				y: Math.min(y, zeroY.value),
				w: Math.max(bw - 2, 1),
				h: Math.max(Math.abs(y - zeroY.value), 0.5),
				color: d.color,
				label: showLabels ? compact(v) : "",
				labelY:
					(v >= 0 ? Math.min(y, zeroY.value) : Math.max(y, zeroY.value)) +
					(v >= 0 ? -3 : 11),
				labelX: x + bw / 2,
			});
		});
	});
	return out;
});

// Line geometry: one polyline per dataset.
const lines = computed(() => {
	if (type.value !== "line") return [];
	const gw = groupWidth.value;
	return datasets.value.map((d) => ({
		color: d.color,
		points: labels.value
			.map((_, li) => `${plot.value.left + li * gw + gw / 2},${yFor(d.values[li] ?? 0)}`)
			.join(" "),
	}));
});

const xTicks = computed(() => {
	const gw = groupWidth.value;
	return labels.value.map((l, i) => ({ label: l, x: plot.value.left + i * gw + gw / 2 }));
});
</script>

<template>
	<div v-if="hasData" class="bg-white border border-ink-200 rounded-lg p-3 mb-3">
		<svg :viewBox="`0 0 ${W} ${H}`" class="w-full" style="max-height: 240px" role="img">
			<!-- zero baseline -->
			<line
				:x1="plot.left"
				:x2="plot.right"
				:y1="zeroY"
				:y2="zeroY"
				stroke="currentColor"
				class="text-ink-300"
				stroke-width="1"
			/>
			<!-- bars -->
			<template v-for="(b, i) in bars" :key="`b${i}`">
				<rect :x="b.x" :y="b.y" :width="b.w" :height="b.h" :fill="b.color" rx="1.5" />
				<text
					v-if="b.label"
					:x="b.labelX"
					:y="b.labelY"
					text-anchor="middle"
					class="fill-ink-600"
					style="font-size: 9px"
				>
					{{ b.label }}
				</text>
			</template>
			<!-- lines -->
			<polyline
				v-for="(ln, i) in lines"
				:key="`l${i}`"
				:points="ln.points"
				fill="none"
				:stroke="ln.color"
				stroke-width="2"
				stroke-linejoin="round"
				stroke-linecap="round"
			/>
			<!-- x-axis labels -->
			<text
				v-for="(t, i) in xTicks"
				:key="`x${i}`"
				:x="t.x"
				:y="H - 8"
				text-anchor="middle"
				class="fill-ink-500"
				style="font-size: 10px"
			>
				{{ t.label }}
			</text>
		</svg>
		<!-- legend -->
		<div class="flex flex-wrap items-center gap-x-4 gap-y-1 mt-1 px-1">
			<div v-for="d in datasets" :key="d.name" class="flex items-center gap-1.5">
				<span
					class="inline-block w-2.5 h-2.5 rounded-sm"
					:style="{ backgroundColor: d.color }"
				></span>
				<span class="text-[11px] text-ink-600">{{ d.name }}</span>
			</div>
		</div>
	</div>
</template>
