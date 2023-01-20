from jiri_one.utils import create_new_file_name
from pathlib import Path

def test_create_new_file_name(tmp_path: Path):
    """ If I put random name, this function will add ' (1)' to its name or increment (1) by one if that file exists
    """
    file = tmp_path / "random_name.json"
    assert "random_name (1).json" == create_new_file_name(file).name
    for counter in range(1,6):
        (tmp_path / f"random_name ({counter}).json").write_text("some text")
        assert f"random_name ({counter+1}).json" == create_new_file_name(file).name
