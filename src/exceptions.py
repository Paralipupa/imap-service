
class NotFoundException(Exception):
    def __init__(self, name):
        self._message = "Справочник не найден ".format(name)
        super(NotFoundException, self).__init__(self._message)

class AccessDeniedException(Exception):
    def __init__(self):
        self._message = "Доступ запрещен"
        super(AccessDeniedException, self).__init__(self._message)

class DataIsNotDefined(Exception):
    def __init__(self):
        self._message = "Данные не определены"
        super(DataIsNotDefined, self).__init__(self._message)

class ConnectionErrorException(Exception):
    def __init__(self, name:str=""):
        self._message = "Ошибка соединения с сервером {}".format(name)
        super(ConnectionErrorException, self).__init__(self._message)
