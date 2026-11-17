# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

import click
import frappe
from frappe.commands import pass_context


@click.command("new-buildsuite-extension")
@click.argument("app")
@click.option("--title", help="Human-readable app title")
@click.option("--dest", help="Folder to create the app in (default: the bench apps folder)")
@pass_context
def new_buildsuite_extension(context, app, title=None, dest=None):
	"""Create a BuildSuite extension app from the template."""
	from buildsuite_core.sdk.scaffold import create_extension_app

	path = create_extension_app(app, title, dest)
	click.echo(f"Created {path}")
	click.echo(f"Next: bench --site <site> install-app {app}  (after bench get-app {path})")


commands = [new_buildsuite_extension]
