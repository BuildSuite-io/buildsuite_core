// Makes every named Core route replaceable. Called once on the route table before the router is
// created, so no view needs to change: each lazy component is wrapped to ask the registry first.
//
//   views.override(name, Component)  replaces the Core view
//   views.wrap(name, Wrapper)        renders around it: the wrapper receives the route's props plus
//                                    `original` (the Core component) and renders h(original, attrs)
//
// Lookup happens when the route is first resolved, after extensions have registered, so an
// extension needs no ordering. A wrapper that throws is dropped and the original shown instead.

import { h, onErrorCaptured, ref } from "vue";
import { viewOverride, viewWrapper } from "@/sdk/registry";

function wrapped(name, wrapper, original) {
	return {
		name: `Wrapped(${name})`,
		inheritAttrs: false,
		setup(_, { attrs }) {
			const failed = ref(false);
			onErrorCaptured((error) => {
				failed.value = true;
				console.warn(
					`[buildsuite] wrapper for view "${name}" failed; showing the original`,
					error
				);
				return false;
			});
			return () => (failed.value ? h(original, attrs) : h(wrapper, { ...attrs, original }));
		},
	};
}

async function resolveView(name, load) {
	const override = viewOverride(name);
	const wrapper = viewWrapper(name);
	if (!override && !wrapper) return load();
	const core = override || (await load());
	const base = core.default || core;
	return wrapper ? wrapped(name, wrapper, base) : base;
}

/** Walk the route table and make every lazily loaded, named route resolve through the registry. */
export function instrumentRoutes(routes) {
	for (const route of routes) {
		if (route.name && typeof route.component === "function") {
			const load = route.component;
			const name = route.name;
			route.component = () => resolveView(name, load);
		}
		if (route.children) instrumentRoutes(route.children);
	}
	return routes;
}
