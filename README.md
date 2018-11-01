# KFrame

Попытка сделать Фреймворк для удобной организации архитектуры больших программ  

В общем виде архитектура представляет из себя один класс родителя и множество детей - плагинов или модулей  
Базовый класс для плагинов и класс родителя имеют удобный интерфейс для расширения программы собственными плагинами и управления для взаимодействия между плагинами  

Подразумевается:
- Плагин - объект класса base.Plugin или его наследница  
	плагин обязан иметь конкретный интерфейс, которым будет пользоваться объект класса base.Parent или его наследника.  
- Модуль - некоторый объект/класс/область видимости с собственными функция  
	модуль не обязан иметь какой-либо интерфейс. Задача родиля в данном случае сводит лишь к харению и предоставлению доступа к модулю  

Модуль все цело замкнут в себе.  
Плагин имеет интерфейс доступа к другим плагнам, модулям и объекту класса base.Parent или его наследника.  

Комплект плагинов:  
- SQL 		- протестирован  
- WEB 		- протестирован  
- Neon 		- протестирован  
- Cookie 	- протестирован  
- Firewall 	- протестирован  
- Stats 	- протестирован  
- Mchunk 	- протестирован  
- Crypto 	- протестирован  
- Cache 	- протестирован  
- Eventer 	- протестирован  

Простой пример:  

```python
from kframe.base.parent import Parent    
from kframe.plugins.neon import Neon    
p = Parent()    
p.add_plugin(key="neon", target=Neon)    
p.init_plugins(site_directory='.',use_neon_server=True)    
p.start()  
```
Версия 1.6   
