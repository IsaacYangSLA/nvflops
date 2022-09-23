from datetime import datetime

from flask import Flask
from flask.json import JSONEncoder
from flask_sqlalchemy import SQLAlchemy

from .config import config

db = SQLAlchemy()


class CustomJSONEncoder(JSONEncoder):
    def default(self, obj):
        try:
            if isinstance(obj, datetime):
                return obj.isoformat()
            if isinstance(obj, db.Model):
                return obj.asdict()
            iterable = iter(obj)
        except TypeError:
            pass
        else:
            return list(iterable)
        return JSONEncoder.default(self, obj)


def create_app(config_name):
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)
    app.config.from_pyfile("./config.py")
    app.json_encoder = CustomJSONEncoder
    db.init_app(app)
    with app.app_context():
        from .apis import admin, routine, s3, submission

        app.register_blueprint(submission)
        app.register_blueprint(admin)
        app.register_blueprint(s3)
        app.register_blueprint(routine)
    return app
