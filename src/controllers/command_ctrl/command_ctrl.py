from dataclasses import dataclass
from typing import Any

from tortoise.expressions import F

from src.controllers.command_ctrl.command_parser import PromptLanguageParser
from src.controllers.command_ctrl.command_validator import (
    ValidationResult,
    validate_code_names,
)
from src.db.records import CommandRecord


@dataclass
class CommandInput:
    project_id: int
    code: str


@dataclass
class CommandOutput:
    id: int
    project_id: int
    order: int
    command_code: str
    command_json: dict[str, Any]


async def add_command(
    input: CommandInput, insert_at: int | None = None
) -> list[str] | None:
    """
    Add a new command. If insert_at is specified, insert at that position,
    otherwise append to the end.
    """
    if insert_at is None:
        # Append to end
        last_command = (
            await CommandRecord.filter(project_id=input.project_id)
            .order_by("-order")
            .first()
        )

        next_order = (last_command.order + 1) if last_command else 1
    else:
        # Insert at specific position - shift everything after it
        await CommandRecord.filter(
            project_id=input.project_id, order__gte=insert_at
        ).update(order=F("order") + 1)

        next_order = insert_at

    parser = PromptLanguageParser()
    command = parser.parse(input.code)
    valid_res = await validate_code_names(command)
    if not valid_res.is_valid:
        return valid_res.errors

    print("command_json", command)
    await CommandRecord.create(
        project_id=input.project_id,
        order=next_order,
        command_code=input.code,
        command_json=command.to_dict(),
    )


async def delete_command(command_id: int):
    """
    Delete a command and adjust the order of remaining commands.
    """
    command = await CommandRecord.get(id=command_id)
    project_id = command.project_id
    order = command.order

    await command.delete()

    # Shift down all commands after the deleted one
    await CommandRecord.filter(project_id=project_id, order__gt=order).update(
        order=F("order") - 1
    )


async def move_command(command_id: int, new_order: int) -> CommandOutput | None:
    """
    Move a command to a new position and reorder others accordingly.
    """
    command = await CommandRecord.get(id=command_id)
    old_order = command.order
    project_id = command.project_id

    if old_order == new_order:
        return None  # No change needed

    if old_order < new_order:
        # Moving down: shift commands between old and new position up
        await CommandRecord.filter(
            project_id=project_id, order__gt=old_order, order__lte=new_order
        ).update(order=F("order") - 1)
    else:
        # Moving up: shift commands between new and old position down
        await CommandRecord.filter(
            project_id=project_id, order__gte=new_order, order__lt=old_order
        ).update(order=F("order") + 1)

    command.order = new_order
    await command.save()

    return CommandOutput(
        id=command.id,
        project_id=command.project_id,
        order=command.order,
        command_code=command.command_code,
        command_json=command.command_json,
    )


async def increment_order(command_id: int) -> CommandOutput | None:
    """
    Move a command down by one position (increase order).
    """
    command = await CommandRecord.get(id=command_id)

    # Get the max order for this project
    max_command = (
        await CommandRecord.filter(project_id=command.project_id)
        .order_by("-order")
        .first()
    )
    assert max_command is not None

    if command.order >= max_command.order:
        return None  # Already at the end

    return await move_command(command_id, command.order + 1)


async def decrement_order(command_id: int) -> CommandOutput | None:
    """
    Move a command up by one position (decrease order).
    """
    command = await CommandRecord.get(id=command_id)

    if command.order <= 1:
        return None  # Already at the beginning

    return await move_command(command_id, command.order - 1)


async def reorder_project_commands(project_id: int):
    """
    Rebuild the order sequence to ensure it's 1, 2, 3, 4...
    Useful if you suspect gaps or inconsistencies.
    """
    commands = await CommandRecord.filter(project_id=project_id).order_by("order").all()

    for index, command in enumerate(commands, start=1):
        if command.order != index:
            command.order = index
            await command.save()


async def list_commands(project_id: int) -> list[CommandOutput]:
    query = CommandRecord.filter(project_id=project_id).order_by("order")

    commands = await query.all()
    out = []
    for cmd in commands:
        out.append(
            CommandOutput(
                id=cmd.id,
                project_id=cmd.project_id,
                order=cmd.order,
                command_code=cmd.command_code,
                command_json=cmd.command_json,
            )
        )
    return out
