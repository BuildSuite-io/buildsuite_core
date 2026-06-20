<script setup>
import { ref, computed, watch } from "vue";

const props = defineProps({
	userId: { type: String, default: "" },
	showName: { type: Boolean, default: true },
	size: { type: String, default: "sm" }, // xs | sm | md
});

// Module-level cache shared across all instances — one fetch per unique user
// across the entire app lifetime.
const _cache = new Map();

const userInfo = ref(null);

function initials(name) {
	if (!name) return "?";
	const parts = name.trim().split(/\s+/);
	return parts.length >= 2
		? (parts[0][0] + parts[parts.length - 1][0]).toUpperCase()
		: name[0].toUpperCase();
}

// Deterministic color derived from the user email so the same user always
// gets the same hue even before their info is resolved.
const _COLORS = [
	"#F57F17",
	"#6A1B9A",
	"#0277BD",
	"#2E7D32",
	"#C62828",
	"#00695C",
	"#4527A0",
	"#558B2F",
];
function colorForId(id) {
	let h = 0;
	for (let i = 0; i < id.length; i++) h = (h * 31 + id.charCodeAt(i)) & 0xffffff;
	return _COLORS[Math.abs(h) % _COLORS.length];
}

async function resolveUser(userId) {
	if (!userId) {
		userInfo.value = null;
		return;
	}

	// 1. Check Frappe boot — free, sync, no network needed.
	const boot = window.frappe?.boot?.user_info?.[userId];
	if (boot) {
		userInfo.value = {
			full_name: boot.full_name || userId,
			image: boot.image || null,
			abbr: boot.abbr || initials(boot.full_name || userId),
			color: boot.color || colorForId(userId),
		};
		return;
	}

	// 2. Check module cache for previously fetched users.
	if (_cache.has(userId)) {
		userInfo.value = _cache.get(userId);
		return;
	}

	// 3. Fetch from Frappe User doctype.
	try {
		const res = await fetch(
			`/api/resource/User/${encodeURIComponent(userId)}?fields=["full_name","user_image"]`,
			{ credentials: "include", headers: { Accept: "application/json" } }
		);
		if (res.ok) {
			const doc = (await res.json())?.data;
			const info = {
				full_name: doc?.full_name || userId,
				image: doc?.user_image || null,
				abbr: initials(doc?.full_name || userId),
				color: colorForId(userId),
			};
			_cache.set(userId, info);
			userInfo.value = info;
			return;
		}
	} catch {
		/* fall through */
	}

	// 4. Graceful fallback — show initials from the email address.
	const fallback = {
		full_name: userId,
		image: null,
		abbr: initials(userId),
		color: colorForId(userId),
	};
	_cache.set(userId, fallback);
	userInfo.value = fallback;
}

watch(() => props.userId, resolveUser, { immediate: true });

const sizeClass = computed(
	() =>
		({
			xs: "w-5 h-5 text-[10px]",
			sm: "w-6 h-6 text-[11px]",
			md: "w-8 h-8 text-sm",
		}[props.size] ?? "w-6 h-6 text-[11px]")
);
</script>

<template>
	<div class="inline-flex items-center gap-1.5 min-w-0">
		<!-- Avatar circle -->
		<div
			:class="[
				sizeClass,
				'rounded-full flex-shrink-0 overflow-hidden flex items-center justify-center font-medium',
			]"
			:style="
				userInfo?.image ? '' : `background-color:${userInfo?.color ?? colorForId(userId)}`
			"
		>
			<img
				v-if="userInfo?.image"
				:src="userInfo.image"
				:alt="userInfo.full_name"
				class="w-full h-full object-cover"
			/>
			<span v-else class="text-white leading-none">{{ userInfo?.abbr ?? "?" }}</span>
		</div>

		<!-- Full name -->
		<span v-if="showName" class="text-xs text-ink-700 truncate">
			{{ userInfo?.full_name || userId || "—" }}
		</span>
	</div>
</template>
