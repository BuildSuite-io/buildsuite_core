# Docker dev environment

A self-contained dev bench for BuildSuite Core: MariaDB + two Redis instances + a
`frappe` container (the official `frappe/bench:latest` image, which already ships
Python 3.14 / Node 24 — matching this repo's pinned toolchain) with this repo bind-mounted
in live. No separate `frappe_docker` checkout needed.

This is a **development** setup only (plaintext dev passwords, no TLS/proxy) — not a
production deployment. See [frappe_docker](https://github.com/frappe/frappe_docker) directly
if you need that.

## First run (once per machine)

```bash
cp .devcontainer/.env.example .devcontainer/.env    # adjust passwords if you want
make docker-up          # start mariadb/redis/frappe containers
make docker-bootstrap    # bench init + get-app erpnext + new-site (takes a while the
                          # first time — it's downloading/building a full Frappe v16
                          # + ERPNext bench from scratch; safe to re-run, later runs
                          # are fast since everything lands in the bench-data volume)
make docker-hosts         # adds "127.0.0.1 bs.local" to /etc/hosts (asks for sudo once)
```

That creates a v16 bench, installs ERPNext + BuildSuite Core, and creates the site
`bs.local` (override via `.env`'s `SITE_NAME`). `make docker-bootstrap` is idempotent —
re-running it (e.g. after `make docker-down`) just confirms everything's already there
and exits quickly; it does **not** redo the slow first-time setup.

Alternatively, open this repo in VS Code with the Dev Containers extension and run
**"Reopen in Container"** — it uses the same compose file and runs `bootstrap.sh`
automatically via `postCreateCommand`.

## Stopping

```bash
make docker-down    # stops + removes the containers
```

This is safe and cheap — it does **not** touch the `bench-data` / `mariadb-data` named
volumes, so nothing bootstrapped above is lost. `docker compose ps` will show nothing
running; that's expected.

## Next time (day to day, after the first run)

```bash
make docker-up      # containers back up, same bootstrapped bench-data volume
make docker-shell     # shell into the frappe container

cd frappe-bench && bench start     # backend on :8000, auto-reloads on .py edits
```

No need to re-run `bootstrap.sh` or `docker-hosts` — both are one-time steps per volume
/ machine, not per container restart (re-run `docker-hosts` only if `/etc/hosts` gets
reset, e.g. a fresh machine; it's idempotent either way).

Then open `http://bs.local:8000/core` and log in as `Administrator` / the
`ADMIN_PASSWORD` from `.env` (default `admin`). Frappe routes by the `Host` header, so
`http://localhost:8000` alone 404s ("localhost does not exist") — that's what
`docker-hosts` fixes; a header-injecting browser extension (e.g. ModHeader) against
`http://localhost:8000/core` works too if you'd rather not touch `/etc/hosts`.

Frontend hot reload, in a second shell in the same container:

```bash
make docker-shell
cd frappe-bench/apps/buildsuite_core/frontend
yarn install
yarn dev     # :5173, /api proxied to the bench on :8000
```

Edits to `buildsuite_core/` or `frontend/` on the host are reflected immediately —
the repo is bind-mounted, not copied, and `buildsuite_core` is `pip install -e`'d.

Run the usual gate from inside the container, exactly as documented in the root
`README.md` (`apps/buildsuite_core` is this repo):

```bash
cd frappe-bench/apps/buildsuite_core
make lint
make test SITE=bs.local
```

## Ports

| Port | What |
|---|---|
| 8000 | Frappe web (`bench start`) |
| 9000 | Frappe realtime / socketio |
| 5173 | Vite dev server (`yarn dev`) |
| 6787 | Frappe asset watcher |

## Resetting

Everything bench-managed (frappe/erpnext source, the site, the venv) lives in the
`bench-data` named volume; MariaDB data lives in `mariadb-data`. To wipe both and start
completely over (re-triggers the slow first-time `bootstrap.sh` download/build):

```bash
make docker-down
docker volume rm devcontainer_bench-data devcontainer_mariadb-data
```

Volume names are prefixed with the compose project name, which defaults to the
directory the compose file lives in (`.devcontainer` → `devcontainer`) — run
`docker volume ls` to confirm if that ever differs (e.g. if compose is invoked with
`--project-name` or `-p` from a different working directory).
