"""Unit tests for SecurityKeywords (tags, groups, DFW)."""

from __future__ import annotations

from nsxt_robot.keywords.rest import RestKeywords
from nsxt_robot.keywords.security import SecurityKeywords


class _Lib(SecurityKeywords, RestKeywords):
    def __init__(self, connections):
        self._connections = connections


def test_set_tags_on_segment(spy_connections, spy_session):
    lib = _Lib(spy_connections)
    lib.set_tags_on_segment("seg-a", "app|web", "tier|frontend")
    _, path, body = spy_session.last
    assert path == "/policy/api/v1/infra/segments/seg-a"
    assert body == {"tags": [{"scope": "app", "tag": "web"}, {"scope": "tier", "tag": "frontend"}]}


def test_set_tags_on_segment_no_value(spy_connections, spy_session):
    lib = _Lib(spy_connections)
    lib.set_tags_on_segment("seg-a", "smoke")
    _, _, body = spy_session.last
    assert body["tags"] == [{"scope": "smoke", "tag": ""}]


def test_create_ip_group(spy_connections, spy_session):
    lib = _Lib(spy_connections)
    lib.create_ip_group("grp-src", ["172.16.1.10"])
    _, path, body = spy_session.last
    assert path == "/policy/api/v1/infra/domains/default/groups/grp-src"
    assert body["expression"] == [{"resource_type": "IPAddressExpression", "ip_addresses": ["172.16.1.10"]}]


def test_create_ip_group_custom_domain(spy_connections, spy_session):
    lib = _Lib(spy_connections)
    lib.create_ip_group("grp-src", ["172.16.1.10"], domain="custom")
    _, path, _ = spy_session.last
    assert path == "/policy/api/v1/infra/domains/custom/groups/grp-src"


def test_create_tag_group(spy_connections, spy_session):
    lib = _Lib(spy_connections)
    lib.create_tag_group("grp-tag", "app|bbtest")
    _, path, body = spy_session.last
    assert path == "/policy/api/v1/infra/domains/default/groups/grp-tag"
    expr = body["expression"][0]
    assert expr == {
        "resource_type": "Condition",
        "member_type": "VirtualMachine",
        "key": "Tag",
        "operator": "EQUALS",
        "value": "app|bbtest",
    }


def test_get_group(spy_connections, spy_session):
    spy_session.when("/policy/api/v1/infra/domains/default/groups/grp-1", {"id": "grp-1"})
    lib = _Lib(spy_connections)
    assert lib.get_group("grp-1") == {"id": "grp-1"}


def test_get_group_members(spy_connections, spy_session):
    spy_session.when(
        "/policy/api/v1/infra/domains/default/groups/grp-1/members/virtual-machines",
        {"results": [{"display_name": "172.16.2.10"}]},
    )
    lib = _Lib(spy_connections)
    members = lib.get_group_members("grp-1")
    assert members["results"][0]["display_name"] == "172.16.2.10"


def test_delete_group(spy_connections, spy_session):
    lib = _Lib(spy_connections)
    lib.delete_group("grp-1")
    assert spy_session.last[:2] == ("DELETE", "/policy/api/v1/infra/domains/default/groups/grp-1")


def test_create_security_policy(spy_connections, spy_session):
    lib = _Lib(spy_connections)
    lib.create_security_policy("policy-1")
    _, path, body = spy_session.last
    assert path == "/policy/api/v1/infra/domains/default/security-policies/policy-1"
    assert body == {"display_name": "policy-1", "category": "Application", "sequence_number": "10"}


def test_create_dfw_rule_defaults(spy_connections, spy_session):
    lib = _Lib(spy_connections)
    lib.create_dfw_rule("policy-1", "rule-1", ["/infra/.../grp-src"], ["/infra/.../grp-dst"])
    _, path, body = spy_session.last
    assert path == "/policy/api/v1/infra/domains/default/security-policies/policy-1/rules/rule-1"
    assert body["action"] == "ALLOW"
    assert body["services"] == ["ANY"]
    assert body["direction"] == "IN_OUT"


def test_create_dfw_rule_deny_action(spy_connections, spy_session):
    lib = _Lib(spy_connections)
    lib.create_dfw_rule(
        "policy-1", "rule-1", ["/infra/.../grp-src"], ["/infra/.../grp-dst"], action="DROP"
    )
    _, _, body = spy_session.last
    assert body["action"] == "DROP"


def test_get_dfw_rules(spy_connections, spy_session):
    spy_session.when(
        "/policy/api/v1/infra/domains/default/security-policies/policy-1/rules",
        {"results": [{"id": "rule-1", "action": "DROP"}]},
    )
    lib = _Lib(spy_connections)
    rules = lib.get_dfw_rules("policy-1")
    assert rules["results"][0]["action"] == "DROP"


def test_delete_dfw_rule(spy_connections, spy_session):
    lib = _Lib(spy_connections)
    lib.delete_dfw_rule("policy-1", "rule-1")
    assert spy_session.last[:2] == (
        "DELETE",
        "/policy/api/v1/infra/domains/default/security-policies/policy-1/rules/rule-1",
    )


def test_delete_security_policy(spy_connections, spy_session):
    lib = _Lib(spy_connections)
    lib.delete_security_policy("policy-1")
    assert spy_session.last[:2] == (
        "DELETE",
        "/policy/api/v1/infra/domains/default/security-policies/policy-1",
    )
