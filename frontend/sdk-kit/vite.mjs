// Build kit for an extension app written with Vue single-file components.
//
//   // my_app/frontend/vite.config.mjs
//   import { extensionConfig } from "../../buildsuite_core/frontend/sdk-kit/vite.mjs";
//   export default extensionConfig({ root: import.meta.dirname, entry: "src/index.js",
//                                    outDir: "../my_app/public/js" });
//
// The output is ONE ES module (extension.js, plus extension.css) whose default export is
// register(sdk). It does not bundle Vue, the router or any Core code: imports of `vue`,
// `vue-router` and `@/…` are resolved to Core's own copies, which Core publishes as
// globalThis.__buildsuite before it loads extensions (sdk/index.js `runtime`). Only the parts of
// Core that are public SDK resolve; any other `@/…` import fails the build with a clear message,
// so an extension cannot quietly depend on Core internals.
//
// Styles: put `@tailwind utilities;` in src/style.css and import it from the entry. Tailwind runs over the extension's own sources with Core's theme (brand/ink colours)
// and no preflight reset, so the extension's classes look like Core's and nothing is restyled.

import { createRequire } from "node:module";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import vue from "@vitejs/plugin-vue";
import coreTailwind from "../tailwind.config.js";

const require = createRequire(import.meta.url);
const ID = (name) => `\0buildsuite-runtime:${name}`;
const rt = "globalThis.__buildsuite";

// `@/…` ids that are public SDK, and the runtime member each one stands for.
const CONTROLS = new Set([
  "DeskPage",
  "DeskForm",
  "DeskSection",
  "DeskField",
  "DeskInput",
  "DeskSelect",
  "DeskTextarea",
  "DeskLinkPicker",
  "DeskActionBar",
  "DeskList",
]);
const UTILS = {
  "@/utils/translate": ["__"],
  "@/utils/appToast": ["showToast"],
  "@/utils/format": ["fmtCurrency", "fmtDate"],
  "@/utils/frappeError": ["parseFrappeError"],
};

function exportsOf(pkg) {
  // Only identifier-safe, non-default names can become `export const x`.
  return Object.keys(require(pkg)).filter(
    (k) => /^[A-Za-z_$][\w$]*$/.test(k) && k !== "default"
  );
}

function module(source, names) {
  return {
    code:
      `const R = ${source};\nexport default R;\n` +
      names.map((n) => `export const ${n} = R.${n};`).join("\n"),
  };
}

function buildsuiteRuntime() {
  const vueNames = exportsOf("vue");
  const routerNames = exportsOf("vue-router");
  return {
    name: "buildsuite-runtime",
    enforce: "pre",
    resolveId(id) {
      if (
        id === "vue" ||
        id === "vue-router" ||
        id === "frappe-ui-frappe-request"
      )
        return ID(id);
      if (id.startsWith("@/")) {
        const key = id.replace(/\.vue$/, "");
        const base = key.split("/").pop();
        if (key.startsWith("@/components/desk/") && CONTROLS.has(base))
          return ID(id);
        if (key === "@/components/ExtensionSlot") return ID(id);
        if (key.startsWith("@/composables/")) return ID(id);
        if (UTILS[key]) return ID(id);
        this.error(
          `"${id}" is not part of the BuildSuite SDK, so an extension cannot import it. ` +
            "Use what the SDK hands to register(sdk), or ask for it to be added to the SDK."
        );
      }
      return null;
    },
    load(rid) {
      if (!rid.startsWith("\0buildsuite-runtime:")) return null;
      const id = rid.slice("\0buildsuite-runtime:".length);
      if (id === "vue") return module(`${rt}.vue`, vueNames);
      if (id === "vue-router") return module(`${rt}.vueRouter`, routerNames);
      if (id === "frappe-ui-frappe-request")
        return {
          code: `const f = ${rt}.utils.request; export const frappeRequest = f; export default f;`,
        };
      if (id === "@/components/ExtensionSlot.vue")
        return {
          code: `const C = ${rt}.controls.ExtensionSlot; export default C;`,
        };
      if (id.startsWith("@/components/desk/")) {
        const name = id
          .split("/")
          .pop()
          .replace(/\.vue$/, "");
        return { code: `const C = ${rt}.controls.${name}; export default C;` };
      }
      if (id.startsWith("@/composables/")) {
        const name = id.split("/").pop();
        return {
          code: `const C = ${rt}.composables.${name}; export const ${name} = C; export default C;`,
        };
      }
      return {
        code: UTILS[id]
          .map((n) => `export const ${n} = ${rt}.utils.${n};`)
          .join("\n"),
      };
    },
  };
}

export function extensionConfig({
  root,
  entry = "src/index.js",
  outDir,
  name = "extension",
}) {
  const dir = root || path.dirname(fileURLToPath(import.meta.url));
  return {
    root: dir,
    plugins: [buildsuiteRuntime(), vue()],
    css: {
      postcss: {
        plugins: [
          require("tailwindcss")({
            content: [path.join(dir, "src/**/*.{vue,js}")],
            darkMode: "class",
            theme: coreTailwind.theme,
            corePlugins: { preflight: false },
          }),
          require("autoprefixer"),
        ],
      },
    },
    build: {
      outDir: path.resolve(dir, outDir),
      emptyOutDir: false,
      cssCodeSplit: false,
      sourcemap: false,
      lib: {
        entry: path.resolve(dir, entry),
        formats: ["es"],
        fileName: () => `${name}.js`,
      },
      // One file, so the loader imports a single URL (no hashed chunks left behind).
      rollupOptions: {
        output: { assetFileNames: `${name}.[ext]`, inlineDynamicImports: true },
      },
    },
  };
}

export const kitUrl = pathToFileURL(fileURLToPath(import.meta.url)).href;
