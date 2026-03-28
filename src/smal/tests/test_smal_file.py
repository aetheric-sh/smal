from pathlib import Path
from smal.schemas.smal_file import SMALFile

def test_serde(tmp_path: Path) -> None:
    smal = SMALFile(machine="TestStateMachine", version="1.0.0", states=[])
    for supported_ext in SMALFile.SUPPORTED_FILE_EXTENSIONS:
        path = (tmp_path / "test_machine").with_suffix(supported_ext)
        smal.to_file(path)
        loaded = SMALFile.from_file(path)
        assert loaded.machine == "TestStateMachine"
        assert loaded.version == "1.0.0"