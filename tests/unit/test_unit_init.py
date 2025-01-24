from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from cyaudit.commands.init import create_config
from cyaudit.constants import CONFIG_FILE_NAME, DEFAULT_CYAUDIT_CONFIG


def test_create_config_default(monkeypatch):
    """Test creating config with default settings when no global config exists"""
    with TemporaryDirectory() as tmpdir:
        # Ensure global config doesn't exist for this test
        monkeypatch.setattr(
            "cyaudit.constants.GLOBAL_CONFIG_LOCATION", "/nonexistent/path"
        )

        # Call create_config with temp directory
        config_path = create_config(tmpdir)

        # Verify the config file was created
        assert config_path.exists()
        assert config_path.name == CONFIG_FILE_NAME
        assert config_path.read_text() == DEFAULT_CYAUDIT_CONFIG


def test_create_config_with_global(monkeypatch):
    """Test creating config by copying from existing global config"""
    with TemporaryDirectory() as tmpdir:
        global_config = Path(tmpdir) / "global_config.toml"
        test_content = "test_global_config = true\n"
        global_config.write_text(test_content)
        monkeypatch.setattr(
            "cyaudit.commands.init.GLOBAL_CONFIG_LOCATION", str(global_config)
        )
        with TemporaryDirectory() as project_dir:
            config_path = create_config(project_dir)

            assert config_path.exists()
            assert config_path.name == CONFIG_FILE_NAME
            assert config_path.read_text() == test_content


def test_create_config_no_global_flag(monkeypatch):
    """Test creating config with no_global flag ignores existing global config"""
    with TemporaryDirectory() as tmpdir:
        # Create a temporary global config
        global_config = Path(tmpdir) / "global_config.toml"
        test_content = "test_global_config = true\n"
        global_config.write_text(test_content)

        with TemporaryDirectory() as project_dir:
            monkeypatch.setattr(
                "cyaudit.constants.GLOBAL_CONFIG_LOCATION", str(global_config)
            )

            # Create the config with no_global=True
            config_path = create_config(project_dir, no_global=True)

            # Verify the config was created with default content
            assert config_path.exists()
            assert config_path.name == CONFIG_FILE_NAME
            assert config_path.read_text() == DEFAULT_CYAUDIT_CONFIG


def test_create_config_force_overwrite():
    """Test force flag allows overwriting existing config"""
    with TemporaryDirectory() as tmpdir:
        project_path = Path(tmpdir)
        config_path = project_path / CONFIG_FILE_NAME

        # Create initial config
        config_path.write_text("original_content")

        # Attempt to create new config with force flag
        new_config_path = create_config(tmpdir, force=True)

        # Verify the config was overwritten with default content
        assert new_config_path.resolve() == config_path.resolve()
        assert config_path.read_text() == DEFAULT_CYAUDIT_CONFIG


def test_create_config_exists_no_force():
    """Test FileExistsError is raised when config exists and no force flag"""
    with TemporaryDirectory() as tmpdir:
        project_path = Path(tmpdir)
        config_path = project_path / CONFIG_FILE_NAME

        # Create initial config
        config_path.write_text("original_content")

        # Attempt to create new config without force flag
        with pytest.raises(FileExistsError):
            create_config(tmpdir)


def test_create_config_nested_path():
    """Test creating config in nested directory structure"""
    with TemporaryDirectory() as tmpdir:
        nested_path = Path(tmpdir) / "deeply" / "nested" / "project"

        # Create config in nested path
        config_path = create_config(str(nested_path))

        # Verify the config was created in the correct location
        assert config_path.exists()
        assert config_path.resolve() == (nested_path / CONFIG_FILE_NAME).resolve()
        assert config_path.read_text() == DEFAULT_CYAUDIT_CONFIG
