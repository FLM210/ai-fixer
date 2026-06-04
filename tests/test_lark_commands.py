import pytest

from app.lark.commands import COMMANDS, CommandParser


class TestCommandParser:
    @pytest.fixture
    def parser(self):
        return CommandParser()

    def test_parse_status(self, parser):
        result = parser.parse("/status INC-001")
        assert result["command"] == "status"
        assert result["args"] == ["INC-001"]
        assert result["error"] is None

    def test_parse_help(self, parser):
        result = parser.parse("/help")
        assert result["command"] == "help"
        assert result["args"] == []
        assert result["error"] is None

    def test_parse_unknown_command(self, parser):
        result = parser.parse("/unknown arg1")
        assert result["command"] == "unknown"
        assert result["args"] == ["arg1"]
        assert result["error"] == "未知指令: unknown"

    def test_parse_non_command_text(self, parser):
        result = parser.parse("not a command")
        assert result["command"] == ""
        assert result["args"] == []
        assert result["error"] == "无效指令"

    def test_parse_empty_text(self, parser):
        result = parser.parse("")
        assert result["command"] == ""
        assert result["error"] == "无效指令"

    def test_parse_diag_with_args(self, parser):
        result = parser.parse("/diag INC-002")
        assert result["command"] == "diag"
        assert result["args"] == ["INC-002"]
        assert result["error"] is None

    def test_parse_run_with_plugin(self, parser):
        result = parser.parse("/run restart_pod INC-003")
        assert result["command"] == "run"
        assert result["args"] == ["restart_pod", "INC-003"]
        assert result["error"] is None

    def test_parse_ignore(self, parser):
        result = parser.parse("/ignore INC-004")
        assert result["command"] == "ignore"
        assert result["args"] == ["INC-004"]
        assert result["error"] is None

    def test_parse_escalate(self, parser):
        result = parser.parse("/escalate @user INC-005")
        assert result["command"] == "escalate"
        assert result["args"] == ["@user", "INC-005"]
        assert result["error"] is None

    def test_parse_plugins(self, parser):
        result = parser.parse("/plugins")
        assert result["command"] == "plugins"
        assert result["args"] == []
        assert result["error"] is None

    def test_commands_dict(self):
        assert "status" in COMMANDS
        assert "diag" in COMMANDS
        assert "run" in COMMANDS
        assert "ignore" in COMMANDS
        assert "escalate" in COMMANDS
        assert "help" in COMMANDS
        assert "plugins" in COMMANDS
        assert len(COMMANDS) == 7
