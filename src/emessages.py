import imaplib
import email
import warnings
import logging
import datetime
import re
from pathlib import Path
from email.header import decode_header
from typing import Tuple, List, Any
from bs4 import BeautifulSoup, MarkupResemblesLocatorWarning
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import lru_cache
from .settings import *
from .result import Result
from .helpers import (
    get_name_template,
    write_contents,
    make_archive,
    decode_quoted_printable,
)
from src import app
from .exceptions import *

warnings.filterwarnings("ignore", category=MarkupResemblesLocatorWarning)
logger = logging.getLogger(__name__)

connection_pool = ThreadPoolExecutor(max_workers=16)


def connect(folder: str):
    try:
        imap = imaplib.IMAP4_SSL(
            host=app.config.IMAP_SERVER.host,
            port=app.config.IMAP_SERVER.port,
            timeout=30,
        )
    except Exception as ex:
        logger.error(f"{ex}")
        raise ConnectionErrorException(ex)

    try:
        imap.login(app.config.IMAP_SERVER.user, app.config.IMAP_SERVER.password)
    except Exception as ex:
        logger.error(f"{ex}")
        raise AccessDeniedException(ex)

    status, _ = imap.select(folder)
    if status == "OK":
        return imap
    else:
        try:
            status, folders = imap.list()
            if folders:
                folders = "".join([x.decode("utf-8") for x in folders]).strip("'") + "("
                folders = ",".join(
                    re.findall(r"(?<=\s)[A-Za-zА-Яа-я-\s]{2,}(?=\()", folders)
                )
        finally:
            imap.logout()
            raise InboxIsNotSelected(f"{folder}. Список доступных папок: {folders}")


def disconnect(imap):
    try:
        imap.close()
    finally:
        imap.logout()


# Пул для повторного использования соединений IMAP
def pooled_connection(folder: str):
    return connection_pool.submit(connect, folder)


def get_message(id: bytes, folder: str):
    imap = connect(folder)
    try:
        status, data = imap.uid("fetch", id.decode(), "(RFC822)")
        if status == "OK" and len(data) > 1:
            return email.message_from_bytes(data[0][1])
        return None
    finally:
        disconnect(imap)


def search_messages(criteria, folder: str) -> Any:
    """Поиск сообщений с помощью серверных фильтров"""
    imap = connect(folder)
    date_begin = (datetime.datetime.now() - datetime.timedelta(days=365)).strftime(
        "%d-%b-%Y"
    )
    args = ["SENTSINCE", date_begin]
    criteria_list = criteria.split(",")
    if len(criteria_list) > 1:
        args.append("OR")
    for cr in criteria_list:
        args.append("TEXT")
        args.append(cr.strip())

    try:
        criteria_text = " ".join(args).encode("utf-8")
        status, data = imap.uid("search", "charset", "utf-8", criteria_text)
        if status == "OK":
            return data
        return None
    finally:
        disconnect(imap)


@lru_cache(maxsize=1024)
def get_message_data(id: bytes, folder: str, criteria: str = ""):
    """Выборка данных сообщения"""
    # Преобразование id (bytes) в строку для кеширования
    id_str = id.decode("utf-8")
    msg = get_message(id, folder)
    if msg:
        result = Result(criteria=criteria)
        result.criteria = criteria
        result.path = folder
        result.id = id
        result.sender = get_email_from_message(msg)
        result.date = get_date_from_message(msg)
        result.subject = get_subject(msg)
        result.body, result.files = get_body(msg)
        return result if result.files else None
    return None


def fetch_messages(criteria: str, folders: List[str]):
    """Поиск сообщений"""
    results = []
    error_results = []
    with ThreadPoolExecutor(max_workers=8) as executor:
        for folder in folders:
            data = search_messages(criteria, folder)
            if data:
                futures = [
                    executor.submit(get_message_data, id, folder, criteria)
                    for id in data[0].split()[:100]
                ]
                for future in futures:
                    try:
                        result = future.result()
                        if result:
                            results.append(result)
                    except Exception as ex:
                        error_results.append(Result(error_message=f"{ex}"))

    try:
        sorted_results = sorted(
            [r for r in results if r], key=lambda x: x.date, reverse=True
        )
        return sorted_results + error_results
    except Exception as ex:
        logger.error(f"{ex}")
        return []


@lru_cache(maxsize=1024)
def get_subject(msg) -> str:
    try:
        subject = decode_header(msg["Subject"])[0][0]
        return subject.decode() if isinstance(subject, bytes) else subject
    except Exception as ex:
        logger.warning(f"{ex}")
        return ""


