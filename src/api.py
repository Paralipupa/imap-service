import logging
import requests
from functools import lru_cache
from .emessage_process import (
    fetch_messages as f_messages,
    fetch_message as f_message,
    fetch_attachments as f_attachments,
)

# from .emessage_thread import (
#     fetch_messages as f_messages,
#     fetch_message as f_message,
#     fetch_attachments as f_attachments,
# )
from flask_api import status
from .helpers import serialize
from .result import Result
from src import app
from .exceptions import *

logger = logging.getLogger(__name__)


@lru_cache(maxsize=32, typed=False)
def fetch_messages(**param):
    """Получить список писем по ИНН или ОГРН
    ИНН или ОГРН ищутся в теле и заголовке писем
    если задан идентификатор id возвращается письмо
    соответстующее этому идентификатору
    """
    try:
        # if not fetch_verify_auth(**param):
        #     raise AccessDeniedException
        id = param.get("id")
        if id:
            id = bytes(str(id), "utf-8")
            results = f_message(id)
        else:
            search_text = param.get("inn") if param.get("inn") else ""
            search_text += "," if param.get("inn") and param.get("ogrn") else ""
            search_text += param.get("ogrn") if param.get("ogrn") else ""
            results = f_messages(search_text)
        return results
    except ConnectionErrorException as ex:
        logger.error(f"{ex}")
    except Exception as ex:
        logger.error(f"{ex}")
    return Result(error_message="error")


def fetch_attachments(**param):
    """Получить вложения письма по идентификатору письма id
    если задан иден.файла "attach" не равный "0", то возвращается
    файл соответствующий этому идентификатору
    """
    try:
        id = param.get("id")
        if id:
            id = bytes(str(id), "utf-8")
            attachments = param.get("attach")
            if attachments:
                results = f_attachments(id, attachments)
                return results
    except ConnectionErrorException as ex:
        logger.error(f"{ex}")
    except Exception as ex:
        logger.error(f"{ex}")
    return Result(error_message="error")


def fetch_verify_auth(**param):
    if param["ogrn"]:
        url = "http://stage1.qqube.ru:7001/identity/get_token/" + param["ogrn"]
        response = requests.get(
            url, auth=(app.config.BASIC_AUTH.user, app.config.BASIC_AUTH.password)
        )
        if response.status_code == status.HTTP_200_OK:
            return True
    return False


if __name__ == "__main__":
    pass
