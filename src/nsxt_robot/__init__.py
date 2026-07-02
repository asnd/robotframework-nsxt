"""nsxt_robot — a reusable Robot Framework library for testing VMware NSX-T.

Provides ``NsxtApi`` (JSON extraction + typed status assertions for the NSX-T
Policy/Management API) plus a set of ``.robot`` resource files — packaged under
``nsxt_robot/resources/`` — covering REST session/realization helpers, NSX-T
Policy API operations, SSH traffic keywords, and structured ``bbprobe``
data-plane probing.

Typical usage from a consuming suite::

    *** Settings ***
    Library     nsxt_robot.NsxtApi
    Resource    nsxt_robot/resources/common.robot
    Resource    nsxt_robot/resources/policy_api.robot
"""

from __future__ import annotations

__version__ = "0.1.0"

from .api import NsxtApi  # noqa: E402 — must follow __version__ (api.py imports it)

__all__ = ["NsxtApi", "__version__"]
