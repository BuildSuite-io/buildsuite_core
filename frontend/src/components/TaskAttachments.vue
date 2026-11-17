<script setup>
// A task's own files (drawings, reference images, specifications) plus the
// photos its progress updates carried — mirrors the prototype's TaskAttachments.
//
// Both are native Frappe File records: task files attach to the Task, progress
// photos attach to each Task Progress Entry (filed when the crew logs progress)
// and are shown here read-only, newest first, each linked back to its entry.
import { computed, onMounted, onUnmounted, ref, watch } from "vue";
import { useConfirm } from "@/composables/useConfirm";
import { showToast } from "@/utils/appToast";
import { createDataAdapter } from "@/data/adapters";
import { useDataStore } from "@/stores";
import FileUploadHandler from "frappe-ui-file-upload-handler";
import UserAvatar from "@/components/UserAvatar.vue";
import DeskLink from "@/components/desk/DeskLink.vue";
import { fmtDate } from "@/utils/format";
import { __ } from "@/utils/translate";

const props = defineProps({
	// Task docname — what files attach to.
	taskId: { type: String, required: true },
	// Progress entries of this task ([{ id, entryDate, progressPct }]) — their
	// image attachments surface as the progress-photos gallery.
	entries: { type: Array, default: () => [] },
	// Upload / remove are task-edit affordances; viewing is always allowed.
	canManage: { type: Boolean, default: false },
});

const adapter = createDataAdapter(useDataStore());
const confirmDialog = useConfirm();

// ---- file-type helpers ----
const IMAGE_EXTS = ["jpg", "jpeg", "png", "gif", "webp", "svg", "bmp", "avif"];
function extOf(att) {
	const url = typeof att === "string" ? att : att?.file_url || att?.file_name;
	return (url || "").split(".").pop().toLowerCase().split("?")[0];
}
function isImage(att) {
	return IMAGE_EXTS.includes(extOf(att));
}
function isPdf(att) {
	return extOf(att) === "pdf";
}
function fileIcon(att) {
	const ext = extOf(att);
	if (IMAGE_EXTS.includes(ext)) return "🖼️";
	if (ext === "pdf") return "📕";
	if (["dwg", "dxf"].includes(ext)) return "📐";
	if (["doc", "docx"].includes(ext)) return "📝";
	if (["xls", "xlsx", "csv"].includes(ext)) return "📊";
	if (["zip", "rar", "7z"].includes(ext)) return "🗜️";
	return "📄";
}
function formatFileSize(bytes) {
	if (!bytes) return "0 B";
	const units = ["B", "KB", "MB", "GB"];
	let i = 0;
	let n = bytes;
	while (n >= 1024 && i < units.length - 1) {
		n /= 1024;
		i++;
	}
	return (i === 0 ? n : n.toFixed(n < 10 ? 1 : 0)) + " " + units[i];
}

function rowsOf(resource) {
	const raw = resource?.data;
	if (Array.isArray(raw)) return raw;
	if (Array.isArray(raw?.value)) return raw.value;
	return [];
}

// ---- task files (native File on the Task) ----
const filesResource = ref(null);
function loadFiles() {
	filesResource.value = props.taskId
		? adapter.list("File", {
				filters: [
					["attached_to_doctype", "=", "Task"],
					["attached_to_name", "=", props.taskId],
				],
				fields: [
					"name",
					"file_name",
					"file_url",
					"file_size",
					"is_private",
					"creation",
					"owner",
				],
				orderBy: "creation desc",
		  })
		: null;
}
watch(() => props.taskId, loadFiles, { immediate: true });
const files = computed(() => rowsOf(filesResource.value));

// ---- progress photos (image File on this task's Task Progress Entries) ----
const entryMap = computed(() => {
	const m = {};
	for (const e of props.entries || []) m[e.id] = e;
	return m;
});
const entryIds = computed(() => (props.entries || []).map((e) => e.id).filter(Boolean));
const photosResource = ref(null);
function loadPhotos() {
	photosResource.value = entryIds.value.length
		? adapter.list("File", {
				filters: [
					["attached_to_doctype", "=", "Task Progress Entry"],
					["attached_to_name", "in", entryIds.value],
				],
				fields: [
					"name",
					"file_name",
					"file_url",
					"file_size",
					"creation",
					"owner",
					"attached_to_name",
				],
				orderBy: "creation desc",
		  })
		: null;
}
watch(() => entryIds.value.join(","), loadPhotos, { immediate: true });
const photos = computed(() =>
	rowsOf(photosResource.value)
		.filter(isImage)
		.map((r) => {
			const e = entryMap.value[r.attached_to_name] || {};
			return {
				...r,
				entry: r.attached_to_name,
				entryDate: e.entryDate,
				progressPct: e.progressPct,
			};
		})
);

