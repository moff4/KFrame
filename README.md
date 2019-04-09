# KFrame

Попытка сделать Фреймворк для удобной организации архитектуры небольших программ  

В общем виде архитектура представляет из себя один класс родителя и множество детей - плагинов или модулей  
Базовый класс для плагинов и класс родителя имеют удобный интерфейс для расширения программы собственными плагинами и управления для взаимодействия между плагинами.  

Прелесть такой системы в том, что все плагины имеют указатель на родителя, а тот в свою очередь имеет (при необходимости) указатели на плагины и модули  

### Плагин  
Плагин - объект класса base.Plugin или его наследника  
плагин обязан иметь конкретный интерфейс, которым будет пользоваться объект класса base.Parent или его наследника.  
Плагин имеет интерфейс доступа к другим плагнам, модулям и объекту класса base.Parent или его наследника.  

### Модуль  
Модуль - некоторый объект/класс/область видимости с собственными функция.  
Модуль не обязан иметь какой-либо интерфейс.  
Задача родиля в данном случае сводит лишь к харению и предоставлению доступа к модулю.  
Модуль все цело замкнут в себе.  

## Комплект плагинов и модулей  

### Плагины

#### SQL
SQL - Обертка над драйвером MySQL  

Констркутор принимает четыре обязательных параметра:  
* host - хост БД  
* port - порт БД  
* user - логин  
* passwd - пароль  

Так же можно передать:
* ddl - словарь, ключ - название таблицы table_name, значение DDL-скрипт  
* scheme - схема по-умолчанию    

Интерфейс класса:
```python
def execute(self, query, commit=False, multi=False)  
def select_all(self, query, unique_cursor=False)  
def select(self, query, unique_cursor=False)  
```
Метод execute - универсальный метод обращений с БД.  
Возвращает кортеж : Флаг успеха и список кортежей (записей), если запрос подразумевает результат.  

Метод select_all - облегченная версия execute, годная лишь для чтения БД.  
Результат - список кортежей (записей).  
В случае ошибки вернет None.  

Метод select - облегченная версия execute, годная лишь для чтения БД.  
Результат - генератор, который возвращает по кортежу (по записе).  
В случае ошибки кинет исключение.  

#### Neon  
Neon - Веб-сервер. Особенность такого веб-севера в том, что он запускается не в главном треде, что удобно для программы, где веб не первостепенная задача.  

Конфигурация передается веб-серверу через параметры в методе init:  
* allowed_hosts - default: {'any'}, - список разрешенных значений HTTP-заголовка Host  
* only_local_hosts - default: False, - Если True, то обрабатывает запросы только с приватных IP  
* believe_x_from_y - default: False, - Если True, то значение заголовка X-From-Y считается реальным IP клиента  
* http_port - default: 8080, - порт для HTTP трафика  
* https_port - default: 8081, - порт для HTTPS трафика  
* use_ssl - default: False, - использовать SSL  
* ca_cert - default: None, - путь к файлу с корневыми сертификатами  
* ssl_certs - default: {} - настройки ssl: ассоциативный массив, ключ - имя хоста, значение - словарь настроек  
Пример такой настройки: {  
 -- certfile - путь к серверному сертификату в кодировке PEM  
 -- keyfile - путь к закрытому ключу от сертификата  
 -- keypassword - пароль от ключа (опционально)  
}
* max_data_length - default: 4КБ, - параметр управление разрешенного объема данных в запросе  
* max_header_count - default: 32, - параметр управление разрешенного объема данных в запросе  
* max_header_length - default: 2КБ, - параметр управление разрешенного объема данных в запросе  
* site_directory - default: './var', - путь к папке с исходными файлами сайта (html/js/css)  
* threading - default: False, - обрабатывать каждый запрос в новом треде?  
* use_neon_server - default: False, - использовать встроенный обработчие запросов ? (выдача статических файлов/содержимого директории)  
* response_settings - default: {}, - настройки заголовков ответа  
 -- cache_min - default 120, - значение 'Cache-Control' в секундах  
 -- max_response_size - default 2^20, - Масимальный размер ответа на запрос (для статических файлов)  
* single_request_per_socket - default: True, - Если True, то работает принцип "одно соединение - один запрос"  
* enable_stats - default: True, - Если True, то неон будет собирать статистику  

