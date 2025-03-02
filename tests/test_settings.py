from pathlib import Path
from unittest import mock

import platformdirs
import pytest

from gitlab_personal_issue_board import settings


@pytest.mark.parametrize(
    "defined", [pytest.param(True, id="defined"), pytest.param(False, id="undefined")]
)
def test_load_settings_gitlab_section(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, defined: bool
) -> None:
    """
    Gitlab config section is defined in config
    """
    config_dir_mock = mock.Mock(return_value=tmp_path)
    monkeypatch.setattr(platformdirs, "user_config_dir", config_dir_mock)

    if defined:
        config_file = tmp_path / "config.toml"
        config_file.write_text("[gitlab]\nconfig_section = 'my_gitlab_conf_section'\n")
    settings.load_settings.cache_clear()

    result = settings.load_settings()

    if defined:
        assert result.gitlab.config_section == "my_gitlab_conf_section"
    else:
        assert result.gitlab.config_section is None

    assert config_dir_mock.call_args_list == [
        mock.call(settings.APP_NAME),
    ]
