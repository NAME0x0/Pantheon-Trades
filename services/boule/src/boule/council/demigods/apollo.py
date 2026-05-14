"""Apollo namespace mirror — the signal engine lives in services/apollo.

This module is a forward-reference shim; the dashboard treats Apollo as
a demigod-tier participant, but the actual implementation is the
out-of-process Apollo service.
"""

from __future__ import annotations


class Apollo:
    """Marker class referenced by the council taxonomy."""

    name = "apollo"
    weight = 0.0
    has_veto = False
