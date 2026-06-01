import os
import pytest
import importlib


@pytest.fixture(autouse=True)
def set_env():
    """Override the parent conftest autouse fixture.

    Integration tests use real env vars from the environment (set in GH Actions
    or exported locally). The parent conftest sets fake env vars via monkeypatch
    for unit tests — this no-op prevents that from interfering here.
    """
    pass


@pytest.fixture(scope="session")
def integration_app(tmp_path_factory):
    """Flask app loaded with real env vars and a session-scoped temp DB.

    DB_PATH is set before reloading modules so all three modules (db, config, app)
    pick up the temp path. The DB persists for the entire test session so history
    tests can see runs from earlier tests.
    """
    tmp = tmp_path_factory.mktemp("integration_data")
    original_db_path = os.environ.get("DB_PATH")
    os.environ["DB_PATH"] = str(tmp / "integration.db")

    import app as app_module
    import db
    import config as config_module

    importlib.reload(db)
    importlib.reload(config_module)
    importlib.reload(app_module)
    db.init_db()

    app_module.flask_app.config["TESTING"] = True
    yield app_module.flask_app

    if original_db_path is None:
        os.environ.pop("DB_PATH", None)
    else:
        os.environ["DB_PATH"] = original_db_path


@pytest.fixture(scope="session")
def client(integration_app):
    """Session-scoped Flask test client. DB persists across all integration tests."""
    with integration_app.test_client() as c:
        yield c
