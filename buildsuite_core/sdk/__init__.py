# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""The BuildSuite Python SDK: the stable surface for apps that extend BuildSuite Core.

Import from `buildsuite_core.sdk`, not from Core's internals. Everything exported here is
versioned with SDK_VERSION; anything else may change without notice. See
docs/extension-sdk-plan.md."""

from buildsuite_core.sdk.custom_fields import apply_custom_fields, custom_field_values
from buildsuite_core.sdk.customisations import get_customisations
from buildsuite_core.sdk.extensions import SDK_VERSION, get_extension_entries
from buildsuite_core.sdk.seed import seed_if_missing
from buildsuite_core.sdk.settings_pages import get_settings_pages

__all__ = [
	"SDK_VERSION",
	"apply_custom_fields",
	"custom_field_values",
	"get_customisations",
	"get_extension_entries",
	"get_settings_pages",
	"seed_if_missing",
]
