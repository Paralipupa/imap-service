import os
from flask_httpauth import HTTPBasicAuth, HTTPTokenAuth, MultiAuth
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt import _jwt_required
from src import jwt, app

### Настройки авторизации
basic_user = {
    app.config.BASIC_AUTH.user: generate_password_hash(app.config.BASIC_AUTH.password),
}

basic_auth = HTTPBasicAuth()
token_auth = HTTPTokenAuth()
multi_auth = MultiAuth(basic_auth, token_auth)


@basic_auth.verify_password
@basic_auth.verify_password
def verify_password(user, password):
    if app.config.BASIC_AUTH.user == user and check_password_hash(
        basic_user[app.config.BASIC_AUTH.user], password
    ):
        return {"inn": "", "ogrn": ""}


@token_auth.verify_token
def verify_token(token):
    try:
        data = jwt.jwt_decode_callback(token)
        if app.debug:
            logger.info("verify_token: %s", data)
    except Exception as e:
        return _jwt_required(app.config["JWT_DEFAULT_REALM"])
    result = {
        "user_id": data.get("user_id"),
        "user_name": data.get("user_name"),
        "ogrn": data.get("ogrn"),
        "permissions": data.get("permissions"),
    }

    return result


#######################################################################################################
