# imap-service
Сервис получения электронных писем по протоколу IMAP<br/>

## Описание
Осуществляет поиск писем с вложениями по заданным параметрам ИНН и/или ОГРН<br/>
Выдает список писем, в которых найдены ИНН или ОГРН в заголовке или теле письма<br/>

## Установка

git clone git@gitlab.com:qqube/imap-service<br/>
cd imap-service<br/>
pipenv install --dev<br/>
pipenv shell<br/>

docker-compose -f build/docker-compose.yml up -d<br/>

## Документация

http://localhost:5000/swagger/<br/>


## Использование

В заголовочной части запросов обязательно указывать jwt token:<br/>
headers = {'Authorization': Bearer <access_token>}<br/>
Для проверки авторизации должен обязательно присутствовать один из <br/>
параметров inn или ogrn, либо оба параметра.<br/>
##
http://localhost:5000/mail<br/>

Параметры:<br/>

<lu>
<li>inn = ИНН </li>
<li>ogrn = ОГРН</li>
<li>page = номер страницы (по-умолчанию 1)</li>
<li>page_size = количество записей на одной странице (по-умолчанию 50)</li>
</ul><br/>
  

Возвращает:

Список писем в заголовке или теле которых присутствует заданные ИНН или ОГРН

##
http://localhost:5000/mail/[id]/<br/>

<b>id</b> - цифровой идентификатор письма<br/>

Параметры:<br/>

<lu>
<li>inn = ИНН </li>
<li>ogrn = ОГРН</li>
<li>page = номер страницы (по-умолчанию 1)</li>
<li>page_size = количество записей на одной странице (по-умолчанию 50)</li>
</ul><br/>

Возвращает:

Данные письма с идентификатором равным <b>id</b>
##
3. http://localhost:5000/mail/[id]/attachments/<br/>

<b>id</b> - цифровой идентификатор письма<br/>

Параметры:<br/>

<lu>
<li>inn = ИНН </li>
<li>ogrn = ОГРН</li>
</ul><br/>

Возвращает:<br/>

Файлы, прикрепленные к письму в виде zip-архива.

##

4. http://localhost:5000/mail/[id]/attachments/[id_attach]/<br/>

<b>id</b> - цифровой идентификатор письма<br/>
<b>id_attach</b> - строковый идентификатор файла в письме<br/>

Параметры:<br/>

<lu>
<li>inn = ИНН </li>
<li>ogrn = ОГРН</li>
</ul><br/>

Возвращает:<br/>

Файл, прикрепленные к письму, соответствующий идентификатору <b>id_attach</b>


##

Примеры:
1. http://localhost:5000/mail?inn=1234567890&ogrn=&page=1&page_size=50<br/>

Результат:<br/>

<pre>
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
                        "id": "20",
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
</pre>
