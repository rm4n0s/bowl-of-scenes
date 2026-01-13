from src.controllers.command_ctrl.command_parser import PromptLanguageParser


def test_simple_parser():
    parser = PromptLanguageParser()
    cmd = parser.parse(
        "server -$ workflow_anime: characters x  poses(~jumping) x emotions(sad)"
    )
    assert cmd.server_code_name == "server"
    assert cmd.generator_code_name == "workflow_anime"
    assert cmd.group_selections[0].group_code_name == "characters"
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


def test_and_keyword_parser():
    parser = PromptLanguageParser()
    cmd = parser.parse(
        "server -$ workflow_anime: characters and anime x  poses(~jumping) and fighting(kick) x emotions(sad)"
    )
    assert cmd.group_selections[0].is_merged
    assert cmd.group_selections[1].is_merged
    assert cmd.group_selections[1].merged_groups is not None
    assert "jumping" in cmd.group_selections[1].merged_groups[0]["exclude"]
    assert "kick" in cmd.group_selections[1].merged_groups[1]["include_only"]
    assert not cmd.group_selections[2].is_merged
    assert cmd.group_selections[2].include_only is not None
    assert "sad" in cmd.group_selections[2].include_only
    assert cmd.fixers is None


def test_fixer_keyword_parser():
    parser = PromptLanguageParser()
    cmd = parser.parse(
        "server -$ workflow_anime: characters and anime > fixer1 > fixer2"
    )

    assert cmd.group_selections[0].is_merged
    assert cmd.fixers
    assert len(cmd.fixers) == 2
    assert cmd.fixers == ["fixer1", "fixer2"]

    cmd = parser.parse(
        "server -$ workflow_anime: characters and anime > fixer2 > fixer1"
    )

    assert cmd.fixers
    assert len(cmd.fixers) == 2
    assert cmd.fixers == ["fixer2", "fixer1"]


def test_color_coded_keyword_parser():
    parser = PromptLanguageParser()
    cmd = parser.parse(
        "server -$ workflow: group_1{red: group_2 and group5 x group_4(item1), blue: group_3 x group_4(item1)} x group_6 > fixer2 > fixer1"
    )

    assert cmd.fixers
    assert len(cmd.fixers) == 2
    assert cmd.fixers == ["fixer2", "fixer1"]

    assert cmd.group_selections[0].is_color_coded
    assert not cmd.group_selections[1].is_color_coded
    assert cmd.group_selections[1].color_coded_group_selections is None
    assert cmd.group_selections[1].group_code_name == "group_6"
    assert cmd.group_selections[0].color_coded_group_selections is not None
    assert "red" in cmd.group_selections[0].color_coded_group_selections.keys()
    assert "blue" in cmd.group_selections[0].color_coded_group_selections.keys()
    assert cmd.group_selections[0].color_coded_group_selections["red"][0].is_merged
    assert cmd.group_selections[0].color_coded_group_selections["red"][0].merged_groups
    assert (
        cmd.group_selections[0]
        .color_coded_group_selections["red"][0]
        .merged_groups[0]["group_code_name"]
        == "group_2"
    )
    assert cmd.group_selections[0].color_coded_group_selections["red"][1].include_only
    assert (
        "item1"
        in cmd.group_selections[0].color_coded_group_selections["red"][1].include_only
    )
