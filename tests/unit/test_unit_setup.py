import tempfile
from pathlib import Path

from cyaudit.commands.setup import copy_template_folder_to


def test_copy_template_folder_to():
    with tempfile.TemporaryDirectory() as temp_dir:
        test_dir = Path(temp_dir) / "test_output"

        copy_template_folder_to(str(test_dir))

        assert test_dir.exists(), "Output directory wasn't created"
        assert (test_dir / "output").exists(), "output directory not found"
        assert (test_dir / "source").exists(), "source directory not found"
        assert (test_dir / "templates").exists(), "templates not found"
