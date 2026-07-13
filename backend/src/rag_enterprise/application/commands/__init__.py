"""Command package."""

from rag_enterprise.application.commands.base import Command, CommandBase

__all__ = ["Command", "CommandBase", "CommandDispatcher"]


def __getattr__(name: str) -> object:
    if name == "CommandDispatcher":
        from rag_enterprise.application.commands.dispatcher import CommandDispatcher

        return CommandDispatcher
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
