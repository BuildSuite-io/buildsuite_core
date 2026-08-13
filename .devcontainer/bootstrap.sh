#!/usr/bin/env bash
# One-time (idempotent) setup for the BuildSuite Core dev bench. Run inside the
# `frappe` container: bash /workspace/buildsuite_core/.devcontainer/bootstrap.sh
#
# What it does:
#   1. `bench init` a v16 bench into the persistent bench-data volume (skipped if
#      it already exists).
#   2. Point it at the sibling mariadb/redis containers instead of localhost.
#   3. `bench get-app` erpnext (BuildSuite Core requires it installed).
#   4. Symlink this repo (bind-mounted at /workspace/buildsuite_core) into
#      apps/buildsuite_core and register it with the bench — no `get-app`/git
#      clone, so host edits are reflected immediately with no resync step.
#   5. Create the site and install both apps (skipped if the site already exists).
set -euo pipefail

WORKSPACE=/workspace
BENCH_DIR="$WORKSPACE/frappe-bench"
APP_SRC="$WORKSPACE/buildsuite_core"
SITE_NAME="${SITE_NAME:-bs.local}"
DB_ROOT_PASSWORD="${DB_ROOT_PASSWORD:-changeit}"
ADMIN_PASSWORD="${ADMIN_PASSWORD:-admin}"

cd "$WORKSPACE"

if [ ! -d "$BENCH_DIR/apps/frappe" ]; then
  echo "==> bench init (version-16)"
  # $BENCH_DIR is the bench-data named volume's mount point — it always "exists"
  # (Docker creates it, even empty, before the container starts), but `bench init`
  # does a plain existence check and refuses to run against any pre-existing path.
  # It's also a live mount, so it can't just be rm -rf'd out of the way either. Init
  # into a scratch dir under $HOME instead (writable by frappe, unlike /workspace
  # itself, which is root-owned) and move the result into the mounted volume.
  SCRATCH="$HOME/_bench_init_tmp"
  rm -rf "$SCRATCH"
  cd "$HOME"
  bench init --skip-redis-config-generation --frappe-branch version-16 "$(basename "$SCRATCH")"
  cp -a "$SCRATCH/." "$BENCH_DIR/"
  rm -rf "$SCRATCH"
  cd "$WORKSPACE"
  # `apps/frappe` was pip-installed editable while still under $SCRATCH, so its
  # finder (site-packages/frappe.pth) — and every venv console-script shebang
  # except env/bin/python, a symlink to the stable pyenv interpreter — still
  # points at that now-deleted path. Re-run the editable install via `python -m
  # pip` (bypassing the broken shebangs) so it re-points at the moved location;
  # everything's already cached, so this doesn't re-download anything.
  "$BENCH_DIR/env/bin/python" -m pip install --quiet -e "$BENCH_DIR/apps/frappe"
else
  echo "==> frappe-bench already initialized, skipping bench init"
fi

cd "$BENCH_DIR"

echo "==> pointing bench at the mariadb/redis containers"
bench set-config -g db_host mariadb
bench set-config -g redis_cache redis://redis-cache:6379
bench set-config -g redis_queue redis://redis-queue:6379
bench set-config -g redis_socketio redis://redis-queue:6379

if [ ! -d apps/erpnext ]; then
  echo "==> bench get-app erpnext (version-16)"
  bench get-app --branch version-16 erpnext
else
  echo "==> erpnext already present, skipping get-app"
fi

# Appends $2 to file $1 as its own line, first adding a newline if the file's
# last line isn't already newline-terminated (plain `echo >>` would otherwise
# silently concatenate onto that last line, e.g. "erpnext" + "buildsuite_core"
# -> "erpnextbuildsuite_core" — a real bug hit while building this script).
append_line() {
  local file=$1 line=$2
  grep -qx "$line" "$file" 2>/dev/null && return 0
  if [ -s "$file" ] && [ "$(tail -c1 "$file")" != "" ]; then
    echo >>"$file"
  fi
  echo "$line" >>"$file"
}

if [ ! -e apps/buildsuite_core ]; then
  echo "==> linking buildsuite_core (bind-mounted repo, no clone)"
  ln -s "$APP_SRC" apps/buildsuite_core
fi
append_line apps.txt buildsuite_core
# `bench get-app` normally keeps sites/apps.txt (what the installer actually
# validates `--install-app` against) in sync with the bench-root apps.txt above;
# since buildsuite_core is linked in directly rather than fetched via get-app,
# it needs to be added here too or `install_app` rejects it as "not in apps.txt".
append_line sites/apps.txt buildsuite_core
echo "==> pip install -e apps/buildsuite_core"
# `env/bin/pip`'s own shebang can be stale after the bench-init relocation above
# (see the comment there) — go through `python -m pip` so this isn't order-dependent.
"$BENCH_DIR/env/bin/python" -m pip install --quiet -e apps/buildsuite_core

# frappe-mcp==0.1.0's declared "pydantic~=2.11.7" pin has no Python 3.14 wheel
# and fails to build from source on this bench's Python. pyproject.toml above
# already pins its real runtime deps (pydantic 2.12+, which does have 3.14
# wheels) directly, so install frappe-mcp itself with --no-deps to skip pip's
# (unsatisfiable-on-3.14) resolution of its declared bound.
echo "==> pip install --no-deps frappe-mcp==0.1.0"
"$BENCH_DIR/env/bin/python" -m pip install --quiet --no-deps frappe-mcp==0.1.0

if [ ! -d "sites/$SITE_NAME" ]; then
  echo "==> creating site $SITE_NAME (installing erpnext)"
  bench new-site \
    --mariadb-user-host-login-scope='%' \
    --db-root-password "$DB_ROOT_PASSWORD" \
    --admin-password "$ADMIN_PASSWORD" \
    --install-app erpnext \
    "$SITE_NAME"
  bench use "$SITE_NAME"
  # `bench new-site --install-app erpnext` only registers the app — the root
  # master data ("All Supplier Groups", "All Item Groups", etc.) that erpnext
  # apps generally assume exist is instead seeded by ERPNext's *setup wizard*
  # (erpnext/setup/setup_wizard/setup_wizard.py's "Installing presets" stage),
  # which is normally completed interactively and is skipped entirely here.
  # buildsuite_core's after_install (seed_subcontract_masters ->
  # seed_subcontractor_supplier_group) assumes "All Supplier Groups" exists and
  # crashes without it, so seed it directly via erpnext's own preset installer.
  echo "==> seeding ERPNext preset master data (normally done by its setup wizard)"
  bench --site "$SITE_NAME" execute erpnext.setup.setup_wizard.operations.install_fixtures.install \
    --kwargs '{"country": "United States"}'
else
  echo "==> site $SITE_NAME already exists, skipping new-site"
fi

# A separate, idempotent step (rather than bundled into the one-shot `new-site`
# call above) so a prior run that got this far but failed before installing
# buildsuite_core (e.g. the apps.txt bug above) self-heals on retry — bench
# install-app is a no-op if the app is already installed.
echo "==> ensuring buildsuite_core is installed on $SITE_NAME"
bench --site "$SITE_NAME" install-app buildsuite_core

cat <<EOF

==> Bootstrap complete.

  cd frappe-bench && bench start        # backend on :8000, auto-reloads on .py edits
  open http://localhost:8000/core        # log in as Administrator / $ADMIN_PASSWORD

Frontend hot reload (separate shell in this container):
  cd frappe-bench/apps/buildsuite_core/frontend && yarn install && yarn dev
EOF
