"""Shell 执行插件：在容器/宿主机上执行 shell 命令。"""

import asyncio
import shlex
from typing import Any, ClassVar

from app.plugins.base import Plugin, PluginContext, PluginResult, PluginSpec
from app.plugins.registry import global_registry, register

# 危险命令黑名单
BLOCKED_PATTERNS: list[str] = [
    "rm -rf /",
    "mkfs",
    "dd if=",
    "> /dev/",
    "shutdown",
    "reboot",
    "halt",
    "init 0",
    "init 6",
    ":(){ :|:& };:",  # fork bomb
    "chmod 777 /",
    "chown root",
]

# 危险重定向/管道
BLOCKED_REDIRECTS: list[str] = [
    " > /etc/",
    " >> /etc/",
    " > /usr/",
    " > /boot/",
    " > /dev/sd",
]


def _is_command_safe(command: str) -> tuple[bool, str]:
    """检查命令是否安全。"""
    cmd_lower = command.lower().strip()

    # 检查黑名单
    for pattern in BLOCKED_PATTERNS:
        if pattern in cmd_lower:
            return False, f"危险命令: 包含 '{pattern}'"

    # 检查危险重定向
    for pattern in BLOCKED_REDIRECTS:
        if pattern in cmd_lower:
            return False, f"危险重定向: 包含 '{pattern}'"

    # 检查是否尝试写入关键目录
    try:
        parts = shlex.split(command)
        for part in parts:
            if part.startswith(">") or part.startswith(">>"):
                target = part.lstrip(">").strip()
                if target.startswith(("/etc", "/usr", "/boot", "/dev", "/proc", "/sys")):
                    return False, f"禁止写入: {target}"
    except ValueError:
        pass

    return True, ""


@register(global_registry)
class ShellExec(Plugin):
    _SCHEMA: ClassVar[dict[str, Any]] = {
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "minLength": 1,
                "description": "要执行的 shell 命令",
            },
            "reason": {
                "type": "string",
                "description": "执行原因",
            },
            "timeout": {
                "type": "integer",
                "description": "超时秒数(默认 30)",
                "default": 30,
            },
            "workdir": {
                "type": "string",
                "description": "工作目录(可选)",
            },
        },
        "required": ["command", "reason"],
        "additionalProperties": False,
    }

    @property
    def spec(self) -> PluginSpec:
        return PluginSpec(
            name="shell.exec",
            category="diagnostic",
            description="执行 shell 命令进行问题排查(读操作)。可用于查看日志、检查进程、网络诊断等。",
            risk_level="medium",
            requires_approval=False,
            timeout_seconds=60,
            input_schema=self._SCHEMA,
        )

    async def execute(self, ctx: PluginContext, args: dict[str, Any]) -> PluginResult:
        command = args["command"]
        reason = args.get("reason", "")
        timeout = min(args.get("timeout", 30), 120)  # 最大 120 秒
        workdir = args.get("workdir")

        # 安全检查
        safe, reason_blocked = _is_command_safe(command)
        if not safe:
            return PluginResult(
                ok=False,
                output={},
                error=f"命令被拒绝: {reason_blocked}",
            )

        try:
            proc = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=workdir,
            )

            try:
                stdout_bytes, stderr_bytes = await asyncio.wait_for(
                    proc.communicate(), timeout=timeout
                )
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
                return PluginResult(
                    ok=False,
                    output={"timeout": True},
                    error=f"命令超时 ({timeout}s): {command}",
                )

            stdout = stdout_bytes.decode("utf-8", errors="replace") if stdout_bytes else ""
            stderr = stderr_bytes.decode("utf-8", errors="replace") if stderr_bytes else ""

            # 截断输出（避免过大）
            max_output = 8000
            if len(stdout) > max_output:
                stdout = stdout[:max_output] + f"\n... (截断，共 {len(stdout_bytes)} 字节)"
            if len(stderr) > max_output:
                stderr = stderr[:max_output] + f"\n... (截断，共 {len(stderr_bytes)} 字节)"

            exit_code = proc.returncode or 0

            return PluginResult(
                ok=exit_code == 0,
                output={
                    "stdout": stdout,
                    "stderr": stderr,
                    "exit_code": exit_code,
                    "command": command,
                },
                evidence_snippets=[stdout[:500]] if stdout else [],
                error=stderr if exit_code != 0 else None,
            )

        except Exception as e:
            return PluginResult(ok=False, output={}, error=str(e))


@register(global_registry)
class ShellExecWrite(Plugin):
    """需要审批的写操作 shell 插件。"""

    _SCHEMA: ClassVar[dict[str, Any]] = {
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "minLength": 1,
                "description": "要执行的 shell 命令(写操作)",
            },
            "reason": {
                "type": "string",
                "description": "执行原因",
            },
            "timeout": {
                "type": "integer",
                "description": "超时秒数(默认 30)",
                "default": 30,
            },
        },
        "required": ["command", "reason"],
        "additionalProperties": False,
    }

    @property
    def spec(self) -> PluginSpec:
        return PluginSpec(
            name="shell.exec_write",
            category="remediation",
            description="执行 shell 命令(写操作，需审批)。用于修改配置、重启服务等。",
            risk_level="high",
            requires_approval=True,
            timeout_seconds=60,
            input_schema=self._SCHEMA,
        )

    async def execute(self, ctx: PluginContext, args: dict[str, Any]) -> PluginResult:
        command = args["command"]
        timeout = min(args.get("timeout", 30), 120)

        # 安全检查
        safe, reason_blocked = _is_command_safe(command)
        if not safe:
            return PluginResult(
                ok=False,
                output={},
                error=f"命令被拒绝: {reason_blocked}",
            )

        try:
            proc = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            try:
                stdout_bytes, stderr_bytes = await asyncio.wait_for(
                    proc.communicate(), timeout=timeout
                )
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
                return PluginResult(
                    ok=False,
                    output={"timeout": True},
                    error=f"命令超时 ({timeout}s)",
                )

            stdout = stdout_bytes.decode("utf-8", errors="replace") if stdout_bytes else ""
            stderr = stderr_bytes.decode("utf-8", errors="replace") if stderr_bytes else ""

            return PluginResult(
                ok=(proc.returncode or 0) == 0,
                output={
                    "stdout": stdout[:5000],
                    "stderr": stderr[:5000],
                    "exit_code": proc.returncode or 0,
                    "command": command,
                },
                error=stderr if (proc.returncode or 0) != 0 else None,
            )

        except Exception as e:
            return PluginResult(ok=False, output={}, error=str(e))
