# KFrame

Попытка сделать Фреймворк для удобной организации архитектуры небольших программ  

В общем виде архитектура представляет из себя один класс родителя и множество детей - плагинов или модулей  
Базовый класс для плагинов и класс родителя имеют удобный интерфейс для расширения программы собственными плагинами и управления для взаимодействия между плагинами  

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
def execute(self,query,commit=False,multi=False)  
def select_all(self,query)  
def select(self,query)  
```
Метод execute - универсальный метод обращений с БД.  
Возвращает кортеж : Флаг успеха и список кортежей (записей), если запрос подразумевает результат.  

Метод select_all - облеченная версия execute, годная лишь для чтения БД.  
Результат - список кортежей (записей).  
В случае ошибки вернет None.  

Метод select - облеченная версия execute, годная лишь для чтения БД.  
Результат - генератор, который возвращает по кортежу (по записе).  
В случае ошибки кинет исключение.  

#### Neon  
Neon - Веб-сервер 

Пользовательский интерфейс объекта этого класса:
```python
def add_site_module(self,module)  
```
Метод добавляет module в список возможных обработчиков запросов.  
Модулем может быть любой объект, класс или модуль, удовлетворяющий определенном интерфейсу.  
А именно должны быть поля:  
* Host - список или сет всех возможных вариантов http-заголовка Host, с которыми должен ассоциироваться этот модуль. (если содержит строку "any", ассоциировается со всеми)  
* Path - строка, минимально необъходимое начало url, для ассоциации модкля с запросом.  
И должны быть методы:  
* get(request) - обработчик запросов метода GET.  
* post(requests) - обработчик запросов метода POST.  
* head(requests) - обработчик запросов метода HEAD.  
* put(requests) - обработчик запросов метода PUT.  
* delete(requests) - обработчик запросов метода DELETE.  
* trace(requests) - обработчик запросов метода TRACE.  
* connect(requests) - обработчик запросов метода CONNECT.  
* options(requests) - обработчик запросов метода OPTIONS.  

Модуль выбирается, если запрос содержит заголовок Host или слово "any", имеются в поле модуля Hosts, и имеет самое длинное поле Path, среди всех модулей, у которых Path является началом запрошенной url.  
Если пришел запрос с методом, который не поддерживается модулем, клиенту ортправляется 404.  

Объект requests содержит в себе поле resp - объект класса Responce, отвечающий за ответ клиенту, который должен быть заполнен в обработчике запроса.  

#### Auth  
Auth - Для авторизации и поддержки сессий  

Этот класс отвечает за генерацию и проверку куки файла.  
И этот класс не использует базу данных.  
Логика такова, что значение куки - это зашифрованный объект, содержащий в себе идентификаторы юзера, временные метки и некоторые прочие данные.  

Класс имеет пользовательский интерфейс в виде двух методов:  
```python
def generate_cookie(self, user_id, **kwargs)  
def valid_cookie(self,cookie,ip=None)  
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
def init_stat(self,key,type,**kwargs)  
def add(self,key,value=None)  
def get(self,key)  
def export(self,extension=False)  
```

init_stat - объявляет о начале сбора статистики с ключом key и типа type  
Статистика может быть типов:  
* aver - среднее арифметическое на основе последних 500 замеров. (можно изменить передав count в kwargs)  
* collect - просто сбор  последних 500 замеров. (можно изменить передав count в kwargs)  
* set - множество. сохраняет факт вхождения элемента.  
* single - имеет единственное значение.  
* inc - счетчик. (можно изменить наш счетчика, передав increment в kwargs)
* sum - сумматор.  
Так же можно сразу инициализировать начальное значение, передав default в kwargs.  
Можно придать каждой статистике пояснение передав desc в kwargs.  

Метода add добавляет замер value в статистику c ключом key.  
Для счетчика можно не передавать значение.  

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

#### Cache  
Cache - Временное хранение данных  
Использует отдельный тред для чистки устарешей информации  

#### SSP  
SSP - Простой Протокол Безопастности  
не нужен, если не создаешь велосипед  

#### Eventer  
Eventer - Регистратор событий  
Как кэш, но один тред, и сложность и записи, и чтения - константы  

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
def marshal(data,mask=None,random=True)  
def unmarshal(data=None,fd=None,mask=None)  
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
def apply(obj,scheme)  
```  
obj - имеющийся объект, который необходимо проверить и по возможности дополнить согласно правилам  
scheme - правила, по которым проверяется объект.  
Принцип описания правил похож на JSON-scheme.  


## Простой пример:  

main.py:  
```python
#!/usr/bin/env python3
from kframe.base.parent import Parent    
from kframe.plugins.neon import Neon    
p = Parent()    
p.add_plugin(key="neon", target=Neon)    
p.init_plugin(key="neon", export=False, site_directory='.', use_neon_server=True, http_port=8080)    
p.start()  
# open http://127.0.0.1:8080
```

запуск:  
`$ ./main.py --stdout --debug`  

## Зависимости  
* pygost - Криптографическая библиотека  
* mysql-connector - драйвер MySQL  

Версия 2.2.1  
