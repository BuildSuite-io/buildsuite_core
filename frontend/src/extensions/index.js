// Frontend extensions: how another app on the bench adds to this SPA without Core naming it.
// (The prototype's src/data/docExtensions.js + registerWorkspaceTile, made real.)
//
// An app ships `<app>/buildsuite_extension/index.js` (beside its Python package) whose default
// export is `register(api)`. At build time every such file in the bench is bundled
// (import.meta.glob below, with Tailwind scanning the same folders); at runtime only the ones
// whose app is installed on this site run (boot `installed_apps`). Extension files import
// Core's modules through "@/" and share Core's Vue, router and store (vite.config dedupe).
//
// api
//   registerDocExtension(doctype, ext)   sections and save hooks on a Core document
//   registerSettingsTile(group, tile)     a tile on the Settings page
//                                         tile: { slug, icon, label, desc, to, can?(store) }
//   addRoute(route)                       a page inside the app shell (vue-router record)
//   app                                   the app's name
//
// A doc extension — a plain object, every key optional:
//   key             unique name
//   fields          the doctype's Custom Fields the extension owns: the form loads them into
//                   `form.custom` and saves them back
//   formSections    [{ position, component }] on the create/edit form; props `form`, `doc`
//                   (the saved document when editing, else null) and `setTerms(text)` (replace
//                   the terms without dropping their template link, as a template load does).
//                   Quotation: 'after-who', 'before-items' (inside Items, above the grid),
//                   'after-items'.
//   detailSections  [{ position, component }] on the record page; props `doc`,
//                   `persist(values)` (save fields and reload) and `reload()`.
//                   Quotation: 'before-lines'. Assembly: 'after-summary'.
//   defaults(form)                  a new document's starting values
//   onLoad(form, doc)               editing: after the saved document is read into the form
//   beforeSave(payload, form)       may add fields to what is saved (may be async)
//   afterSave(doc, { isNew })       after the document is stored (may be async)

import { markRaw } from "vue";

const DOCS = {};
const TILES = [];

export function registerDocExtension(doctype, ext) {
	const list = (DOCS[doctype] ||= []);
	if (ext.key && list.some((e) => e.key === ext.key)) return;
	const raw = (sections) =>
		(sections || []).map((s) => ({ position: s.position, component: markRaw(s.component) }));
	list.push({ ...ext, formSections: raw(ext.formSections), detailSections: raw(ext.detailSections) });
}

export function docExtensions(doctype) {
	return DOCS[doctype] || [];
}

/** The components the extensions placed at one spot, keyed for v-for. */
export function extensionSections(doctype, kind, position) {
	return docExtensions(doctype).flatMap((x, n) =>
		(x[kind] || [])
			.filter((s) => s.position === position)
			.map((s, i) => ({ key: `${x.key || n}:${position}:${i}`, component: s.component }))
	);
}

/** Every Custom Field the extensions of a doctype own (loaded into and saved from form.custom). */
export function extensionFields(doctype) {
	return [...new Set(docExtensions(doctype).flatMap((x) => x.fields || []))];
}

/** Run one hook of every extension of a doctype, in registration order. */
export async function runExtensionHook(doctype, hook, ...args) {
	for (const x of docExtensions(doctype)) {
		if (typeof x[hook] === "function") await x[hook](...args);
	}
}

export function registerSettingsTile(group, tile) {
	if (TILES.some((t) => t.slug === tile.slug)) return;
	TILES.push({ ...tile, group });
}

/** Settings tiles from extensions, grouped like the Settings page's own groups. */
export function settingsTileGroups(store) {
	const groups = {};
	for (const t of TILES) {
		if (typeof t.can === "function" && !t.can(store)) continue;
		(groups[t.group] ||= []).push(t);
	}
	return Object.entries(groups).map(([title, tiles]) => ({ title, tiles }));
}

// ../../../../ = the bench's apps folder (src/extensions → src → frontend → app → apps).
const MODULES = import.meta.glob("../../../../*/buildsuite_extension/index.js", { eager: true });

/** Register the extensions of the apps installed on this site. Call before the router is used. */
export async function loadExtensions(router) {
	const installed = new Set(window.installed_apps || []);
	for (const [path, mod] of Object.entries(MODULES)) {
		const app = path.split("/").slice(-3)[0];
		if (!installed.has(app) || typeof mod.default !== "function") continue;
		try {
			await mod.default({
				app,
				registerDocExtension,
				registerSettingsTile,
				addRoute: (route) => router.addRoute("shell", route),
			});
		} catch (error) {
			console.warn(`[buildsuite] extension "${app}" failed to register`, error);
		}
	}
}
