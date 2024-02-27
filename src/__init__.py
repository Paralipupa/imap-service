from flask import Flask
from dynaconf import FlaskDynaconf
from flasgger import Swagger

app = Flask(__name__, template_folder="../templates")
flask_conf = FlaskDynaconf(
    app,
    settings_files=["settings.yaml", ".secrets.yaml"],
)
swagger = Swagger(app)

from src import routes
from src.settings import *