Пользовательский интерфейс объекта этого класса:
```python
def add_site_module(self, module, path: str=None, response_type: str=None)  
def add_middleware(self, target=None, post=None)   
```
Метод add_site_module добавляет module в список возможных обработчиков запросов.  
Модуль будет ассоциироваться со всеми url, у которых начало совпадает с path (естественно из ассоциированных модулей выбирается с наибольшим path)  
Модулем может быть любой объект, класс или модуль, удовлетворяющий определенном интерфейсу.  
А именно должны быть методы:  
* get(request) - обработчик запросов метода GET.  
* post(requests) - обработчик запросов метода POST.  
* head(requests) - обработчик запросов метода HEAD.  
* put(requests) - обработчик запросов метода PUT.  
* delete(requests) - обработчик запросов метода DELETE.  
* options(requests) - обработчик запросов метода OPTIONS.  

Если пришел запрос с методом, который не поддерживается модулем, клиенту ортправляется 405.  

Объект requests содержит в себе поле resp - объект класса Responce или наследника, отвечающий за ответ клиенту, который должен быть заполнен в обработчике запроса.  
Если response_type был передан, то поле респ указывает на объект известного класса:  

| response_type | response class |  
|-----|------|  
| base | Response |  
| static | StaticResponse |  
| rest | RestResponse |  

Метод add_middleware добавляет target или post в список предобработчиков или постобработчиков соответсвенно, которые будут вызваны между парсингом данных из сокета и вызовом обработчика запроса или после вызова обработчика соответственно.  
Предобработчик - вызываемый объект (callable), которому будут переданы два параметра: запрос и обработчик запроса.  
Постобработчик - вызываемый объект (callable), которому будут переданы три параметра: запрос, ответ и обработчик запроса, сегенерировавший ответ.  
Все предобработчики будут вызваны в той же последовательности, что и были зарегестрированы.  
Все постобработчики будут вызваны в обратном порядке, что и были зарегестрированы.  


#### Auth  
Auth - Для авторизации и поддержки сессий  

Этот класс отвечает за генерацию и проверку куки файла.  
И этот класс не использует базу данных.  
Логика такова, что значение куки - это зашифрованный объект, содержащий в себе идентификаторы юзера, временные метки и некоторые прочие данные.  

Класс имеет пользовательский интерфейс в виде двух методов:  
```python
def generate_cookie(self, user_id, **kwargs)  
def valid_cookie(self, cookie, ip=None)  
```

Первый метод создает значение куки-файла ивозвращает байтовую строку.  
Помимо идентификатора юзера (целое число) могут быть переданы:  
* expires - целое число секунд сколько будет валидным этот куки с момента генерации  
* ip - (строка) ip-адрес клиента. Если передан, то при проверки будет проверяться, что клиент имеет тот же ip  

Второй метод принимает байтовую строку и опционально ip адрес клиент.  
Результатом будет либо идентификатор юзера, которую принадлежит куки, либо None, если куки невалиден.  
Если был передан ip, то будет проверятся, совпадают ли переданный ip и ip при генерации куки.  

#### Stats  
Stats - Сбор статистики  

Объект этого класса выполняет аккумулирующую функцию для данных разных типов.


Имеется пользовательский интерфейс в виде четырех методов:  
```python
def init(self, **kwargs)
def init_stat(self, key, type, **kwargs)  
def add(self, key, value=None)  
def init_and_add(self, key, type, value=None, **kwargs)
def get(self, key)  
def export(self, extension=False)  
```

init может принимать следующие параметры:
* add_neon_handler - default False - добавить в Неон ручку выдачи статистики  
* neon_handler_cfg - default {} - набор параметров для модуля расширения неона.  
Пример:  
 -- only_local_hosts - default True - выдача только на запросы с приватных IP (127.0.0.1, 192.168.*.* итд)  
 -- stat_url - default '/{parent.name}-admin/stats' - url, по которому будет выдаваться статистика  

