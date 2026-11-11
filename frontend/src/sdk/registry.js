// The extension registries: what installed apps have added to the SPA. Reactive, so a page that
// renders a slot or a tile group updates when an extension registers (including a later one).
// Core reads these through ExtensionSlot / WorkspaceReportsSection; extensions write them through
// the SDK object they receive (sdk/index.js), never directly.

import { shallowReactive, markRaw } from "vue";

const slots = shallowReactive({}); // slot name -> [{ id, extension, component, when }]
const workspaceTiles = shallowReactive({}); // workspace slug -> [{ id, extension, ...tile }]
let nextId = 1;

export function addSlot(extension, name, component, opts = {}) {
	if (!name || !component) throw new Error("slots.add needs a slot name and a component");
	const item = {
		id: `${extension}:${name}:${nextId++}`,
		extension,
		component: markRaw(component),
		when: typeof opts.when === "function" ? opts.when : null,
		order: Number(opts.order) || 0,
	};
	slots[name] = [...(slots[name] || []), item].sort((a, b) => a.order - b.order);
}

export function slotsFor(name) {
	return slots[name] || [];
}

export function addWorkspaceTile(extension, workspace, tile) {
	if (!workspace || !tile?.label || !tile?.to) {
		throw new Error("workspaces.addTile needs a workspace slug and a tile with label and to");
	}
	const list = workspaceTiles[workspace] || [];
	if (list.some((t) => t.extension === extension && t.to === tile.to)) return;
	workspaceTiles[workspace] = [...list, { id: `${extension}:${tile.to}`, extension, ...tile }];
}

export function tilesFor(workspace) {
	return workspaceTiles[workspace] || [];
}

// ---- Views: replace or wrap a Core page, by its route name --------------------------------------
const viewOverrides = {}; // route name -> component
const viewWrappers = {}; // route name -> component that renders props.original

function setView(table, kind, extension, name, component) {
	if (!name || !component) throw new Error(`views.${kind} needs a route name and a component`);
	if (table[name]) {
		console.warn(
			`[buildsuite] "${extension}" replaces an earlier views.${kind} for "${name}"`
		);
	}
	table[name] = markRaw(component);
}

export const setViewOverride = (extension, name, component) =>
	setView(viewOverrides, "override", extension, name, component);
export const setViewWrapper = (extension, name, component) =>
	setView(viewWrappers, "wrap", extension, name, component);
export const viewOverride = (name) => viewOverrides[name] || null;
export const viewWrapper = (name) => viewWrappers[name] || null;

// ---- DocType hooks: defaults / onLoad / beforeSave / afterSave on the generic form --------------
const docHooks = {}; // doctype ("*" for every one) -> [{ extension, ...hooks }]
const HOOKS = ["defaults", "onLoad", "beforeSave", "afterSave"];

export function addDocHooks(extension, doctype, hooks) {
	if (!doctype || !hooks) throw new Error("doctype(...).on needs a doctype and a hooks object");
	const unknown = Object.keys(hooks).filter(
		(k) => k !== "fields" && k !== "listColumns" && !HOOKS.includes(k)
	);
	if (unknown.length) throw new Error(`unknown DocType hook(s): ${unknown.join(", ")}`);
	(docHooks[doctype] ||= []).push({ extension, ...hooks });
}

/** The Custom Field names the extensions declare for a doctype (hooks.fields). */
export function docFields(doctype) {
	return [
		...new Set(
			[...(docHooks["*"] || []), ...(docHooks[doctype] || [])].flatMap((h) => h.fields || [])
		),
	];
}

/** The extra list columns the extensions declare for a doctype (hooks.listColumns):
 *  [{ field, label, align?, render?(value, row) }]. Lists show them after Core's own columns. */
export function listColumns(doctype) {
	const seen = new Set();
	return [...(docHooks["*"] || []), ...(docHooks[doctype] || [])]
		.flatMap((h) => h.listColumns || [])
		.filter((c) => c?.field && !seen.has(c.field) && seen.add(c.field));
}

/** Run one hook of every extension registered for the doctype (and for "*"), in order. A failing
 *  beforeSave stops the save and shows its message; a failure in any other hook is logged only. */
export async function runDocHook(doctype, hook, ...args) {
	for (const entry of [...(docHooks["*"] || []), ...(docHooks[doctype] || [])]) {
		if (typeof entry[hook] !== "function") continue;
		try {
			await entry[hook](...args);
		} catch (error) {
			if (hook === "beforeSave") throw error;
			console.warn(`[buildsuite] extension "${entry.extension}" ${hook} failed`, error);
		}
	}
}

// ---- Settings tiles: a tile on the Settings page (for a page the extension registers itself) ----
const settingsTiles = shallowReactive([]); // { id, extension, group, label, to, description?, icon? }

export function addSettingsTile(extension, group, tile) {
	if (!group || !tile?.label || !tile?.to) {
		throw new Error("settings.addTile needs a group and a tile with label and to");
	}
	if (settingsTiles.some((t) => t.extension === extension && t.to === tile.to)) return;
	settingsTiles.push({ id: `${extension}:${tile.to}`, extension, group, ...tile });
}

export const settingsTilesList = () => settingsTiles;
