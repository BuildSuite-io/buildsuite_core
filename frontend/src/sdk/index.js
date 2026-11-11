// The public JS SDK. An extension receives one of these in its `register(sdk)` call; this file is
// the whole contract. Anything not reachable from here is private and may change in any release.
// Bump SDK_VERSION's major when the surface changes incompatibly, its minor when it only grows
// (the Python SDK carries the same number: buildsuite_core.sdk.SDK_VERSION).

import * as vue from "vue";
import * as vueRouter from "vue-router";
import DeskPage from "@/components/desk/DeskPage.vue";
import DeskForm from "@/components/desk/DeskForm.vue";
import DeskSection from "@/components/desk/DeskSection.vue";
import DeskField from "@/components/desk/DeskField.vue";
import DeskInput from "@/components/desk/DeskInput.vue";
import DeskSelect from "@/components/desk/DeskSelect.vue";
import DeskTextarea from "@/components/desk/DeskTextarea.vue";
import DeskLinkPicker from "@/components/desk/DeskLinkPicker.vue";
import DeskActionBar from "@/components/desk/DeskActionBar.vue";
import DeskList from "@/components/desk/DeskList.vue";
import ExtensionSlot from "@/components/ExtensionSlot.vue";
import { usePermissions } from "@/composables/usePermissions";
import { useDoctypeMeta } from "@/composables/useDoctypeMeta";
import { useDocTypeList } from "@/composables/useDocTypeList";
import { useFormErrors } from "@/composables/useFormErrors";
import { useConfirm } from "@/composables/useConfirm";
import { useActiveCompany } from "@/composables/useActiveCompany";
import { useExtensionFields } from "@/sdk/useExtensionFields";
import { showToast } from "@/utils/appToast";
import { __ } from "@/utils/translate";
import {
	addSlot,
	addWorkspaceTile,
	addDocHooks,
	addSettingsTile,
	setViewOverride,
	setViewWrapper,
} from "@/sdk/registry";

export const SDK_VERSION = "1.2"; // 1.1: views.override/wrap, doctype().on, form slots; 1.2: settings.addTile, useExtensionFields

/** The SDK object handed to one extension. `router` is the app router (routes are added to it). */
export function createSdk(extension, router) {
	return {
		version: SDK_VERSION,
		extension,

		// Core's own copies of Vue and the router, so an extension shares one reactivity system and
		// one router with the app instead of bundling a second.
		vue,
		vueRouter,

		routes: {
			/** A page inside the app shell: a vue-router record. `meta` guards apply as for Core
			 *  routes (meta.requiresAdmin, meta.workspace, meta.cap). */
			add(route) {
				if (!route?.path || !route?.component) {
					throw new Error("routes.add needs a path and a component");
				}
				router.addRoute("shell", route);
			},
		},

		slots: {
			/** Add a component to a named slot. Every page built on DeskPage (most of them) has page.<route-name>.top and
			 *  page.<route-name>.bottom (DeskPage). `opts.when(context)` shows it conditionally;
			 *  `opts.order` sorts several extensions. */
			add(name, component, opts) {
				addSlot(extension, name, component, opts);
			},
		},

		views: {
			/** Replace a Core page. `name` is its route name (see the router). */
			override(name, component) {
				setViewOverride(extension, name, component);
			},
			/** Render around a Core page. The wrapper gets the route's props plus `original`:
			 *  render it with h(props.original, attrs). */
			wrap(name, wrapper) {
				setViewWrapper(extension, name, wrapper);
			},
		},

		/** Hooks on the generic DocType form: sdk.doctype("ToDo").on({ defaults, onLoad,
		 *  beforeSave(payload, form), afterSave(doc, { isNew }) }). "*" matches every doctype.
		 *  Slots on that form: form.<DocType>.top and form.<DocType>.bottom. */
		doctype(doctype) {
			return {
				on(hooks) {
					addDocHooks(extension, doctype, hooks);
				},
			};
		},

		settings: {
			/** A tile on the Settings page: addTile("Acme", { label, to, description?, icon? }).
			 *  A page that is just a Single DocType needs no JavaScript: declare it in hooks.py
			 *  (buildsuite_settings_pages) instead. */
			addTile(group, tile) {
				addSettingsTile(extension, group, tile);
			},
		},

		workspaces: {
			/** A tile on a workspace landing: { label, to, description?, icon? }. */
			addTile(workspace, tile) {
				addWorkspaceTile(extension, workspace, tile);
			},
		},

		// Reusable controls, the same ones Core's own pages are built from.
		controls: {
			DeskPage,
			DeskForm,
			DeskSection,
			DeskField,
			DeskInput,
			DeskSelect,
			DeskTextarea,
			DeskLinkPicker,
			DeskActionBar,
			DeskList,
			ExtensionSlot,
		},

		composables: {
			usePermissions,
			useDoctypeMeta,
			useDocTypeList,
			useFormErrors,
			useConfirm,
			useActiveCompany,
			useExtensionFields,
		},

		utils: { __, showToast },
	};
}
