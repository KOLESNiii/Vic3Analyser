import zipfile
from pathlib import Path

import pytest

from vic3analyser.config import Config, Paths
from vic3analyser.ingest.melt import MeltError, melt_save

PLAINTEXT = 'meta_data = {\n  version = "1.0"\n}\ngame_date = 1836.1.1\n'


def _cfg(tmp_path: Path, rakaly: Path | None = None) -> Config:
    return Config(
        paths=Paths(
            vic3_install=None,
            save_dir=None,
            mod_dirs=[],
            rakaly_bin=rakaly,
            data_dir=tmp_path / "data",
        ),
        player_tag=None,
    )


def test_plaintext_save(tmp_path):
    save = tmp_path / "text.v3"
    save.write_text(PLAINTEXT)
    res = melt_save(save, _cfg(tmp_path))
    assert res.source == "plaintext"
    assert "game_date" in res.gamestate


def test_zip_text_save(tmp_path):
    save = tmp_path / "ziptext.v3"
    with zipfile.ZipFile(save, "w") as zf:
        zf.writestr("meta", 'version = "1.0"')
        zf.writestr("gamestate", PLAINTEXT)
    res = melt_save(save, _cfg(tmp_path))
    assert res.source == "zip-text"
    assert "game_date" in res.gamestate
    assert res.meta is not None


def test_binary_without_rakaly_errors(tmp_path):
    save = tmp_path / "binary.v3"
    # Non-zip, non-text bytes -> treated as binary needing rakaly.
    save.write_bytes(b"SAV0\x00\x01\x02\x03binary\x00tokens\x00here")
    with pytest.raises(MeltError, match="rakaly"):
        melt_save(save, _cfg(tmp_path, rakaly=None))


def test_missing_file_errors(tmp_path):
    with pytest.raises(MeltError, match="not found"):
        melt_save(tmp_path / "nope.v3", _cfg(tmp_path))