init_stat - объявляет о начале сбора статистики с ключом key и типа type  
Статистика может быть типов:  
* aver - среднее арифметическое на основе последних 500 замеров. (можно изменить передав count в kwargs)  
* single - имеет единственное значение.  
* inc - счетчик. (можно изменить наш счетчика, передав increment в kwargs)
* sum - сумматор.  
* event - сохраняет события с их временными метками, автроматически удаляет устаревшие (поле limit)  
* event_counter - сохраняет кол-во событый произошедших в каждую секунду с их временными метками, автроматически удаляет устаревшие (поле limit)  

Так же можно сразу инициализировать начальное значение, передав default в kwargs.  
Можно придать каждой статистике пояснение передав desc в kwargs.  

Метод add добавляет замер value в статистику c ключом key.  
Для счетчика можно не передавать значение.  

Метод init_and_add работает как метод add но, если сбор ститистики с таким клюсом еще не иничиализирован, то будет вызван метод init_stat  

Метод get вернет текущие статистические данные для ключа key, либо None, если нет статистики по ключу.   
(aver посчитан не будет)

Метод export вернет dict, в котором будет вся текущая статистика.  
(aver будет посчитан)  
Если был поднят флаг extension, то значение кажой статистики будет сопровождаться пояснением переданым при регистрации статистики.  

#### Mchunk  
Mchunk - Хранение секретов  

Логика объекта такова, что он не хранит важные данные, а хранит информацию как их получить.  
А именно: имеется маска, сгенерированная случанно, и результат XOR маски и важных данных.  

Методы объекта этого класса:  
```python
def set(self,data)  
def mask(self)  
def unmask(self)  
def get(self)  
```

set задает данные, которые надо хранить, и генерирует для них маску  
mask - маскирует данные.  
unmask - получает исходные данные.  
get - возвращает данные в текущем состоянии, не меняя их.  

Методы set, mask, unmask написаны в стиле ORM - возвращают текущий объект этого класса.  
Также класс поддерживает работу с контекстным менеджером  

#### Cache  
Cache - Временное хранение данных c функцией автоматичексой очисти протухших данных  
Функция инициализации принимает параметры:
* auto_clean_in_new_thread - default: False - Если True, то создастся новый тред для проверки тухлости данных  
* timeout - default: 1.0 - интервал проверки. Игнорируется, если auto_clean_in_new_thread == False  
* save_file - default: "cache.json" - имя файла для временного сохранения данных  
* autosave - default: False - если True, автоматически сбрасывает данные в файл. Игнорируется, если auto_clean_in_new_thread == False  

#### Eventer  
Eventer - Регистратор событий  
Как кэш, но один тред, и сложность и записи, и чтения - константы  

#### Planner  
Planner - Запускает задачи по расписанию  
Список возможныех параметров плагина:  
enable_stats (bool), default =  False - флаг агрегации статистики в плагине stats  
add_neon_handler (bool), default =  False - включить поддержку REST API в Neon  
neon_handler_cfg (dict), default =  {} - параметры модуля расширения neon  
возможные параметры модуля расширения:  
-- only_local_hosts (bool), default = True - флаг доступа только с приватных адресов  
-- stat_url (str), default = '/%s-admin/planner' % parent.name - начало url, по которому модуль будет идентифицироваться  

Каждая задача определяется набором обязательных параметров:
* key (str) - уникальный ключ/имя задачи  
* target (function) - функция, которая будет запущена  
И набором второстепенных параметров:
* enable (bool), default = True - флаг участует ли задача в планировании (и соотв будет выполнена)  
* hours (int), default = 0 - интервал между запусками в часах (суммируется с значенями интервала в других единицах измерения)  
* min (int), default = 0 - интервал между запусками в минутах (суммируется с значенями интервала в других единицах измерения)  
* sec (int), default = 0 - интервал между запусками в секундах (суммируется с значенями интервала в других единицах измерения)  
* shedule - список кортежей ('HH:MM:SS', 'HH:MM:SS'), default ('00:00:00','23:59:59') - Расписание запусков (с, по)  
* calendar - { 'allowed' or 'disallowed': { month as key [1..12] => set of days [1..31] }}  
	default {} (всегда разрешено) - выделить дни, когда запускать или не запускать. Можно передать только один из двух ключей {allowed/disallowed}  
