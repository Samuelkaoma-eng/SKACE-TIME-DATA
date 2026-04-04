from pathlib import Path
import shutil
import uuid

import pytest

try:
    from hypothesis import settings
except ImportError:  # pragma: no cover - hypothesis is available in test env
    settings = None


if settings is not None:
    settings.register_profile("local", deadline=None)
    settings.load_profile("local")


class LocalTmpPathFactory:
    def __init__(self, root: Path):
        self.root = root
        self.root.mkdir(exist_ok=True)

    def mktemp(self, basename: str) -> Path:
        path = self.root / f"{basename}_{uuid.uuid4().hex}"
        path.mkdir()
        return path


@pytest.fixture(scope="session")
def tmp_path_factory() -> LocalTmpPathFactory:
    root = Path("test_runtime_tmp")
    root.mkdir(exist_ok=True)
    try:
        yield LocalTmpPathFactory(root)
    finally:
        shutil.rmtree(root, ignore_errors=True)


@pytest.fixture
def tmp_path() -> Path:
    """
    Repo-local replacement for pytest's built-in tmp_path fixture.

    The default tmpdir plugin is unreliable in this Windows environment because
    the global temp root is permission-constrained. We create a temp directory
    inside the repository instead and clean it up after each test.
    """
    root = Path("test_runtime_tmp")
    root.mkdir(exist_ok=True)
    temp_dir = root / f"case_{uuid.uuid4().hex}"
    temp_dir.mkdir()
    try:
        yield temp_dir
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