// ---- upload / remove (task files only; photos are filed with their entry) ----
const picker = ref(null);
const uploading = ref(0);
function pick() {
	picker.value?.click();
}
async function onPicked(e) {
	const picked = Array.from(e.target.files || []);
	if (e.target) e.target.value = "";
	if (!picked.length) return;
	uploading.value += picked.length;
	for (const f of picked) {
		try {
			await new FileUploadHandler().upload(f, {
				doctype: "Task",
				docname: props.taskId,
				private: true,
			});
		} catch (err) {
			showToast(err.message || __("Failed to upload {0}", [f.name]), "error");
		} finally {
			uploading.value--;
		}
	}
	filesResource.value?.reload?.();
}
async function removeFile(att) {
	const ok = await confirmDialog({
		title: __("Remove file"),
		message: __('Remove "{0}" from this task?', [att.file_name]),
		confirmLabel: __("Remove"),
		destructive: true,
	});
	if (!ok) return;
	try {
		await adapter.remove("File", att.name);
		filesResource.value?.reload?.();
		showToast(__("File removed."));
	} catch (err) {
		showToast(err.message || __("Failed to remove file"), "error");
	}
}

// ---- lightbox (images gallery + single PDF) ----
const lightbox = ref(null); // { items, index }
const current = computed(() =>
	lightbox.value ? lightbox.value.items[lightbox.value.index] : null
);
function openFile(att) {
	if (isImage(att)) {
		const imgs = files.value.filter(isImage);
		lightbox.value = { items: imgs, index: Math.max(0, imgs.indexOf(att)) };
	} else if (isPdf(att)) {
		lightbox.value = { items: [att], index: 0 };
	} else if (att.file_url) {
		window.open(att.file_url, "_blank", "noopener");
	}
}
function openPhoto(i) {
	lightbox.value = { items: photos.value, index: i };
}
function closeLightbox() {
	lightbox.value = null;
}
function prev() {
	if (lightbox.value && lightbox.value.index > 0) lightbox.value.index--;
}
function next() {
	if (lightbox.value && lightbox.value.index < lightbox.value.items.length - 1)
		lightbox.value.index++;
}
function onKey(e) {
	if (!lightbox.value) return;
	if (e.key === "Escape") closeLightbox();
	else if (e.key === "ArrowLeft") prev();
	else if (e.key === "ArrowRight") next();
}
onMounted(() => window.addEventListener("keydown", onKey));
onUnmounted(() => window.removeEventListener("keydown", onKey));
</script>