* weekdays - {0,..,6} - список номеров дней недели, когда можно запускать задачу. Понедельник = 0, Воскресенье = 6.  
* offset (int), default = 0 - начальнй отступ в секундах  
* args (list), , default = [] - параметры функции  
* kwargs (dict), default = {}  - параметры функции  
* threading (bool), default = False . если True или 'thread', запустит функцию в новом потоке, если 'process', запустит в новом процессе.  
* after (int), default = None . временная метка, раньше которой функция запущена не будет (None - без ограничения)  
* times (int), default = None . кол-во раз, которое будет запущена функция (None - без ограничения)  
* max_parallel_copies (int), default = None - максиальное кол-во одновременных исполнений задачи (None - без ограничения)  

Интерфейс плагина имеет несколько методов:
```python
def registrate(self, **task)
def update_task(self, key, **task)
def delete_task(self, key):
def get_task(self, key):
def run_task(self, key, set_after=False):
def get_running_tasks(self):
def get_shedule(self):
def get_next_task(self):
```
registrate создает задачу. Возвращает True в случае успеха;  
update_task обновляет существующую задачу или создает новую. Возвращает True в случае успеха;  
delete_task удаляет задачу, если такая имелась;  
get_task возвращает словарь, содержащий всю информацию о задаче, или None в случае неудачи;  
get_running_tasks возвращает список задач, которые данный момент исполняются, и когда они были запущены;  
get_shedule возвращает список задач, время, когда они будут запущены, и, сколько секунд осталось до запуска;  
get_next_task аналогичнен get_shedule, но возвращает информацию только о первой задачи в очереди на исполнение.  

## Модули

#### Crypto  
Crypto - Библиотека крипто алгоритмов  
Имеет в себе алгоритмы:  
* хеширования  
* генерации общего секрета  
* подписи и проверки подписи  
* шифрования  

Также имеются второстепенные функции такие, как генерации эфимерной пары ключей или генерации случайного инициализирующего вектора для шифрования.  

#### Art  
Art - Язык описания данных экономичнее JSON  

Интерфейс модуля:
```python
def marshal(data, mask=None, random=True)  
def unmarshal(data=None, fd=None, mask=None)  
```

Метод marshal - маршализирует объект в байтовую строку.  
Особенность принципа кодирования такова, что можно неоднозначно маршализировать, но обратное действие всегда будет однозначным.  
Флаг random указывает, использовать ли рандов в необднозначностях.  
Если передать байтовую строку как аргумент mask, к возвращаемому значению будет применен XOR с этой маской.  

Метод unmarshal - создание объект из байтовой строки.  
Данные можно передать как строкой, так и потоком данных (файл/сокет).  
Если передать байтовую строку как аргумент mask, к возвращаемому значению будет применен XOR с этой маской.  

#### JScheme  
JScheme - Проверка и дополнения объектов.  
Содержит всего одну функцию:  
```python  
def apply(obj, scheme)  
```  
obj - имеющийся объект, который необходимо проверить и по возможности дополнить согласно правилам  
scheme - правила, по которым проверяется объект.  
Принцип описания правил похож на JSON-scheme.  

## Простой пример:  

### веб-сервис  

main.py:  
```python
#!/usr/bin/env python3
from kframe.base.parent import Parent
from kframe.plugins.neon import Neon
Parent(name='TestApp').add_plugin(target=Neon, kwargs={
	'site_directory': '.',
	'use_neon_server': True,
	'http_port': 8080,
}).init().start()
# open http://127.0.0.1:8080
```

запуск:  
`$ ./main.py --stdout --debug`  

### крон-сервис  

main.py:  
```python
#!/usr/bin/env python3
import time
from kframe.base.parent import Parent
from kframe.plugins.planner import Planner
p = Parent(name='TestApp').add_plugin(target=Planner).init()
p.planner.registrate(key='Task-1', target=lambda: print(time.ctime()), sec=5)
p.start()  # Here program will stop and wait for end of Planner, who will work untill get SIGINT
p.stop()
```

запуск:  
`$ ./main.py --stdout --debug`  

## Установка

Установка производится через утилиту pip:  
```bash
$ pip install git+https://github.com/moff4/kframe.git  
```  
или через ручную сборку:  
```bash
$ python3 setup.py build  
$ python3 setup.py install  
```

## Зависимости  
* pygost - Криптографическая библиотека  
* mysql-connector - драйвер MySQL  
