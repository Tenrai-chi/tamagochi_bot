# Tamagochi
Этот проект представляет собой Telegram бота Тамагочи, который позволяет пользователям создавать и заботиться о своих виртуальных питомцах. Пользователи могут взаимодействовать с ботом, ухаживать за питомцем, кормить его, играть с ним и следить за его состоянием. Бот предоставляет увлекательный и интерактивный опыт, напоминая о классических играх Тамагочи.

## **Функционал**
Телеграм бот позволяет создать и взаимодействовать с интерактивным зверьком. За питомцем нужно ухаживать и играт с ним. В зависимости от действий пользователя состояние питомца может изменяться. Так же характеристики питомца не связанны только с действиями пользователя. Со временем характеристики падают, поэтому пользователю нужно своевременно кормить, играть, чистить, радовать, лечить и отправлять спать своего питомца, иначе он может заболеть. 

## **Команды бота**
Для взаимодействия с ботом используются следующие команды:
- **start**: приветствие питомца или предложение создать питомца, если у пользователя его нет
- **create**: запустить процесс создания питомца. Можно выбрать типа питомца из предложенных и выбрать ему имя
- **rename**: переименовать питомца
- **check**: проверить текущее состояние питомца
- **play**: поиграть с питомцем в прятки (в процессе разработки)
- **grooming**: поухаживать за питомцем, чтобы он был чистым и опрятным
- **therapy**: вылечить питомца, если он заболел или его здоровье понизилось
- **sleep**: отправить питомца спать, чтобы восстановить энергию, питомец становится недоступным для взаимодействия на 4 часа
- **XXX**: команда для создания и заполнения базы данных необходимыми данными при развертывании (в процессе разработки)

## **База данных**
Для хранения данных используется PostgreSQL. Для взаиодействия с базой данных используется SQLAlchemy+asyncpg. 
Таблицы type_tamagochi, type_food, food, reaction, hiding_place заполняются данными из json в методе *initialize_database* + создаются необходиые триггеры

 **Таблицы**:
* **user.** Данные о пользователях
  |  id  | user_telegram_id | username |  last_request  |
  |------|------------------|----------|----------------|
  | auto |        int       | str(255) |     datetime   |
  
* **type_tamagochi.** Доступные типы питомцев pet_types.json
  |  id  |   name  | health_max | happiness_max | grooming_max | energy_max | hunger_max | image_url |
  |------|---------|------------|---------------|--------------|------------|------------|-----------|
  | auto | str(30) |    int     |      int      |       int    |      int   |      int   |  str(500) |

* **user_tamagochi.** Питомца пользователей
  |  id  |   name  |      type_id      | health | happiness | grooming | energy | hunger |  sick |  sleep | time_sleep |
  |------|---------|-------------------|--------|-----------|----------|--------|--------|-------|--------|------------|
  | auto | str(50) | type_tamagochi.id |   int  |     int   |    int   |   int  |   int  |  bool |  bool  |  datetime  |
  
* **type_food.** Типы еды. В зависимости от типа увеличивает и умеьшает различные характеристики type_food.json
  |  id  |    name | up_state_name | up_state_point | down_state_name | down_state_point |
  |------|---------|---------------|----------------|-----------------|------------------|
  | auto | str(70) |     str(20)   |       int      |       str(20)   |       int        |

* **food.** Доступные типы питомцев foods.json
  |  id  |   name  |    type_id   |
  |------|---------|--------------|
  | auto | str(70) | type_food.id |

* **reaction.** Реакция питомца на различные действия пользователя pet_reaction.json
  |  id  |  action  | reaction |
  |------|----------|----------|
  | auto | str(100) | str(300) |

* **hiding_place.** Места для пряток во время игры с питомцем и реакция на его нахождение places.json
  |  id  |  place  | reaction |
  |------|---------|----------|
  | auto | str(100)| str(300) |

## **Установка и запуск**
### **Запуск без Docker**
Для запуска бота на своем устройстве необходимо:
1. Склонируйте репозиторий
2. Установите необходимые библиотеки из reqirements.txt в проект
```bash
pip install -r reqirements.txt
```
3. Создайте пользователя и базу данных в postgresql, дайте необходимые права на созданную бд 
4. Создайте файл .env в корнейвой директории проекта и заполните его необходимыми данными:
   - **bot_token** - токен вашего бота, 
   - **db_host** - адрес, на котором находится ваша бд
   - **db_name** - имя базы данных
   - **db_user** - имя пользователя, который будет подключаться к бд
   - **db_password** - пароль пользователя
6. Запустите проект с помощью файла main.py или bot.py
7. После запуска бота и и вывода в консоль логов о запуске, отправьте боту команду /XLir3HJkIDRsFyM, это создаст все таблицы и заполнит их необходимыми данными
8. Если в консоль вывелось сообщение о том, что таблицы и триггеры созданы, то ваш бот готов к работе

## **План дальнейшей разработки:**
- [ ] Использование Docker для развертывания
- [ ] Уменьшение характеристик питомца со временем с использованием Celery и RabbitMQ
- [ ] Игра в прятки с питомцем
- [X] Лечение питомца
- [X] Груминг питомца
- [X] Отправка питомца спать, чтобы на некоторое время, пока восстанавливается энергия, питомец был недоступен для взаимодействия
- [ ] Запрет на некоторые взаимодействия при низком уровне определенных характериктик
- [X] Добавление возможности автоматического создания и заполнени базы данных
- [ ] Отправка сообщений питомцами своим хозяевам при долгой неактивности или понижения важных характеристик (здоровье, настроение)
- [ ] Добавление описания запуска и настройки проекта в readme с использованием Docker
- [X] Добавление описания запуска и настройки проекта в readme без использования Docker
- [ ] Покрыть код тестами

## **Используемые инструменты:**
* Python 3.9
* python-telegram-bot
* PostgreSQL
* SQLAlchemy
* asyncpg
* asyncio
* json
* pytz

