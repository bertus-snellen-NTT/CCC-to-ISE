from flask import Flask


def create_app():
    app = Flask(__name__)
    app.config["CATALYST_CENTER_CONFIG"] = "config.ini"

    from app.routes import main

    app.register_blueprint(main)
    return app
