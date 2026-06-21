import { readFileSync } from "node:fs";
import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";
import path from "path";
import frappeui from "frappe-ui/vite";

// Resolve the local Frappe backend for the dev-server proxy — from VITE_FRAPPE_HOST
// or the bench's site config — so no host/port is hardcoded in the repo. The proxy
// is dev-only; production assets are served by Frappe at the same origin.
function frappeBackend() {
	if (process.env.VITE_FRAPPE_HOST) return process.env.VITE_FRAPPE_HOST;
	try {
		const cfg = JSON.parse(
			readFileSync(path.resolve(__dirname, "../../../sites/common_site_config.json"), "utf8")
		);
		if (cfg.webserver_port) return `http://localhost:${cfg.webserver_port}`;
	} catch {
		/* not inside a bench (e.g. a CI asset build) — fall back to the Frappe default port */
	}
	return "http://localhost:8000";
}

export default defineConfig(({ command }) => ({
	base: command === "build" ? "/assets/buildsuite_core/frontend/" : "/",
	plugins: [
		// lucideIcons resolves ~icons/lucide/* used inside frappe-ui components.
		// frappeProxy / jinjaBootData / buildConfig are disabled — BuildSuite manages them separately.
		...frappeui({
			lucideIcons: true,
			frappeProxy: false,
			jinjaBootData: false,
			buildConfig: false,
		}),
		vue(),
	],
	resolve: {
		alias: [
			{ find: "@", replacement: path.resolve(__dirname, "./src") },
			{
				find: "frappe-ui-config",
				replacement: path.resolve(
					__dirname,
					"./node_modules/frappe-ui/src/utils/config.ts"
				),
			},
			{
				find: "frappe-ui-frappe-request",
				replacement: path.resolve(
					__dirname,
					"./node_modules/frappe-ui/src/utils/frappeRequest.js"
				),
			},
			{
				find: "frappe-ui-list-resource",
				replacement: path.resolve(
					__dirname,
					"./node_modules/frappe-ui/src/resources/listResource.js"
				),
			},
			{
				find: "frappe-ui-document-resource",
				replacement: path.resolve(
					__dirname,
					"./node_modules/frappe-ui/src/resources/documentResource.js"
				),
			},
			{
				find: "frappe-ui-file-upload-handler",
				replacement: path.resolve(
					__dirname,
					"./node_modules/frappe-ui/src/utils/fileUploadHandler.ts"
				),
			},
			// frappe-ui imports feather-icons as a default export, but modern ESM
			// resolution exposes named exports only. Route bare imports through a shim.
			{
				find: /^feather-icons$/,
				replacement: path.resolve(__dirname, "./src/shims/feather-icons-default.js"),
			},
		],
	},
	// frappe-ui uses ~icons/lucide/* virtual modules resolved by a custom Rollup
	// plugin. Exclude it from esbuild pre-bundling so Vite's plugin pipeline
	// (which has the lucideIcons Rollup plugin) handles it in dev mode.
	// debug is a CJS-only package pulled in transitively by frappe-ui's TextEditor
	// (tiptap). Since frappe-ui is excluded, debug never gets pre-bundled — include
	// it explicitly so esbuild converts it to ESM before the browser sees it.
	optimizeDeps: {
		exclude: ["frappe-ui"],
		include: ["debug"],
	},
	build: {
		outDir: path.resolve(__dirname, "../buildsuite_core/public/frontend"),
		emptyOutDir: true,
		manifest: "manifest.json",
		sourcemap: true,
	},
	server: {
		port: 5173,
		open: true,
		proxy: {
			// Forward the Frappe-owned paths to the backend so the SPA can use
			// relative URLs in dev exactly like it does in production (same origin).
			"^/(api|app|assets|files|private|login)(/|$)": {
				target: frappeBackend(),
				changeOrigin: true,
				secure: false,
			},
		},
	},
}));
