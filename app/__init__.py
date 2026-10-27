from pathlib import Path

from flask import Flask


def create_app():
    app = Flask(__name__)
    app.config["CATALYST_CENTER_CONFIG"] = "config.ini"
    app.config["DATABASE_PATH"] = Path(app.instance_path) / "catalyst_center.sqlite3"

    from app.routes import main

    app.register_blueprint(main)
    return app
