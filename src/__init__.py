from flask import Flask
from dynaconf import FlaskDynaconf


app = Flask(__name__, template_folder="../templates")
flask_conf = FlaskDynaconf(
    app,
    settings_files=["settings.yaml", ".secrets.yaml"],
)


from src import routes
from src.settings import *
