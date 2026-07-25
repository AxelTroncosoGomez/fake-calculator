"""Shared pytest fixtures for the gcp test suite."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication


@pytest.fixture(scope="session")
def qapp():
    """Session-scoped QApplication for headless testing."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app
