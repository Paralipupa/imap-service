import os, re, time, logging
from shutil import rmtree
from werkzeug.routing import Rule
from flask import (
    Response,
    request,
    send_from_directory,
    render_template,
    jsonify,
    make_response,
)
from flask_api import status
from flask_restful import abort
from src import app, api
from .auth import multi_auth

logger = logging.getLogger(__name__)


@app.route("/mail", defaults={"id": None})
@app.route("/mail/<int:id>", methods=["GET"])
@multi_auth.login_required()
def fetch_messages(id):
    """получить список писем по вхождению ИНН или ОГРН в
    заголовке и тексте писем.
    Если указан идентификатор письма то получаем только
    это письмо.
    """
    param, param_page = __get_param(id=id)
    data = multi_auth.current_user()
    __check_auth(data, param)
    result = api.fetch_messages(**param)
    __check_result(result)
    try:
        url = __get_url_without_page()
        paginat = __get_pagination(result, url, **(param | param_page))
        if param_page["json"] in "true,yes,1":
            return jsonify(paginat)
        else:
            return render_template(
                "results.html", paginat=paginat, url=request.host_url
            )
    except Exception as ex:
        api.fetch_messages.cache_clear()
        abort(status.HTTP_500_INTERNAL_SERVER_ERROR, **dict(message=f"{ex}"))


@app.route("/mail/<int:id>/attachments", defaults={"attach": "0"})
@app.route("/mail/<int:id>/attachments/<string:attach>", methods=["GET"])
@multi_auth.login_required()
def fetch_attachments(id: int, attach: str):
    """получить вложения по идентификатору письма
    и идентификатору файла. Если нет идент.файла,
    то скачиваются все файлы из письма в виде архива
    """
    param, _ = __get_param(id=id, attach=attach)
    data = multi_auth.current_user()
    __check_auth(data, param)
    file_name = api.fetch_attachments(**param)
    __check_result(file_name)
    if file_name:
        if os.path.exists(file_name):
            responce = __download_file(file_name)
            __remove_files(os.path.dirname(file_name))
            return responce
        else:
            responce = Response(
                f"Файл '{os.path.basename(file_name)}' не найден.\n",
                status=status.HTTP_404_NOT_FOUND,
            )
    abort(status.HTTP_404_NOT_FOUND, **dict(message="file not found "))


### Обработка ошибок запросов ###################################################
def get_error_response(error, code, message, **kwargs):
    error_message = (
        (error.data.get("message") if hasattr(error, "data") else None)
        or kwargs.get("message")
        or message
    )
    logger.error("%s: error: %s ", code, error_message)
    response = make_response(
        {
            "result": "error",
            "error": error_message,
        },
        code,
    )
    response.headers["Content-Type"] = "application/json; charset=utf-8"
    return response


@app.errorhandler(status.HTTP_404_NOT_FOUND)
def not_found(error, **kwargs):
    return get_error_response(
        error, status.HTTP_404_NOT_FOUND, "404 Not found", **kwargs
    )


@app.errorhandler(status.HTTP_400_BAD_REQUEST)
def bad_request(error, **kwargs):
    return get_error_response(
        error, status.HTTP_400_BAD_REQUEST, "400 Bad Request", **kwargs
    )


@app.errorhandler(status.HTTP_401_UNAUTHORIZED)
def unauthorized(error, **kwargs):
    return get_error_response(
        error, status.HTTP_401_UNAUTHORIZED, "401 Unauthorized", **kwargs
    )


@app.errorhandler(status.HTTP_500_INTERNAL_SERVER_ERROR)
def int_error(error, **kwargs):
    return get_error_response(
        error, status.HTTP_500_INTERNAL_SERVER_ERROR, "500 Internal Error", **kwargs
    )


#################################################################################################


def __get_param(id=None, attach=None):
    param = {}
    param["id"] = id
    param["attach"] = attach
    param["inn"] = request.args.get("inn")
    param["ogrn"] = request.args.get("ogrn")
    param_page = {}
    # возвращает только json
    param_page["json"] = request.args.get("json_only", "yes")
    param_page["page"] = request.args.get("page", "1")
    param_page["page_size"] = request.args.get(
        "page_size", str(app.config.PAGINATOR.PageSize)
    )
    if param_page["page"].isdigit():
        param_page["page"] = int(param_page["page"])
    else:
        param_page["page"] = 1
    if param_page["page"] < 1:
        param_page["page"] = 1

    if param_page["page_size"].isdigit():
        param_page["page_size"] = int(param_page["page_size"])
    else:
        param_page["page_size"] = int(app.config.PAGINATOR.page_size)
    if param_page["page_size"] < 1:
        param_page["page_size"] = app.config.PAGINATOR.PageSize

    if app.config.DEBUG:
        param_page["timer"] = time.time()

    return param, param_page


def __download_file(filename: str):
    return send_from_directory(
        os.path.dirname(filename), os.path.basename(filename), as_attachment=True
    )


def __remove_files(path: str):
    if os.path.isdir(path):
        rmtree(path)


def __get_url_without_page():
    """убрать параметры page и page_size из url"""
    url = request.host_url
    path_b = re.findall(".+(?=\?)", request.full_path)
    if path_b:
        path_b = path_b[0]
    path_a = re.findall("(?<=\?).+", request.full_path)
    if path_a:
        path_a = re.sub("&page=[0-9]*|&page_size=[0-9]*", "", path_a[0])
    return url.rstrip("/") + path_b + ("?" + path_a if path_a else "")


def __get_pagination(data: list, url, **param):
    count = len(data)
    page_num = param["page"]
    page_size = param["page_size"]
    max_pages = (count // page_size) + (1 if count % page_size != 0 else 0)
    paginat = {}
    paginat["inn"] = param["inn"]
    paginat["ogrn"] = param["ogrn"]
    paginat["page"] = page_num
    paginat["page_size"] = page_size
    paginat["count"] = max_pages
    if page_num == 1:
        paginat["previous"] = ""
    else:
        paginat["previous"] = url + "&page={0}&page_size={1}".format(
            page_num - 1, page_size
        )
    if page_num >= max_pages:
        paginat["next"] = ""
    else:
        paginat["next"] = url + "&page={0}&page_size={1}".format(
            page_num + 1, page_size
        )
    if paginat["previous"] or paginat["next"]:
        paginat["current"] = url + "&page={0}&page_size={1}".format(page_num, page_size)
    else:
        paginat["current"] = url
    paginat["results"] = data[(page_num - 1) * page_size : page_num * page_size]
    if app.config.DEBUG:
        paginat["timer"] = time.time() - param["timer"]
    return paginat


def __check_auth(data, param):
    if data["error"]:
        abort(status.HTTP_400_BAD_REQUEST, **dict(message=data["error"])),

    if data["ogrn"] != param["ogrn"] and data["inn"] != param["inn"]:
        abort(status.HTTP_401_UNAUTHORIZED)


def __check_result(result):
    if isinstance(result, list):
        if (
            result
            and isinstance(result[0], object)
            and hasattr(result[0], "error")
            and result[0].error
        ):
            abort(
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                **dict(message=result[0].error),
            )
    elif isinstance(result, object):
        if hasattr(result, "error") and result.error:
            abort(status.HTTP_500_INTERNAL_SERVER_ERROR, **dict(message=result.error))
    elif isinstance(result, dict):
        if result.get("error"):
            abort(
                status.HTTP_500_INTERNAL_SERVER_ERROR, **dict(message=result["error"])
            )
