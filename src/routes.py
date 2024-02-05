import os, re, time, logging
from shutil import rmtree
from werkzeug.routing import Rule
from flask import Response, request, send_from_directory, render_template, jsonify
from flask_api import status
from src import app, api

logger = logging.getLogger(__name__)

app.url_map.add(Rule("/", defaults={"_404": ""}, endpoint="catch_all"))
app.url_map.add(Rule("/<path:_404>", endpoint="catch_all"))


@app.endpoint("catch_all")
def _404(_404):
    return Response(" ", status=status.HTTP_404_NOT_FOUND)


@app.route("/mail", defaults={"id": None})
@app.route("/mail/<int:id>", methods=["GET"])
def fetch_messages(id):
    """получить список писем по вхождению ИНН или ОГРН в
    заголовке и тексте писем.
    Если указан идентификатор письма то получаем только
    это письмо.
    """
    param, param_page = __get_param(id=id)
    result = api.fetch_messages(**param)
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
        logger.error(f"{ex}")
        api.fetch_messages.cache_clear()
        return Response(f"error: {ex}", status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@app.route("/mail/<int:id>/attachments", defaults={"attach": "0"})
@app.route("/mail/<int:id>/attachments/<string:attach>", methods=["GET"])
def fetch_attachments(id: int, attach: str):
    """получить вложения по идентификатору письма
    и идентификатору файла. Если нет идент.файла,
    то скачиваются все файлы из письма в виде архива
    """
    param, _ = __get_param(id=id, attach=attach)
    file_name = api.fetch_attachments(**param)
    if os.path.exists(file_name):
        responce = __download_file(file_name)
        __remove_files(os.path.dirname(file_name))
        return responce
    else:
        responce = Response(
            f"Файл '{os.path.basename(file_name)}' не найден.\n",
            status=status.HTTP_404_NOT_FOUND,
        )


def __get_param(id=None, attach=None):
    param = {}
    param["id"] = id
    param["attach"] = attach
    param["inn"] = request.args.get("inn")
    param["ogrn"] = request.args.get("ogrn")
    param_page = {}
    # возвращает только json
    param_page["json"] = request.args.get("json_only", "no")
    param_page["page"] = request.args.get("page", "1")
    param_page["pagesize"] = request.args.get(
        "page_size", str(app.config.PAGINATOR.PageSize)
    )
    if param_page["page"].isdigit():
        param_page["page"] = int(param_page["page"])
    else:
        param_page["page"] = 1
    if param_page["page"] < 1:
        param_page["page"] = 1

    if param_page["pagesize"].isdigit():
        param_page["pagesize"] = int(param_page["pagesize"])
    else:
        param_page["pagesize"] = int(app.config.PAGINATOR.PageSize)
    if param_page["pagesize"] < 1:
        param_page["pagesize"] = app.config.PAGINATOR.PageSize

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
    page_size = param["pagesize"]
    max_pages = (count // page_size) + (1 if count % page_size != 0 else 0)
    paginat = {}
    paginat["inn"] = param["inn"]
    paginat["ogrn"] = param["ogrn"]
    paginat["page"] = page_num
    paginat["pagesize"] = page_size
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
