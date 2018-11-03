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

## Комплект плагинов  
- SQL 		- протестирован - Обертка над драйвером MySQL  
- WEB 		- протестирован - Наитупейшись веб-сервер  
- Neon 		- протестирован - Веб-сервер уровнем выше  
- Auth 		- черновик      - Для авторизации и поддержки сессий  
- Cookie 	- протестирован - Для куков. Нуждается в переработке  
- Firewall 	- протестирован - ... пора удалить  
- Stats 	- протестирован - Сбор статистики  
- Mchunk 	- протестирован - Хранение секретов  
- Crypto 	- протестирован - Библиотека крипто алгоритмов  
- Cache 	- протестирован - Временное хранение данных  
- Art 		- протестирован - Язык описания данных экономичнее JSON  
- Eventer 	- протестирован - Регистратор событий  
- JScheme	- протестирован - Проверка и дополнения объектов  

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

Версия 1.7  
