"""Command registration tests."""

from rag_enterprise.application.commands import CommandBase, CommandDispatcher
from rag_enterprise.application.common import Result
from rag_enterprise.application.handlers import CommandHandler


class RegisterProbeCommand(CommandBase):
    value: int


class RegisterProbeHandler:
    async def handle(self, command: RegisterProbeCommand) -> Result[int]:
        return Result.ok(command.value * 2)


def test_register_multiple_command_types() -> None:
    dispatcher = CommandDispatcher()

    class SecondCommand(CommandBase):
        value: str

    class SecondHandler:
        async def handle(self, command: SecondCommand) -> Result[str]:
            return Result.ok(command.value)

    dispatcher.register(RegisterProbeCommand, RegisterProbeHandler())
    dispatcher.register(SecondCommand, SecondHandler())

    assert dispatcher.is_registered(RegisterProbeCommand)
    assert dispatcher.is_registered(SecondCommand)


def test_handler_protocol_compatibility() -> None:
    handler: CommandHandler[RegisterProbeCommand, int] = RegisterProbeHandler()
    assert handler is not None
