COMMANDS = {
    'status': '查指定 incident 状态',
    'diag': '重新触发诊断',
    'run': '手动触发修复插件',
    'ignore': '标记 incident 为已忽略',
    'escalate': '升级到指定人',
    'help': '列出所有指令',
    'plugins': '列出可用插件',
}


class CommandParser:
    def parse(self, text: str) -> dict:
        parts = text.strip().split()
        if not parts or not parts[0].startswith('/'):
            return {'command': '', 'args': [], 'error': '无效指令'}

        cmd = parts[0][1:]
        args = parts[1:]

        if cmd not in COMMANDS:
            return {'command': cmd, 'args': args, 'error': f'未知指令: {cmd}'}

        return {'command': cmd, 'args': args, 'error': None}
