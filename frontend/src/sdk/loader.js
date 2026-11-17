// Loads the frontend extensions of the apps installed on this site. The server lists them in boot
// (`buildsuite_extensions`, from each installed app's `buildsuite_frontend_extensions` hook); each
// is an ES module whose default export is `register(sdk)`. An extension that is incompatible or
// throws is skipped and logged — it never stops the app from starting.

import { createSdk, runtime, SDK_VERSION } from "@/sdk";

/** Same major, and the extension's minimum minor no newer than ours. */
export function sdkCompatible(minSdk, current = SDK_VERSION) {
	if (!minSdk) return true;
	const [wantMajor, wantMinor = 0] = String(minSdk).split(".").map(Number);
	const [haveMajor, haveMinor = 0] = String(current).split(".").map(Number);
	if ([wantMajor, wantMinor, haveMajor, haveMinor].some(Number.isNaN)) return false;
	return wantMajor === haveMajor && wantMinor <= haveMinor;
}

function addStylesheet(href) {
	if (document.querySelector(`link[data-buildsuite-extension][href="${href}"]`)) return;
	const link = document.createElement("link");
	link.rel = "stylesheet";
	link.href = href;
	link.dataset.buildsuiteExtension = "1";
	document.head.appendChild(link);
}

export async function loadExtensions(router) {
	const loaded = [];
	// Extensions built with their own bundler read Core's shared copies from here.
	globalThis.__buildsuite = runtime;
	for (const entry of window.buildsuite_extensions || []) {
		try {
			if (!sdkCompatible(entry.min_sdk)) {
				console.warn(
					`[buildsuite] extension "${entry.name}" needs SDK ${entry.min_sdk}; this is ${SDK_VERSION} — skipped`
				);
				continue;
			}
			if (entry.css) addStylesheet(entry.css);
			const mod = await import(/* @vite-ignore */ entry.js);
			if (typeof mod.default !== "function") {
				throw new Error("the module has no default export register(sdk)");
			}
			await mod.default(createSdk(entry.name, router));
			loaded.push(entry.name);
		} catch (error) {
			console.warn(`[buildsuite] extension "${entry.name}" failed to load`, error);
		}
	}
	return loaded;
}
