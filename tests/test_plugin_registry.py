from typing import Any

import pytest

from app.llm import ToolSpec
from app.plugins.base import Plugin, PluginContext, PluginResult, PluginSpec
from app.plugins.registry import PluginRegistry, register


def _make_plugin_class(name: str, category: str = "diagnostic") -> type[Plugin]:
    class _P(Plugin):
        @property
        def spec(self) -> PluginSpec:
            return PluginSpec(
                name=name,
                category=category,  # type: ignore[arg-type]
                description="x",
                risk_level="low",
                timeout_seconds=5,
                input_schema={"type": "object", "properties": {}, "additionalProperties": False},
            )

        async def execute(self, ctx: PluginContext, args: dict[str, Any]) -> PluginResult:
            return PluginResult(ok=True)

    _P.__name__ = f"P_{name.replace('.', '_')}"
    return _P


def test_registry_register_and_get() -> None:
    reg = PluginRegistry()
    Cls = _make_plugin_class("k8s.foo")
    reg.register(Cls())
    assert reg.get("k8s.foo").spec.name == "k8s.foo"


def test_registry_duplicate_rejected() -> None:
    reg = PluginRegistry()
    reg.register(_make_plugin_class("k8s.foo")())
    with pytest.raises(ValueError):
        reg.register(_make_plugin_class("k8s.foo")())


def test_registry_unknown_raises() -> None:
    reg = PluginRegistry()
    with pytest.raises(KeyError):
        reg.get("does.not_exist")


def test_registry_list_specs_filtered_by_category() -> None:
    reg = PluginRegistry()
    reg.register(_make_plugin_class("k8s.diag1", "diagnostic")())
    reg.register(_make_plugin_class("k8s.diag2", "diagnostic")())
    reg.register(_make_plugin_class("k8s.fix1", "remediation")())
    diag = reg.list_specs(category="diagnostic")
    assert {s.name for s in diag} == {"k8s.diag1", "k8s.diag2"}
    fix = reg.list_specs(category="remediation")
    assert {s.name for s in fix} == {"k8s.fix1"}


def test_registry_as_tool_specs_returns_llm_compatible() -> None:
    reg = PluginRegistry()
    reg.register(_make_plugin_class("k8s.diag", "diagnostic")())
    tools = reg.as_tool_specs(category="diagnostic")
    assert len(tools) == 1
    assert isinstance(tools[0], ToolSpec)
    assert tools[0].name == "k8s.diag"


def test_register_decorator_uses_global_registry() -> None:
    # 先清掉 global registry
    from app.plugins.registry import global_registry
    global_registry.clear()

    @register(global_registry)
    class _Foo(Plugin):
        @property
        def spec(self) -> PluginSpec:
            return PluginSpec(
                name="dec.foo",
                category="diagnostic",
                description="x",
                risk_level="low",
                timeout_seconds=5,
                input_schema={"type": "object", "properties": {}, "additionalProperties": False},
            )

        async def execute(self, ctx: PluginContext, args: dict[str, Any]) -> PluginResult:
            return PluginResult(ok=True)

    assert global_registry.get("dec.foo").spec.name == "dec.foo"
    global_registry.clear()


def test_discover_builtin_finds_nothing_when_empty() -> None:
    reg = PluginRegistry()
    reg.discover_builtin()
    # Task 11 之前 builtin 包为空,期望不报错且不注册任何插件
    assert reg.list_specs() == []