<template>
	<section class="bg-white border border-ink-200 overflow-hidden" style="border-radius: 10px">
		<header
			class="px-5 py-3 bg-gradient-to-r from-brand-50 to-white border-b border-ink-100 flex items-center justify-between gap-3"
		>
			<div class="min-w-0">
				<h3 class="text-sm font-semibold text-ink-900">{{ __("Files") }}</h3>
				<div class="text-[11px] text-ink-500">
					{{ __("{0} files", [files.length]) }} ·
					{{ __("{0} progress photos", [photos.length]) }}
				</div>
			</div>
			<button
				v-if="canManage"
				type="button"
				class="desk-save-btn !text-xs shrink-0"
				:disabled="uploading > 0"
				@click="pick"
			>
				{{ uploading > 0 ? __("Adding… ({0})", [uploading]) : __("+ Add files") }}
			</button>
			<input ref="picker" type="file" multiple class="hidden" @change="onPicked" />
		</header>

		<div class="p-5 space-y-4">
			<!-- Task files -->
			<ul
				v-if="files.length"
				class="border border-ink-200 divide-y divide-ink-100"
				style="border-radius: 8px"
			>
				<li
					v-for="f in files"
					:key="f.name"
					class="flex items-center gap-3 px-3 py-2 hover:bg-ink-50"
				>
					<button
						type="button"
						class="w-12 h-9 shrink-0 border border-ink-200 bg-ink-50 overflow-hidden flex items-center justify-center hover:ring-2 hover:ring-brand-200"
						style="border-radius: 4px"
						:title="__('Open {0}', [f.file_name])"
						@click="openFile(f)"
					>
						<img
							v-if="isImage(f) && f.file_url"
							:src="f.file_url"
							alt=""
							class="w-full h-full object-cover"
							loading="lazy"
						/>
						<span v-else class="text-lg">{{ fileIcon(f) }}</span>
					</button>
					<div class="flex-1 min-w-0">
						<button
							type="button"
							class="text-sm text-ink-900 hover:text-brand-700 hover:underline text-left truncate max-w-full block"
							:title="f.file_name"
							@click="openFile(f)"
						>
							{{ f.file_name }}
						</button>
						<div class="text-[11px] text-ink-500">
							{{ formatFileSize(f.file_size) }} · {{ fmtDate(f.creation) }}
						</div>
					</div>
					<UserAvatar :user-id="f.owner" size="xs" />
					<button
						v-if="canManage"
						type="button"
						class="text-xs px-1.5 py-0.5 border border-ink-200 bg-white hover:bg-danger-50 text-danger-700"
						style="border-radius: 4px"
						:title="__('Remove {0}', [f.file_name])"
						@click="removeFile(f)"
					>
						&times;
					</button>
				</li>
			</ul>
			<div v-else class="text-sm text-ink-500">
				{{ __("No files on this task yet.")
				}}<span v-if="canManage">
					{{
						__(
							"Add the drawings, reference images and specifications the crew works from."
						)
					}}</span
				>
			</div>

			<!-- Progress photos — read-only, filed with each progress entry -->
			<div v-if="photos.length">
				<div class="text-[10px] uppercase tracking-wider text-ink-500 font-medium mb-1.5">
					{{ __("Progress photos · {0}", [photos.length]) }}
				</div>
				<div class="grid grid-cols-2 sm:grid-cols-4 gap-2">
					<figure
						v-for="(p, i) in photos"
						:key="p.name"
						class="border border-ink-200 overflow-hidden"
						style="border-radius: 6px"
					>
						<button
							type="button"
							class="block w-full"
							:title="__('View photo')"
							@click="openPhoto(i)"
						>
							<img
								:src="p.file_url"
								alt=""
								class="w-full aspect-[4/3] object-cover bg-ink-50"
								loading="lazy"
							/>
						</button>
						<figcaption
							class="px-2 py-1 text-[11px] text-ink-600 flex items-center justify-between gap-1"
						>
							<span
								>{{ fmtDate(p.entryDate)
								}}<span v-if="p.progressPct != null">
									· {{ p.progressPct }}%</span
								></span
							>
							<DeskLink :to="`/progress-entries/${p.entry}`" class="text-[11px]">{{
								__("Entry")
							}}</DeskLink>
						</figcaption>
					</figure>
				</div>
			</div>
		</div>

		<!-- Lightbox — images navigate as a gallery, PDFs embed -->
		<div
			v-if="current"
			class="fixed inset-0 bg-ink-900/70 z-[70] flex items-center justify-center p-4 sm:p-8"
			@click.self="closeLightbox"
		>
			<button
				v-if="lightbox.items.length > 1"
				type="button"
				class="absolute left-3 sm:left-6 text-white/80 hover:text-white text-3xl p-2 disabled:opacity-30"
				:disabled="lightbox.index === 0"
				:title="__('Previous')"
				@click.stop="prev"
			>
				‹
			</button>
			<div
				class="bg-white rounded-xl shadow-2xl w-full max-w-4xl max-h-[90vh] flex flex-col overflow-hidden"
				@click.stop
			>
				<header
					class="px-4 py-3 border-b border-ink-200 flex items-center justify-between gap-3 flex-shrink-0"
				>
					<div class="min-w-0 flex items-center gap-2">
						<span class="text-base flex-shrink-0">{{ fileIcon(current) }}</span>
						<div class="min-w-0">
							<h2
								class="text-sm font-semibold text-ink-900 truncate"
								:title="current.file_name"
							>
								{{ current.file_name }}
							</h2>
							<div class="text-[11px] text-ink-400 tabular-nums">
								{{ formatFileSize(current.file_size)
								}}<span v-if="lightbox.items.length > 1">
									· {{ lightbox.index + 1 }} / {{ lightbox.items.length }}</span
								>
							</div>
						</div>
					</div>
					<div class="flex items-center gap-1.5 flex-shrink-0">
						<a
							:href="current.file_url"
							target="_blank"
							rel="noopener"
							download
							class="text-xs px-2.5 py-1.5 border border-ink-200 bg-white hover:bg-ink-50 text-ink-700 rounded-md flex items-center gap-1.5"
						>
							<svg
								class="w-3.5 h-3.5"
								fill="none"
								stroke="currentColor"
								viewBox="0 0 24 24"
							>
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									stroke-width="1.75"
									d="M4 16v2a2 2 0 002 2h12a2 2 0 002-2v-2M7 10l5 5m0 0l5-5m-5 5V3"
								/>
							</svg>
							{{ __("Download") }}
						</a>
						<button
							type="button"
							class="text-ink-400 hover:text-ink-900 p-1"
							:title="__('Close')"
							@click="closeLightbox"
						>
							✕
						</button>
					</div>
				</header>
				<div
					class="flex-1 min-h-0 overflow-auto bg-ink-50 flex items-center justify-center"
				>
					<img
						v-if="isImage(current)"
						:src="current.file_url"
						:alt="current.file_name"
						class="max-w-full max-h-[75vh] object-contain"
					/>
					<iframe
						v-else-if="isPdf(current)"
						:src="current.file_url"
						class="w-full h-[75vh] bg-white"
						:title="current.file_name"
					></iframe>
				</div>
			</div>
			<button
				v-if="lightbox.items.length > 1"
				type="button"
				class="absolute right-3 sm:right-6 text-white/80 hover:text-white text-3xl p-2 disabled:opacity-30"
				:disabled="lightbox.index === lightbox.items.length - 1"
				:title="__('Next')"
				@click.stop="next"
			>
				›
			</button>
		</div>
	</section>
</template>
