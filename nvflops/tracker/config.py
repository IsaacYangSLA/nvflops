import os


class Config:
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    @staticmethod
    def init_app(app):
        pass


class DevelopmentConfig(Config):
    DEBUG = True
    SECRET_KEY = (os.environ.get("SECRET_KEY") or "dev_key",)
    SQLALCHEMY_DATABASE_URI = os.environ.get("DEV_DATABASE_URL") or "sqlite:///" + os.path.join(
        os.getcwd(), "status.sqlite"
    )
    # SQLALCHEMY_DATABASE_URI = 'postgresql://<username>:<password>@localhost:5432/nvflops'


class TestingConfig(Config):
    DEBUG = True
    TESTING = True
    SQLALCHEMY_DATABASE_URI = os.environ.get("TEST_DATABASE_URL")


config = {"development": DevelopmentConfig, "testing": TestingConfig, "default": DevelopmentConfig}