@lru_cache(maxsize=1024)
def get_date_from_message(msg):
    return email.utils.parsedate_to_datetime(msg["Date"]) if msg else None


@lru_cache(maxsize=1024)
def get_email_from_message(msg):
    return msg["Return-path"] if msg else None


def get_body_text(part) -> str:
    encode = get_Transfer_Encoding(part)
    payload = part.get_payload()
    contents = (
        email.base64mime.decode(payload)
        if encode == "base64"
        else (
            decode_quoted_printable(payload)
            if encode == "quoted-printable"
            else payload
        )
    )
    soup = BeautifulSoup(contents, "html.parser")
    return re.sub(r"(\n)+", r"\n", soup.text)


@lru_cache(maxsize=1024)
def get_file_name(part):
    filename = decode_header(part.get_filename())[0][0]
    return filename.decode() if isinstance(filename, bytes) else filename


def get_Transfer_Encoding(part):
    encoding = part.get("Content-Transfer-Encoding", "").lower()
    return encoding


def get_body(msg) -> Tuple[str, list]:
    text = ""
    files = []
    for part in msg.walk():
        if part.get_content_disposition() == "attachment":
            filename = get_file_name(part)
            if filename:
                files.append({"id": Result.hashit(filename), "name": filename})
        elif part.get_content_maintype() == "text":
            text = get_body_text(part)
    return text, files


def extract_attachments(msg, att_ids):
    files = []
    path = Path(
        Path(__file__).resolve().parent.parent,
        get_name_template(app.config.OUTPUT_DIR),
    )
    path.mkdir(parents=True, exist_ok=True)

    for part in msg.walk():
        if part.get_content_disposition() == "attachment":
            filename = get_file_name(part)
            contents = part.get_payload(decode=True)
            if not filename in files:
                if (not att_ids or att_ids == "0") or Result.hashit(
                    filename
                ) in att_ids:
                    files.append(filename)
                    write_contents(Path(path, filename), contents)

    if files:
        return make_archive(path, files) if len(files) > 1 else Path(path, files[0])
    return None


# --------------------------------------------------------------------------


def fetch_messages(criteria: str, folders):
    results = []
    error_results = []

    with ThreadPoolExecutor(max_workers=4) as folder_executor:
        future_to_folder = {
            folder_executor.submit(process_folder, criteria, folder): folder
            for folder in folders
        }

        for future in as_completed(future_to_folder):
            try:
                folder_results, folder_errors = future.result()
                results.extend(folder_results)
                error_results.extend(folder_errors)
            except Exception as ex:
                logger.error(f"Ошибка обработки папки: {ex}")
                error_results.append(Result(error_message=f"Ошибка папки: {ex}"))

    try:
        results = sorted([x for x in results if x], key=lambda x: x.date, reverse=True)
        return results + error_results
    except Exception as ex:
        logger.error(f"{ex}")
        return error_results


def process_folder(criteria: str, folder: str):
    """Обработка одной папки и возврат результатов и ошибок"""
    folder_results = []
    folder_errors = []
    data = search_messages(criteria, folder)
    if data:
        with ThreadPoolExecutor(max_workers=8) as message_executor:
            future_to_message = {
                message_executor.submit(get_message_data, id, folder, criteria): id
                for id in data[0].split()[:100]  # Ограничим до 200 первых сообщений
            }

            for future in as_completed(future_to_message):
                try:
                    result = future.result()
                    if result:
                        folder_results.append(result)
                except Exception as ex:
                    folder_errors.append(Result(error_message=f"{ex}"))

    return folder_results, folder_errors


def fetch_message(id: bytes, folders: set):
    """Выборка сообщения по идентификатору"""
    results = []

    with ThreadPoolExecutor(max_workers=4) as folder_executor:
        futures = [
            folder_executor.submit(get_message_data, id, folder) for folder in folders
        ]

        for future in as_completed(futures):
            result = future.result()
            if result:
                results.append(result)

    return results


def fetch_attachments(id: str, folders: set, att_id: str = ""):
    """Получить вложение письма"""
    with ThreadPoolExecutor(max_workers=4) as folder_executor:
        futures = [
            folder_executor.submit(get_message, id, folder) for folder in folders
        ]

        for future in as_completed(futures):
            msg = future.result()
            if msg:
                return extract_attachments(msg, att_id)

    return None


if __name__ == "__main__":
    pass
