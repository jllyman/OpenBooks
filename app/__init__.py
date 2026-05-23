from pathlib import Path
from secrets import token_hex

from flask import Flask

from .database import init_db
from .routes import register_routes


def get_secret_key(app_root: Path) -> str:
    secret_path = app_root.parent / ".openbooks_secret"
    if not secret_path.exists():
        secret_path.write_text(token_hex(32), encoding="utf-8")
    return secret_path.read_text(encoding="utf-8").strip()


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["SECRET_KEY"] = get_secret_key(Path(app.root_path))
    app.config["DATABASE_PATH"] = Path(app.root_path).parent / "openbooks.db"
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

    init_db(app.config["DATABASE_PATH"])
    register_routes(app)
    return app
