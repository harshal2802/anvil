"""Shared regex for parsing PlanScribe-emitted PLAN-*.md headings."""

from __future__ import annotations

import re

# Matches PlanScribe's fixed "### Phase N: <name>" heading format.
# Flexible on whitespace (handles tabs, double-spaces) so callers don't
# silently miscount if formatting drifts.
PHASE_HEADING_RE = re.compile(
    r"^###\s+Phase\s+(\d+):\s+(.+?)\s*$",
    re.MULTILINE,
)
