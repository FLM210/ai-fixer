import importlib
import os
import pkgutil
import sys
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import TypeVar

from app.llm import ToolSpec
from app.plugins.base import Plugin, PluginCategory, PluginSpec, ResourceType

T = TypeVar("T", bound=Plugin)

# 自定义插件目录
CUSTOM_PLUGINS_DIR = os.environ.get(
    "CUSTOM_PLUGINS_DIR",
    os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "custom_plugins"),
)


class PluginRegistry:
    def __init__(self) -> None:
        self._plugins: dict[str, Plugin] = {}
        self._disabled: set[str] = set()
        self._loaded_plugins: dict[str, str] = {}  # name -> module_path
        self._plugin_sources: dict[str, str] = {}  # name -> "builtin" | "custom"
        self._plugin_files: dict[str, str] = {}  # name -> file_path

    def register(self, plugin: Plugin, module_path: str = "") -> None:
        name = plugin.spec.name
        self._plugins[name] = plugin
        if module_path:
            self._loaded_plugins[name] = module_path

        # 检测来源和文件路径
        source = "builtin"
        file_path = ""
        if module_path:
            if "custom" in module_path.lower() or CUSTOM_PLUGINS_DIR in module_path:
                source = "custom"
        # 通过 sys.modules 检查模块文件路径
        if module_path and module_path in sys.modules:
            mod = sys.modules[module_path]
            if hasattr(mod, "__file__") and mod.__file__:
                file_path = mod.__file__
                if "custom_plugins" in mod.__file__:
                    source = "custom"
        self._plugin_sources[name] = source
        if file_path:
            self._plugin_files[name] = file_path

    def get(self, name: str) -> Plugin:
        if name in self._disabled:
            raise KeyError(f"plugin is disabled: {name}")
        if name not in self._plugins:
            raise KeyError(f"plugin not found: {name}")
        return self._plugins[name]

    def has(self, name: str) -> bool:
        return name in self._plugins and name not in self._disabled

    def list_specs(
        self,
        category: PluginCategory | None = None,
        resource_type: ResourceType | None = None,
        include_disabled: bool = False,
    ) -> list[PluginSpec]:
        plugins = self._plugins.values()
        if not include_disabled:
            plugins = (p for p in plugins if p.spec.name not in self._disabled)
        specs: Iterable[PluginSpec] = (p.spec for p in plugins)
        if category is not None:
            specs = (s for s in specs if s.category == category)
        if resource_type is not None:
            specs = (s for s in specs if s.resource_type == resource_type)
        return sorted(specs, key=lambda s: s.name)

    def as_tool_specs(self, category: PluginCategory | None = None) -> list[ToolSpec]:
        return [
            ToolSpec(
                name=s.name,
                description=s.description,
                input_schema=s.input_schema,
            )
            for s in self.list_specs(category=category)
        ]

    def enable(self, name: str) -> bool:
        if name not in self._plugins:
            return False
        self._disabled.discard(name)
        return True

    def disable(self, name: str) -> bool:
        if name not in self._plugins:
            return False
        self._disabled.add(name)
        return True

    def is_disabled(self, name: str) -> bool:
        return name in self._disabled

    def get_plugin_source(self, name: str) -> str:
        """获取插件来源：builtin 或 custom。"""
        return self._plugin_sources.get(name, "builtin")

    def get_plugin_file(self, name: str) -> str:
        """获取插件文件路径。"""
        return self._plugin_files.get(name, "")

    def reload(self, disabled_names: list[str] | None = None) -> list[str]:
        """重新加载所有插件，返回加载的插件名列表。

        Args:
            disabled_names: 从数据库加载的已禁用插件名列表
        """
        self._plugins.clear()
        self._loaded_plugins.clear()
        self._plugin_sources.clear()
        if disabled_names is not None:
            self._disabled = set(disabled_names)
        # else: 保留当前 _disabled 状态

        self.discover_builtin()
        self.discover_custom()
        return [s.name for s in self.list_specs(include_disabled=True)]

    def clear(self) -> None:
        self._plugins.clear()
        self._loaded_plugins.clear()
        self._plugin_sources.clear()
        self._disabled.clear()

    def discover_builtin(self) -> None:
        """递归 import app.plugins.builtin 子模块。"""
        self._discover_package("app.plugins.builtin")

    def discover_custom(self) -> None:
        """发现自定义插件目录中的插件。"""
        custom_dir = Path(CUSTOM_PLUGINS_DIR)
        if not custom_dir.exists():
            custom_dir.mkdir(parents=True, exist_ok=True)
            return

        # 把自定义目录加入 sys.path
        custom_dir_str = str(custom_dir)
        if custom_dir_str not in sys.path:
            sys.path.insert(0, custom_dir_str)

        for py_file in custom_dir.glob("*.py"):
            if py_file.name.startswith("_"):
                continue
            module_name = py_file.stem
            try:
                if module_name in sys.modules:
                    importlib.reload(sys.modules[module_name])
                else:
                    importlib.import_module(module_name)
            except Exception:
                import logging

                logging.getLogger(__name__).exception("加载自定义插件失败: %s", py_file.name)

        # 检查子包
        for sub_dir in custom_dir.iterdir():
            if sub_dir.is_dir() and not sub_dir.name.startswith("_"):
                init_file = sub_dir / "__init__.py"
                if init_file.exists():
                    try:
                        pkg_name = sub_dir.name
                        if pkg_name in sys.modules:
                            importlib.reload(sys.modules[pkg_name])
                        else:
                            importlib.import_module(pkg_name)
                    except Exception:
                        import logging

                        logging.getLogger(__name__).exception(
                            "加载自定义插件包失败: %s", sub_dir.name
                        )

    def _discover_package(self, package_name: str) -> None:
        """递归发现包内所有模块。"""
        pkg = importlib.import_module(package_name)
        for _finder, modname, ispkg in pkgutil.iter_modules(pkg.__path__):
            fullname = f"{package_name}.{modname}"
            if fullname in sys.modules:
                importlib.reload(sys.modules[fullname])
            else:
                importlib.import_module(fullname)
            if ispkg:
                self._discover_package(fullname)

    def get_all_plugin_info(self) -> list[dict]:
        """获取所有插件的详细信息。"""
        result = []
        for name, plugin in sorted(self._plugins.items()):
            spec = plugin.spec
            result.append(
                {
                    "name": name,
                    "category": spec.category,
                    "resource_type": spec.resource_type,
                    "risk_level": spec.risk_level,
                    "timeout_seconds": spec.timeout_seconds,
                    "description": spec.description,
                    "enabled": name not in self._disabled,
                    "source": self.get_plugin_source(name),
                }
            )
        return result

    def get_disabled_list(self) -> list[str]:
        """获取已禁用的插件名列表。"""
        return sorted(self._disabled)

    def load_disabled_from_list(self, disabled: list[str]) -> None:
        """从列表加载已禁用的插件。"""
        self._disabled = set(disabled)


global_registry = PluginRegistry()


def register(reg: PluginRegistry) -> Callable[[type[T]], type[T]]:
    """类装饰器:实例化插件类并注册到指定 registry。"""

    def _decorator(cls: type[T]) -> type[T]:
        # 获取模块路径用于判断来源
        module_path = getattr(cls, "__module__", "")
        reg.register(cls(), module_path=module_path)
        return cls

    return _decorator
