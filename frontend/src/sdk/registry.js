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
