"""nsxt_robot — a reusable Robot Framework library for testing VMware NSX-T.

Provides ``NsxtLibrary`` (connection management, REST verbs, and realization
polling against the NSX-T Policy/Management API) and ``NsxtApi`` (JSON
extraction + typed status assertions), plus a set of ``.robot`` resource
files — packaged under ``nsxt_robot/resources/`` — covering NSX-T Policy API
operations, SSH traffic keywords, and structured ``bbprobe`` data-plane
probing.

Typical usage from a consuming suite::

    *** Settings ***
    Library     nsxt_robot.NsxtLibrary
    Library     nsxt_robot.NsxtApi
    Resource    nsxt_robot/resources/common.robot
    Resource    nsxt_robot/resources/policy_api.robot
"""

from __future__ import annotations

__version__ = "0.1.0"

# Both imports must follow __version__: api.py and library.py read it at class
# definition time (ROBOT_LIBRARY_VERSION), and library.py imports api.py.
from .api import NsxtApi  # noqa: E402
from .library import NsxtLibrary  # noqa: E402

__all__ = ["NsxtApi", "NsxtLibrary", "__version__"]
