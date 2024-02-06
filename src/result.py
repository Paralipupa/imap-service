import re
import hashlib
import json_fix
from typing import Any


class Result:
    def __init__(self, criteria: str = "", error_message: str = ""):
        patt = r"(?:(?:[0-9а-яё:\/])*\s*){0,3}"
        self.criteria = criteria
        self.compile: re.compile = re.compile(
            patt + self.criteria + patt, re.IGNORECASE
        )
        self.id: bytes = b"0"
        self.subject: str = ""
        self.body: str = error_message
        self.sender: str = ""
        self.files: list = []
        self.error: str = error_message

    @classmethod
    def hashit(cls, s):
        return hashlib.sha1(s.encode("utf-8")).hexdigest()[:8]

    def find_in_body(self):
        return self.compile.findall(self.body)

    def find(self):
        return self.compile.findall(self.subject + self.body) or any(
            self.compile.findall(x) for x in self.files
        )

    def __json__(self):
        return {
            "id": self.id.decode("utf-8"),
            "sender": self.sender,
            "subject": self.subject,
            "body": self.find_in_body()[0] if self.find_in_body() else "",
            "files": self.files,
        }
