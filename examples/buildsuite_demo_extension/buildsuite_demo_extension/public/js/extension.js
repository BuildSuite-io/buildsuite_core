// The demo extension: a plain ES module, no build step. It receives Core's SDK (Vue, the controls,
// the registries) and adds a page, a slot component and a workspace tile.

export default function register(sdk) {
	const { h } = sdk.vue;
	const { DeskPage, DeskSection } = sdk.controls;
	const { __ } = sdk.utils;

	// 1. A page inside the app shell.
	const DemoPage = {
		name: "DemoExtensionPage",
		setup() {
			return () =>
				h(
					DeskPage,
					{
						title: __("Demo extension"),
						subtitle: __("This page comes from the buildsuite_demo_extension app."),
						breadcrumbs: [
							{ label: __("Home"), to: "/home" },
							{ label: __("Demo extension") },
						],
					},
					{
						default: () =>
							h(DeskSection, { title: __("What this proves"), cols: 1 }, () =>
								h(
									"ul",
									{ class: "text-sm text-ink-700 list-disc pl-5 space-y-1" },
									[
										h(
											"li",
											__("A separate Frappe app added this page at runtime.")
										),
										h(
											"li",
											__(
												"The page is built from Core's own controls (DeskPage, DeskSection)."
											)
										),
										h(
											"li",
											__(
												"Core was not rebuilt and knows nothing about this app."
											)
										),
									]
								)
							),
					}
				);
		},
	};
	sdk.routes.add({ path: "demo-extension", name: "demo-extension", component: DemoPage });

	// 2. A component in a slot every page has (here: the top of the Settings page).
	const Banner = {
		name: "DemoExtensionBanner",
		setup() {
			return () =>
				h(
					"div",
					{
						class: "mb-3 px-3 py-2 text-xs border border-ink-200 bg-ink-50 text-ink-700",
						style: "border-radius: 6px",
						"data-test": "demo-extension-banner",
					},
					__("Added by the demo extension through the slot page.settings.top.")
				);
		},
	};
	sdk.slots.add("page.settings.top", Banner);

	// 3. A workspace tile.
	sdk.workspaces.addTile("sales", {
		label: __("Demo extension"),
		description: __("A page added by an installed app"),
		to: "/demo-extension",
		icon: "🧩",
	});

	// 4. Wrap a Core page: Data Tools gets a notice above it, the Core view renders unchanged below.
	const DataToolsFrame = {
		name: "DemoDataToolsFrame",
		inheritAttrs: false,
		props: { original: { type: Object, required: true } },
		setup(props, { attrs }) {
			return () => [
				h(
					"div",
					{
						class: "mb-3 px-3 py-2 text-xs border border-ink-200 bg-ink-50 text-ink-700",
						style: "border-radius: 6px",
						"data-test": "demo-wrapped-notice",
					},
					__(
						"This page is wrapped by the demo extension; the Core view is unchanged below."
					)
				),
				h(props.original, attrs),
			];
		},
	};
	sdk.views.wrap("settings-data", DataToolsFrame);

	// 5. Replace a Core page: the app-icon diagnostics page becomes a page from this app.
	sdk.views.override("settings-app-icon-diagnostics", {
		name: "DemoDiagnosticsOverride",
		setup() {
			return () =>
				h(DeskPage, { title: __("Diagnostics (overridden)") }, () =>
					h(
						"p",
						{ class: "text-sm text-ink-700", "data-test": "demo-overridden" },
						__("This page replaces the Core view and comes from the demo extension.")
					)
				);
		},
	});

	// 6. Hooks on the generic DocType form ("*" = every doctype) and a slot on one doctype's form.
	sdk.doctype("*").on({
		onLoad() {
			window.__demoDocHooks = (window.__demoDocHooks || 0) + 1; // lets the test see it ran
		},
		beforeSave(payload) {
			const bad = Object.values(payload).some(
				(v) => typeof v === "string" && v.includes("FORBIDDEN-DEMO")
			);
			if (bad) throw new Error(__("The demo extension refuses this value."));
		},
	});
	sdk.slots.add("form.Account Category.top", {
		name: "DemoFormNotice",
		setup() {
			return () =>
				h(
					"div",
					{
						class: "mb-3 px-3 py-2 text-xs border border-ink-200 bg-ink-50 text-ink-700",
						style: "border-radius: 6px",
						"data-test": "demo-form-notice",
					},
					__(
						"Added to this form by the demo extension (slot form.Account Category.top)."
					)
				);
		},
	});

	// 7. A component that throws while rendering — switched on from the browser console to show that
	//    a failing extension is contained: localStorage.buildsuite_demo_break = "1", then reload.
	let breakIt = false;
	try {
		breakIt = window.localStorage.getItem("buildsuite_demo_break") === "1";
	} catch {
		/* storage unavailable */
	}
	if (breakIt) {
		sdk.slots.add("page.settings.bottom", {
			name: "DemoExtensionBroken",
			setup() {
				return () => {
					throw new Error("demo extension: deliberately broken component");
				};
			},
		});
	}
}
