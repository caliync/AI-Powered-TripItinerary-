from pathlib import Path

import pytest

from app.config import BACKEND_DIR
from app.places.seed import load_seed
from app.planner.catalog import Catalog

HOTEL_MARCIANO = {"lat": 14.1960653, "lng": 121.1436264}


@pytest.fixture(scope="session")
def seed():
    return load_seed(BACKEND_DIR / "data")


@pytest.fixture(scope="session")
def catalog(seed) -> Catalog:
    return Catalog.build(seed.places, seed.details)


@pytest.fixture
def tmp_db(tmp_path: Path) -> Path:
    return tmp_path / "test.db"
