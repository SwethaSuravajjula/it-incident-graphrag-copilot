from src.config import PROCESSED_DATA_DIR, PROJECT_ROOT, RAW_DATA_DIR


def test_data_dirs_live_under_project_root():
    assert RAW_DATA_DIR == PROJECT_ROOT / "data" / "raw"
    assert PROCESSED_DATA_DIR == PROJECT_ROOT / "data" / "processed"
    assert RAW_DATA_DIR.is_dir()
    assert PROCESSED_DATA_DIR.is_dir()
