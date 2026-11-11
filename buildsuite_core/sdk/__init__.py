# Copyright (c) 2026, Infraholic Innovations Pvt. Ltd and contributors
# For license information, please see license.txt

"""The BuildSuite Python SDK: the stable surface for apps that extend BuildSuite Core.

Import from `buildsuite_core.sdk`, not from Core's internals. Everything exported here is
versioned with SDK_VERSION; anything else may change without notice. See
docs/extension-sdk-plan.md."""

from buildsuite_core.sdk.extensions import SDK_VERSION, get_extension_entries
from buildsuite_core.sdk.seed import seed_if_missing

__all__ = ["SDK_VERSION", "get_extension_entries", "seed_if_missing"]
