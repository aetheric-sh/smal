"""Module defining tests for the SMALFile class, which represents a state machine in the SMAL format."""

from __future__ import annotations  # Until Python 3.14

from typing import TYPE_CHECKING

from smal.schemas.state_machine import SMALFile

if TYPE_CHECKING:
    from pathlib import Path


def test_serde(tmp_path: Path) -> None:
    """Test that serialization/deserialization of SMALFiles work.

    Args:
        tmp_path (Path): Pytest fixture for a temporary directory.

    """
    smal = SMALFile(machine="TestStateMachine", version="1.0.0", states=[])
    for supported_ext in SMALFile.SUPPORTED_FILE_EXTENSIONS:
        path = (tmp_path / "test_machine").with_suffix(supported_ext)
        smal.to_file(path)
        loaded = SMALFile.from_file(path)
        assert loaded.name == "TestStateMachine"
        assert loaded.version == "1.0.0"
