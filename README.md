# imap-service
Сервис получения электронных писем по протоколу IMAP

## Description
Осуществляет поиск писем с вложениями по заданным параметрам ИНН и/или ОГРН
Выдает список писем, в которых найдены ИНН или ОГРН в заголовке или теле письма

## Installation

git clone git@gitlab.com:qqube/imap-service
cd imap-service
pipenv install --dev
pipenv shell

docker-compose -f build/docker-compose.yml up -d
## Usage

http://localhost:5000/swagger/

В заголовочной части запроса обязательно указывать jwt token:
headers = {'Authorization': Bearer <access_token>}

параметры page (по умолчанию=1) и page_size(50) не обязательны

Для проверки авторизации должен обязательно присутствовать один из 
параметров inn или ogrn, либо оба параметра.

1. http://localhost:5000/mail?inn=1234567890&ogrn=&page=1&page_size=50
Result:
{
    "count": 1,
    "current": "http://localhost:5000/mail?inn=1234567890",
    "inn": "1234567890",
    "next": "",
    "ogrn": null,
    "page": 1,
    "page_size": 50,
    "previous": "",
    "results": [
                    {
                        "body": "",
                        "date": "Sat, 10 Feb 2024 12:04:18 GMT",
                        "files": [
                            {
                                "id": "8dfa0771",
                                "name": "1234567890_022024_1.zip"
                            },
                            {
                                "id": "89sa82s0",
                                "name": "1234567890_022024_2.zip"
                            }
                        ],
                        "id": "19",
                        "sender": "1234567890@mail.ru",
                        "subject": "Fwd: ИНН 1234567890"
                    },
                    ....
                ]
}

2. http://localhost:5000/mail/19/?inn=1234567890&ogrn=&page=1&page_size=50
Result:
    Возвращает  в блоке 'results' письмо с идентификаторм 19

3. http://localhost:5000/mail/19/attachments/?inn=1234567890&ogrn=
Result:
    Возвращает архив с вложенными файла из письма с идент.=19

4. http://localhost:5000/mail/19/attachments/8dfa0771/?inn=1234567890&ogrn=
Result:
    Возвращает файл с идентификатором=8dfa0771 из письма с идент.=19

## Support

## Roadmap

## Contributing


## Authors and acknowledgment

## License

## Project status
