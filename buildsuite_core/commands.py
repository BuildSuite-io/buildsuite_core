"""Custom bench CLI commands for buildsuite_core.

Discovered by bench via the module-level `commands` list. Usage:

    bench change-app-route core
"""

import click


@click.command("change-app-route")
@click.argument("new_route")
def change_app_route(new_route):
	"""Rename the BuildSuite frontend route (e.g. `bench change-app-route core`).

	Rewrites the single route token in hooks.py + frontend/src/utils/appRoute.js
	and renames the www/<route>.{py,html} page, then prints the follow-up build/
	restart steps.
	"""
	from buildsuite_core.route import rename_app_route

	click.echo(rename_app_route(new_route))


commands = [change_app_route]
