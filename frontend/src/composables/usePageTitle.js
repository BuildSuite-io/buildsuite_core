import { watchEffect, unref } from "vue";
import { APP_TITLE } from "@/utils/appRoute";

/**
 * Reactively set the browser/document title to a page-specific value, e.g. the
 * name of the record on a detail page. Pass a ref, a getter, or a string of the
 * specific part — it's suffixed with the app name ("<value> · BuildSuite Core").
 *
 * The router's afterEach already sets a sensible per-route title; call this from a
 * view's setup to override it with something more specific once the record loads.
 * Empty/falsy values are ignored so the route-level title stays until data arrives.
 */
export function usePageTitle(source) {
	watchEffect(() => {
		const value = typeof source === "function" ? source() : unref(source);
		if (value) document.title = `${value} · ${APP_TITLE}`;
	});
}
