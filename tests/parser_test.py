from src.controllers.command_ctrl.command_parser import PromptLanguageParser


def test_parser():
    parser = PromptLanguageParser()
    cmd = parser.parse(
        "server -$ workflow_anime: character x  poses(~jumping) x emotions(sad)"
    )

    assert cmd.server_code_name == "server"
    assert cmd.workflow_code_name == "workflow_anime"
    assert cmd.group_selections[0].group_code_name == "character"
    assert cmd.group_selections[0].exclude is None
    assert cmd.group_selections[0].include_only is None
    assert cmd.group_selections[1].group_code_name == "poses"
    assert cmd.group_selections[1].exclude is not None
    assert "jumping" in cmd.group_selections[1].exclude
    assert cmd.group_selections[1].include_only is None
    assert cmd.group_selections[2].group_code_name == "emotions"
    assert cmd.group_selections[2].exclude is None
    assert cmd.group_selections[2].include_only is not None
    assert "sad" in cmd.group_selections[2].include_only
