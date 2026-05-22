from pathlib import Path

from flask import Flask

from .database import init_db
from .routes import register_routes


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["SECRET_KEY"] = "openbooks-local-dev"
    app.config["DATABASE_PATH"] = Path(app.root_path).parent / "openbooks.db"

    init_db(app.config["DATABASE_PATH"])
    register_routes(app)
    return app
