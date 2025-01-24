from argparse import Namespace
from pathlib import Path

from cyaudit.constants import (
    CONFIG_FILE_NAME,
    DEFAULT_CYAUDIT_CONFIG,
    GLOBAL_CONFIG_LOCATION,
)
from cyaudit.logging import logger


def main(args: Namespace) -> int:
    path: Path = create_config(args.path or ".", args.force or False)
    logger.info(f"Project initialized at {str(path)}")
    return 0


def create_config(
    project_path_str: str = ".", force: bool = False, no_global: bool = False
) -> Path:
    project_path = Path(project_path_str).resolve()
    config_path = project_path / CONFIG_FILE_NAME
    if not force and config_path.exists():
        raise FileExistsError(
            f"Config file exists: {config_path}.\nIf you're sure the file is ok to potentially overwrite, try creating a new config by running with `cyaudit init --force`"
        )

    if Path(GLOBAL_CONFIG_LOCATION).expanduser().exists() and not no_global:
        config_content = Path(GLOBAL_CONFIG_LOCATION).expanduser().read_text()
    else:
        config_content = DEFAULT_CYAUDIT_CONFIG

    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(config_content)
    return config_path
