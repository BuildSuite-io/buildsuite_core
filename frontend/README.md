# BuildSuite Prototype

A clickable, functional prototype of BuildSuite Core — the open source construction-ops Frappe app. Built as a Vue 3 SPA with browser localStorage as the data layer so stakeholders can demo end-to-end flows (create project → add work package → assign tasks → mark progress) without any backend infrastructure.

This is **not** the production Frappe app. It's a **design and feedback artifact** that lets you walk customers, the dev team, and Frappe reviewers through the BuildSuite UX before code is written on the Frappe side.

Developer-facing implementation details (including list view APIs and renderer presets) are documented in `DEVELOPER_GUIDE.md`.

---

## What's in this prototype

**Workspace launcher (home page)** — V16-style admin landing with 12 workspaces.

**Functional pages with localStorage persistence:**
- Dashboard with live KPIs
- Projects: list (with subprojects), detail (7 tabs), new project form, edit-in-place
- Work Packages: list, detail with linked tasks
- Tasks: list with multi-filter, detail with progress slider, new task form
- Schedule: Gantt-style timeline for work packages or tasks
- Scope Change Orders (M7): list with cost-impact rollup

**Placeholder pages (stubbed for next builds):** BOQ, Procurement, Subcontractor, Labour, Financials, Reports.

Everything you create — projects, tasks, edits, status changes, progress updates — persists in your browser's localStorage. Refresh the page and your data is still there.

---

## Setup on your local machine (VS Code)

### Prerequisites

You need **Node.js 18 or higher**. Check by opening a terminal and running:

```bash
node --version
```

If you don't have it, download from https://nodejs.org/ (LTS version).

### 1. Open this folder in VS Code

```bash
cd buildsuite-prototype
code .
```

### 2. Install dependencies

In the VS Code integrated terminal (Terminal → New Terminal):

```bash
npm install
```

This downloads Vue, Vite, Pinia, Vue Router, and Tailwind. Takes about a minute.

### 3. Run the dev server

```bash
npm run dev
```

You'll see something like:

```
  VITE v5.x.x  ready in 350 ms

  ➜  Local:   http://localhost:5173/
```

Open that URL in your browser. The app should load with the workspace launcher.

The dev server has hot reload — any file you edit and save will refresh the browser automatically.

---

## Pushing to GitHub

### 1. Create a new GitHub repo

Go to https://github.com/new and create a new private (or public) repository called `buildsuite-prototype`. Don't initialize it with a README — we already have one.

### 2. Push this code

In the VS Code terminal:

```bash
git init
git add .
git commit -m "Initial prototype"
git branch -M main
git remote add origin https://github.com/YOUR-USERNAME/buildsuite-prototype.git
git push -u origin main
```

Replace `YOUR-USERNAME` with your GitHub username.

---

## Deploying to Vercel

### Option A: One-click from GitHub (recommended)

1. Go to https://vercel.com/new and sign in with your GitHub account
2. Click "Import" next to the `buildsuite-prototype` repo
3. Vercel auto-detects Vite. Don't change any settings. Click "Deploy"
4. In ~60 seconds you'll get a URL like `buildsuite-prototype-abc123.vercel.app`

Every future `git push` to the `main` branch will auto-deploy to that URL.

### Option B: From your local machine via CLI

```bash
npm install -g vercel
vercel
```

Follow the prompts. First run links the project, subsequent runs deploy.

---

## How to make changes

### Add a new field to projects

1. Open `src/data/seed.js` and add the field to the seed data
2. Open `src/stores/index.js` and add it to the `addProject` action
3. Open `src/views/NewProjectView.vue` and add the form field
4. Open `src/views/ProjectDetailView.vue` and display it

### Add a new view

1. Create a new `.vue` file in `src/views/`
2. Add the route in `src/router/index.js`
3. Add the link in `src/layouts/DeskShell.vue` (sidebar navigation)

### Change brand colors

Open `tailwind.config.js`. The `brand` palette is what drives all the green styling.

### Reset the data

In the running app, click the user avatar or go to Settings → "Reset all data". Or open browser DevTools → Application → Local Storage → remove the `buildsuite:data:v1` key, then reload.

---

## Project structure

```
buildsuite-prototype/
├── package.json              # Dependencies & scripts
├── vite.config.js            # Vite build config
├── tailwind.config.js        # Tailwind theme with BuildSuite brand
├── postcss.config.js         # PostCSS config
├── vercel.json               # Vercel SPA rewrite rules
├── index.html                # HTML entry point
├── public/
│   └── favicon.svg           # BuildSuite logo (favicon)
└── src/
    ├── main.js               # App bootstrap
    ├── App.vue               # Root component
    ├── style.css             # Global styles & Tailwind
    ├── router/
    │   └── index.js          # Vue Router routes
    ├── stores/
    │   └── index.js          # Pinia store + localStorage persistence
    ├── data/
    │   └── seed.js           # Initial seed data
    ├── utils/
    │   └── format.js         # Number, currency, date formatters
    ├── components/
    │   ├── LogoIcon.vue      # SVG BuildSuite logo
    │   ├── StatusBadge.vue   # Status / priority badge
    │   └── UserAvatar.vue    # User avatar with name
    ├── layouts/
    │   └── DeskShell.vue     # Sidebar + topbar layout
    └── views/                # One file per page
        ├── HomeView.vue
        ├── DashboardView.vue
        ├── ProjectsView.vue
        ├── NewProjectView.vue
        ├── ProjectDetailView.vue
        ├── WorkPackagesView.vue
        ├── WorkPackageDetailView.vue
        ├── TasksView.vue
        ├── NewTaskView.vue
        ├── TaskDetailView.vue
        ├── ScheduleView.vue
        ├── ScoView.vue
        ├── PlaceholderView.vue
        └── SettingsView.vue
```

---

## The data layer

There's **no backend**. All data lives in `localStorage` under the key `buildsuite:data:v1`.

The Pinia store (`src/stores/index.js`) is the single source of truth. Every mutation through an action automatically persists to localStorage via the `_persist()` helper.

When you're ready for a real backend, you only need to change the actions in `src/stores/index.js` — the views and components don't need to know that the storage layer changed. Suggested next-step backends:

- **Supabase** (Postgres + auth + realtime) — easiest for multi-user prototypes
- **Firebase** — easy auth, decent realtime
- **The actual Frappe REST API** — once buildsuite_core is built, this is what production will use

---

## Common commands

| Command | What it does |
|---------|-------------|
| `npm install` | Install all dependencies (run once) |
| `npm run dev` | Start dev server with hot reload (the one you'll use most) |
| `npm run build` | Build production bundle into `dist/` |
| `npm run preview` | Preview the production build locally |

---

## Branding

The green hexagonal "B" logo and the BuildSuite name are your brand. The Frappe Framework is MIT-licensed which means you can build apps with your own branding on top of it. The Frappe Foundation only restricts use of *their* logos and the "Frappe" and "ERPNext" names. BuildSuite (your product) carries your identity — open source or proprietary.

Brand color: `#22C55E` (Tailwind `green-500`). Full palette in `tailwind.config.js` under `brand.*`.

---

## Known limitations

- **Single-user only**: no auth, no permissions. The admin sees everything by design — this is a prototype.
- **No file uploads**: drawings, photos, attachments are stubbed.
- **No real-time collaboration**: two browsers don't sync.
- **Search palette is decorative**: clicking ⌘K opens the modal but doesn't actually search yet.
- **Mobile layout is partial**: the desk shell sidebar doesn't collapse on small screens yet.

These are all addressable when we wire up a real backend.
