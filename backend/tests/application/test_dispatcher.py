"""Dispatcher tests."""

import pytest

from rag_enterprise.application.commands import CommandBase, CommandDispatcher
from rag_enterprise.application.common import ErrorCode, Result
from rag_enterprise.application.queries import QueryBase, QueryDispatcher


class EchoCommand(CommandBase):
    message: str


class EchoQuery(QueryBase):
    message: str


class EchoCommandHandler:
    async def handle(self, command: EchoCommand) -> Result[str]:
        return Result.ok(command.message)


class FailingValidationCommand(CommandBase):
    message: str

    async def validate_command(self) -> Result[None]:
        return self.validation_error("invalid message", field="message")


class EchoQueryHandler:
    async def handle(self, query: EchoQuery) -> Result[str]:
        return Result.ok(query.message)


@pytest.mark.asyncio
async def test_command_dispatcher_registers_and_dispatches() -> None:
    dispatcher = CommandDispatcher()
    dispatcher.register(EchoCommand, EchoCommandHandler())

    result = await dispatcher.dispatch(EchoCommand(message="hello"))

    assert result.is_success
    assert result.unwrap() == "hello"


@pytest.mark.asyncio
async def test_command_dispatcher_returns_validation_failure() -> None:
    dispatcher = CommandDispatcher()
    dispatcher.register(FailingValidationCommand, EchoCommandHandler())

    result = await dispatcher.dispatch(FailingValidationCommand(message="bad"))

    assert result.is_failure
    assert result.error is not None
    assert result.error.code == ErrorCode.VALIDATION_FAILED


@pytest.mark.asyncio
async def test_command_dispatcher_returns_handler_not_found() -> None:
    dispatcher = CommandDispatcher()

    result = await dispatcher.dispatch(EchoCommand(message="hello"))

    assert result.is_failure
    assert result.error is not None
    assert result.error.code == ErrorCode.HANDLER_NOT_FOUND


@pytest.mark.asyncio
async def test_query_dispatcher_registers_and_dispatches() -> None:
    dispatcher = QueryDispatcher()
    dispatcher.register(EchoQuery, EchoQueryHandler())

    result = await dispatcher.dispatch(EchoQuery(message="read"))

    assert result.is_success
    assert result.unwrap() == "read"


@pytest.mark.asyncio
async def test_duplicate_command_registration_raises() -> None:
    dispatcher = CommandDispatcher()
    dispatcher.register(EchoCommand, EchoCommandHandler())

    with pytest.raises(ValueError, match="already registered"):
        dispatcher.register(EchoCommand, EchoCommandHandler())


def test_command_registration_state() -> None:
    dispatcher = CommandDispatcher()

    assert not dispatcher.is_registered(EchoCommand)
    dispatcher.register(EchoCommand, EchoCommandHandler())
    assert dispatcher.is_registered(EchoCommand)
