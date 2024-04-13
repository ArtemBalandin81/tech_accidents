# Tech_accidents

<details>
  <summary>Оглавление</summary>
  <ol>
    <li>
      <a href="#описание">Описание</a>
      <ul>
        <li><a href="#функционал">Функционал</a></li>
        <li><a href="#технологии">Технологии</a></li>
      </ul>
    </li>
    <li>
    <a href="#запуск-приложения-локально">Запуск приложения локально</a>
    <ul>
      <li><a href="#заполнить-env">Создать и заполнить файл .env</a></li>
      <li><a href="#развернуть-контейнеры">Развернуть контейнеры</a></li>
      <li><a href="#работа-в-сети">Работа в локальной сети</a></li>
    </ul>
    </li>
    <li>
      <a href="#для-разработки">Для разработки</a>
      <ul>
        <li><a href="#установка-и-настройка-приложения">Установка и настройка приложения</a></li>
        <li><a href="#запуск">ЗАПУСК</a></li>
        <li><a href="#работа-с-poetry">Работа с Poetry</a></li>
      </ul>
    </li>
    <li><a href="#использование">Использование</a></li>
    <li>
      <a href="#примеры-запросов-api">Примеры запросов api</a>
      <ul>
        <li><a href="#регистрация">Регистрация</a></li>
        <li><a href="#авторизация">Авторизация</a></li>
        <li><a href="#смена-пароля">Смена пароля</a></li>
        <li><a href="#фиксация-простоя">Фиксация простоя</a></li>
        <li><a href="#редактирование-простоя">Редактирование простоя</a></li>
        <li><a href="#мои-случаи-простоев">Мои случаи простоев</a></li>
        <li><a href="#аналитика-простоев">Аналитика простоев</a></li>
        <li><a href="#постановка-задачи">Постановка задачи</a></li>
        <li><a href="#редактирование-задачи">Редактирование задачи</a></li>
        <li><a href="#выданные-задачи">Выданные задачи</a></li>
        <li><a href="#полученные-задачи">Полученные задачи</a></li>
      </ul>
    </li>
   <li><a href="#разработчики">Разработчики</a></li>
  </ol>
</details>

## Описание

Веб-приложение для учета и фиксации простоев в бизнес-процессах в управляющей
компании инвестиционных фондов, включая менеджер задач, а также  модуль учета
и управления рисками.

Приложение позволяет фиксировать сбои в бизнес-процессах УК ПИФ, в соответствии
с требованиями Положения Банка России от 15.11.2021 N 779-П "Об установлении 
обязательных для некредитных финансовых организаций требований к операционной 
надежности ..., в целях обеспечения непрерывности оказания финансовых услуг".

Приложение в автоматическом режиме фиксирует отсутствие доступа в интернет,
позволяет пользователям вносить случаи простоя, изменять их, получать аналитику 
за выбранный период времени.

Пользователи также могут ставить задачи другим пользователям, изменять и дополнять
их по мере реализации.

### Функционал

#### Модуль фиксации случаев простоя:
- Автоматическая фиксация и запись в базу данных случаев простоя при отсутствии доступа в интернет;
- Авторизация и разграничение прав доступа пользователей;
- Возможность добавления случаев простоя и их редактирование пользователями;
- Получение аналитики по простоям за период: количество, сумма, максимальный простой и т.п;
- Юзер-френдли интерфейс работы приложения с использованием форм ввода данных;
- Соответствие требованиям N 779-П по защите и разграничению прав доступа;
- Доступ только из локальной сети Организации и отсутствие доступа из вне;
- Автоматический бэкап базы данных.

#### Модуль постановки и управления задач:
-	Пользователи могут ставить друг другу задачи и сроки их реализации;
-	Контроль сроков реализации задач и дедлайнов;
-	Централизованное хранение задач в базе данных;
-	Получение аналитики по выставленным и полученным задачам по каждому пользователю.

### Технологии

[![Python][Python-badge]][Python-url]
[![FastAPI][FastAPI-badge]][FastAPI-url]
[![SQLite][SQLite-badge]][SQLite-url]
[![Docker][Docker-badge]][Docker-url]


<summary><h2>Запуск приложения локально</h2></summary>
Запуск приложения локально в доккер-контейнере.

<details>
<summary><h3>Создать и заполнить файл .env</h3></summary>

1. Создать и заполнить файл `.env`:

   ```dotenv
   # Переменные приложения
   SLEEP_TEST_CONNECTION=20  # Интервал доступа к Интернет (сек.)
   SECRET_KEY=  # Cекретный ключ для генерации jwt-токенов

   # Переменные базы данных
   MAX_DB_BACKUP_FILES=50  # Максимальное количество файлов бэкапа БД
   SLEEP_DB_BACKUP=43200  # Интервал архивирования БД в сек (12 ч.)
   DATABASE_NAME=tech_accident_db_local.db  # Имя БД
   
   # Настройки логирования
   LOG_LEVEL=INFO  # Уровень логирования
   LOG_DIR=logs  # Директория для сохранения логов. По умолчанию - logs в корневой директории
   LOG_FILE=app.log  # Название файла с логами
   LOG_FILE_SIZE=10485760  # Максимальный размер файла с логами, в байтах
   LOG_FILES_TO_KEEP=5  # Количество сохраняемых файлов с логами

   # Настройки используемых тех.процессов
   TECH_PROCESS={"DU_25": "25", "SPEC_DEP_26": "26", "CLIENTS_27": "27"}
   
   # Настройки угроз
   RISK_SOURCE="{\"ROUTER\": \"Риск инцидент: сбой в работе рутера.\",
   \"EQUIPMENT\": \"Риск инцидент: отказ оборудования.\",
   \"BROKER\": \"Риск инцидент: на стороне брокер.\",
   \"PO\": \"Риск инцидент: ПО.\",
   \"PROVAIDER\": \"Риск инцидент: сбой на стороне провайдер.\",
   \"ANOTHER\": \"Иное\"}"
   
   # Настройки персонала для постановки задач 
   # (вставить строку из эндпоинта /api/users и разбить по указанному примеру)
   STAFF="{\"1\": \"user@example.com\", \"2\": \"auto@example.com\",
    \"3\": \"true2@example.com\", \"4\": \"user5@example.com\",
     \"5\": \"test_user_ex@example.com\", \"6\": \"user54378@example.com\"}"
    ```

   > **Note**
   > [Полный пример переменных окружения](env.example).

   > **Note**
   > Для наполнения переменной `STAFF` в файле `.env` списком `e-mail` пользователей необходимо:
   > - выбрать эндпоинт [GET/api/users](http://localhost:8001/docs#/users/get_all_active_api_users_get)
   > под правами админа
   > ![Изображение](media/get_api_users.png)
   > - Скопировать строковое представление пользователей и вставить его в переменную `STAFF` в файле `.env`:
   > >`STAFF="{\"1\": \"user@example.com\", \"2\": \"auto@example.com\", \"3\": \"true2@example.com\"}"` 

<summary><h3>Развернуть контейнеры</h3></summary>

2. Перед запуском контейнеров убедиться, что в проекте `"рабочие миграции"`:
   > **Note**
   > 
   > - Если возникает ошибка миграций, необходимо удостовериться, что директория с миграциями пуста!!!;
   >   `C:\...\tech_accidents\src\core\db\migrations\versions` 
   > - Если миграции в ней есть - очистить директорию от миграций.
   > - Если миграций нет, необходимо запустить `автогенерацию миграций`:
   >  `alembic revision --autogenerate -m "first_migration"`

3. При наличии "рабочих миграций" - можно собрать и запустить контейнеры из файла `infra/docker-compose.local.yml`. 
Эта команда создаст и запустит контейнер бэкэнда.
   > **Note**
   > 
   > Перед запуском контейнеров необходимо убедиться, что нет ранее запущенного контейнера
   > `tech_accidents_backend`. 
   > 
   > Если же он имеется - необходимо перед запуском сборки контейнера
   > удалить прежний контейнер `tech_accidents_backend` и его образ!

    ```shell
    docker compose -f infra/docker-compose.local.yml up
    ```
   > **Note**
   > 
   > После успешного запуска контейнера, можно проверить работу приложения на тестовом эндпоинте:
   > 1. Выбрать тестовый эндпоинт проверки доступа к сети интернет: 
   [GET/api/test_get_url](http://localhost:8001/docs#/services/test_get_url_api_test_get_url_get)
   > ![Изображение](media/test_get_url.png)
   > 2. Нажать кнопку `Try it out`.
   > 3. Нажать кнопку `Execute`.
   > 4. Убедиться, что получен ответ `200` в теле ответа `Response body`.

4. После успешного запуска контейнеров, выполните следующую команду, которая войдет в контейнер и выполнит миграции:
   > **Note**
   > 
   > Перед выполнением следующей команды необходимо убедиться, что контейнер запущен.
   > Остановить работу контейнеров в терминале можно сочетанием клавиш `CTRL + C`
   > Команду необходимо выполнять либо в новом терминале, либо запускать контейнер в "десктопной версии" Доккер.
   
    ```shell
    docker exec -it tech_accidents_backend sh -c "alembic upgrade head"
    ```
5. <a href="#запуск">ЗАПУСК</a></li>


</details>


## Для разработки

  Запуск приложения в режиме для разработки.

<details>
  <summary><h3>Установка и настройка приложения</h3></summary>

  1. Клонировать репозиторий.

        ```shell    
        git clone git@github.com:ArtemBalandin81/tech_accidents.git
        cd tech_accidents

  2. Установить зависимости и активировать виртуальное окружение.

        ```shell
        poetry env use python3.11
        poetry shell
        poetry install     

  3. или указать путь до требуемой версии Python311, например:

        ```shell
        poetry env use /C/Users/79129/AppData/Local/Programs/Python/Python311/python.exe     
        poetry shell
        poetry install

  > **Note**
  > 
  > [Документация по установке Poetry](https://python-poetry.org/docs/#installation)

  > **Note**
  > 
  > You can get the path to your Python version by running
  > - `which python3.11` on Linux 
  > - or `py -0p` on Windows.
  
> **Note**
  > 
  > Посмотреть установленные зависимости: `poetry show` 

  4. <a href="#заполнить-env">Создать и заполнить файл .env</a>

  > **Note**
  > [Полный пример переменных окружения](env.example).
</details>



<details>
  <summary><h3>ЗАПУСК</h3></summary>

  > **Note**
  > 
  > - Удостовериться, что директория с миграциями пуста!!!;
  >   `C:\...\tech_accidents\src\core\db\migrations\versions` 
  > - Если миграции в ней есть - очистить директорию от миграций.

  1. Применить миграции базы данных.

      ```shell
      alembic revision --autogenerate -m "first_migration"
      alembic upgrade head

  2. Запустить сервер приложения.

      ```shell
      uvicorn src:app --port 8001 --reload
   
  3. Зарегистрировать первого пользователя, например:
      ```shell
      email: user@example.com
      password: string_string

  > **Note**
  > 
  > 1. Выбрать эндпоинт регистрации: 
  [POST/api/auth/register](http://localhost:8001/docs#/users/users_patch_current_user_api_users_me_patch)
  ![Изображение](media/registration.jpg)
  > 2. Нажать кнопку `Try it out`.
  > 3. Заполнить `"email"` и `"password"`.
  > 4. Нажать кнопку `Execute`.
  > 5. Удостовериться что получен ответ 200: `"Успешная регистрация"`.

  4. Создать `пользователя-бота` с `id=2` в БД для автоматической фиксации простоев:

      ```shell
      - email: auto@example.com
      - password: string_string
      - id=2
  > **Note**
  > 
  > При отсутствии пользователя-бота `auto@example.com` с `id=2` в БД 
  > возможны ошибки в работе приложения при автоматической фиксации простоев!!!

  5. Удостовериться, что зарегистрированные пользователи появились в БД (например с помощью `dbeaver`).

  ![Изображение](media/registered_users.png)

  6. Установить права администратора одному из пользователей в столбце таблицы `is_superuser`
  и применить изменения, нажав кнопку `обновить` в `dbeaver`.

  7. Далее можно работать с приложением, изучив примеры: <a href="#использование">Использование</a>

</details>



<details>
   <summary><h3>Работа с Poetry</h3></summary>
   В этом разделе представлены наиболее часто используемые команды.

   Подробнее: https://python-poetry.org/docs/cli/

   ### Настройка окружения проекта
   Установку необходимо выполнять через curl, как в документации.

    ```shell
    poetry env use python3.11; poetry install
    ```

   1. Активировать виртуальное окружение

       ```shell
       poetry shell
       ```

   2. Добавить зависимость

       ```shell
       poetry add <package_name>
       ```

       > **Note**
      > Использование флага `--dev (-D)` позволяет установить зависимость,
      > необходимую только для разработки.
      > Это полезно для разделения develop и prod зависимостей.

   #### Запустить скрипт без активации виртуального окружения

   ```shell
   poetry run <script_name>.py
   ```
</details>


## Использование

После выполнения инструкций, описанных в разделе [Для разработки](#для-разработки),
будет запущен FastAPI-сервер по адресу: http://localhost:8001.

Полная документация API: http://localhost:8001/docs#.

## Примеры запросов api

Данный раздел содержит примеры использования Приложения.
Настоятельно рекомендуем каждому прочитать его хотя бы один раз.
> **Note**
  > 
  > [tech_accidents_readme.docx](tech_accidents_readme.docx).


<details>
  <summary><h3>Регистрация</h3></summary>

  1. Выбрать эндпоинт регистрации: 
  [POST/api/auth/register](http://localhost:8001/docs#/users/users_patch_current_user_api_users_me_patch)
  ![Изображение](media/registration.jpg)
  2. Нажать кнопку `Try it out`.
  3. Заполнить `"email"` и `"password"`.
  4. Нажать кнопку `Execute`.
  5. Удостовериться что получен ответ 200: `"Успешная регистрация"`.
</details>


<details>
  <summary><h3>Авторизация</h3></summary>

  1. Войти на главную страницу, или выбрать любой эндпоинт с авторизацией: 
   <a href="#">http://localhost:8001/docs#</a>
   ![Изображение](media/autorization.png)
  2. Нажать кнопку `Autorize` или `замочек` авторизации справа.
  3. Ввести `username` и `password`.

> **Note**
   > 
   > Правами на изменение пароля обладают пользователь в эндпоинте:
   > [PATCH/api/users/me](http://localhost:8001/docs#/users/users_patch_current_user_api_users_me_patch)
   > а также администратор:
   > [PATCH/api/users/{id}](http://localhost:8001/docs#/users/users_patch_current_user_api_users_me_patch)

  4. Удостовериться, что получено подтверждение авторизации
  ![Изображение](media/autorization_ok.png)
</details>


<details>
  <summary><h3>Смена пароля</h3></summary>

  1. Выбрать эндпоинт редактирования текущего пользователя:
   [PATCH/api/users/me](http://localhost:8001/docs#/users/users_patch_current_user_api_users_me_patch)  
   ![Изображение](media/change_password.png)
  2. Нажать кнопку `Try it out`.
  3. Заполнить `"email"` и `"password"`.
  4. Нажать кнопку `Execute`.
  5. Удостовериться что получен ответ `200`.

> **Note**
   >
   > Изменить пароль также может пользователь с правами администратора в эндпоинте:
   > [PATCH/api/users/{id}](http://localhost:8001/docs#/users/users_patch_current_user_api_users_me_patch) 

> **Note**
   >
   > Пароли хранятся в БД в хешированном виде и не доступны для считывания
</details>


<details>
  <summary><h3>Фиксация простоя</h3></summary>

> **Note**
  >
  > Приложение с заданным интервалом в секундах (SLEEP_TEST_CONNECTION) автоматически проверяет
  > наличие доступа к двум адресам в сети интернет и при отсутствии доступа к обоим адресам -
  > заносит простой в БД:


  Зарегистрированный пользователь может занести случай простоя в БД

  1. Пройти авторизацию.
  2. Выбрать эндпоинт создания простоя:   
   [POST/api/suspensions/form](http://localhost:8001/docs#/Suspensions%20POST/create_new_suspension_by_form_api_suspensions_form_post)  
  3. Нажать кнопку `Try it out`.
  4. Заполнить поля формы:
   ![Изображение](media/suspensions_post.png)

   > **Note**
   > 
   > Для изменения источника угроз в форме выбора необходимо:
   > - изменить переменную `RISK_SOURCE` в файле `.env` списком требуемых названий угроз вида:
   > > `RISK_SOURCE="{\"ROUTER\": \"Риск инцидент: сбой в работе рутера.\", \"ANOTHER\": \"Иное\"}"`

   > **Note**
   > 
   > Для изменения тех-процессов в в форме выбора необходимо:
   > - изменить переменную `TECH_PROCESS` в файле `.env` списком требуемых названий техпроцессов вида:
   > > `TECH_PROCESS={"DU_25": "25", "SPEC_DEP_26": "26", "CLIENTS_27": "27"}`   

  5. Нажать кнопку `Execute`.
  6. Удостовериться, что случай простоя записался в БД `получен ответ 200`:
   ![Изображение](media/suspensions_post_200.png)
  > **Note**
  >
  > - Ответ содержит описание нового случая простоя в формате `json`.
  > - Имеется возможность скопировать данные в буфер обмана, 
  или экспортировать в `файл json`, (открывается любым текстовым редактором).
</details>


<details>
  <summary><h3>Редактирование простоя</h3></summary>
  Зарегистрированный пользователь - как автор простоя - может его редактировать.

> **Note**
  >
  > - Редактирвоание простоя также доступно админу.
  > - Созданный автоматически простой может редактировать только админ.
  > - *** Редактирование простоя через поля формы в разработке.

  1. Пройти авторизацию.
  2. Выбрать эндпоинт редактирования простоя: 
  [PATCH/api/suspensions/{suspension_id}](http://localhost:8001/docs#/Suspensions%20POST/partially_update_suspension_api_suspensions__suspension_id__patch)
  3. Нажать кнопку `Try it out`.
  4. Ввести уникальный номер простоя в БД, который необходимо отредактировать 
  (доступ лишь у автора простоя и админа).
  5. Заполнить json, или поля формы*** (доступ лишь у автора и админа):
   ![Изображение](media/suspension_patch.png)
  6. Нажать кнопку `Execute`.
</details>


<details>
  <summary><h3>Мои случаи простоев</h3></summary>
  Получение случаев простоя, зафиксированных пользователем:

  1. Пройти авторизацию.
  2. Выбрать эндпоинт простоев текущего пользователя: 
    [GET/api/suspensions/my_suspensions](http://localhost:8001/docs#/Suspensions%20GET/get_my_suspensions_api_suspensions_my_suspensions_get)
    ![Изображение](media/get_my_suspensions.png)
  3. Нажать кнопку `Try it out`.
  4. Нажать кнопку `Execute`.
  5. Удостовериться, что получен список простоев:
    ![Изображение](media/get_my_suspensions_200.png)
  > **Note**
  >
  > - Ответ содержит список простоев текущего пользователя в формате `json`, отсортированный по дате добавления.
  > - Позволяет получить все зафиксированные текущим пользователем простои и их `id`.
  > - Имеется возможность скопировать список в буфер обмана, 
  или экспортировать в `файл json`, (открывается любым текстовым редактором).
</details>


<details>
  <summary><h3>Аналитика простоев</h3></summary>

  Анализ простоев за период по всем, или одному из пользователей:

  1. Авторизация не требуется.
  2. Выбрать эндпоинт аналитики простоев: 
    [GET/api/suspensions/analytics](http://localhost:8001/docs#/Suspensions%20ANALYTICS/get_all_for_period_time_api_suspensions_analytics_get)
    ![Изображение](media/get_analytics_suspensions.png)
  3. Нажать кнопку `Try it out`.
  4. Задать период по предложенному шаблону ввода данных.
  5. Если оставить поле `«id пользователя»` пустым, будет получена аналитика по всем пользователям
  за выбранный период (или по конкретному пользователю, если указать «id»).
  6. Нажать кнопку `Execute`.
  7. В ответе содержится:
     - Итого минут простоев в периоде;
     - Итого количество простоев за период;
     - Самый длинный простой в периоде;
     - Дата и время последнего по времени простоя;
     - Список простоев за выбранный период:
    ![Изображение](media/get_analytics_suspensions_200.png)
  > **Note**
  >
  > - Ответ содержит аналитику и список простоев текущего пользователя (или всех) в формате `json`,
  > отсортированный по дате добавления.
  > - Позволяет получить все зафиксированные текущим пользователем простои и их `id`.
  > - Имеется возможность скопировать список в буфер обмана, 
  или экспортировать в `файл json`, (открывается любым текстовым редактором).

  > **Note**
  > 
  > Для получения списка `id` и `e-mail` всех пользователей необходимо:
  > - выбрать эндпоинт [GET/api/users](http://localhost:8001/docs#/users/get_all_active_api_users_get)
  > под правами админа
  > ![Изображение](media/get_api_users.png)
  > - Нажать кнопку `Try it out`.
  > - Нажать кнопку `Execute` и посмотреть список пользователей вида:
  > `"{\"1\": \"user@example.com\", \"2\": \"auto@example.com\", \"3\": \"true2@example.com\"}"` в ответе эндпоинта.

</details>



<details>
  <summary><h3>Постановка задачи</h3></summary>
  Постановка задачи пользователем (заказчиком задачи) исполнителю.

  1. Пройти авторизацию.
  2. Выбрать эндпоинт постановки задач: 
    [POST/api/tasks/form](http://localhost:8001/docs#/Tasks%20POST/create_new_task_by_form_api_tasks_form_post)
  3. Нажать кнопку `Try it out`.
  4. Заполнить поля формы:
    ![Изображение](media/tasks_post.png)

  > **Note**
  > 
  > Для наполнения переменной `STAFF` в файле `.env` списком `e-mail` пользователей необходимо:
  > - выбрать эндпоинт [GET/api/users](http://localhost:8001/docs#/users/get_all_active_api_users_get)
  > под правами админа
  > ![Изображение](media/get_api_users.png)
  > - Скопировать строковое представление пользователей и вставить его в переменную `STAFF` в файле `.env`:
  > >`STAFF="{\"1\": \"user@example.com\", \"2\": \"auto@example.com\", \"3\": \"true2@example.com\"}"` 

  > **Note**
  > 
  > Если новый исполнитель зарегистрировался в БД, но его еще нет в полях выбора формы 
  > можно задать его `e-mail` в поле `Почта исполнителя не из списка`

  > **Note**
  > 
  > Для изменения тех-процессов в форме выбора необходимо:
  > - изменить переменную `TECH_PROCESS` в файле `.env` списком требуемых названий техпроцессов вида:
  > > `TECH_PROCESS={"DU_25": "25", "SPEC_DEP_26": "26", "CLIENTS_27": "27"}`
   
  7. Нажать кнопку `Execute`.
  8. Удостовериться, что задача была записана в БД `получен ответ 200`!
  > **Note**
  >
  > - Ответ содержит описание новой задачи в формате `json`.
  > - Имеется возможность скопировать данные в буфер обмана, 
  или экспортировать в `файл json`, (открывается любым текстовым редактором).
</details>


<details>
  <summary><h3>Редактирование задачи</h3></summary>
  Редактирование задачи пользователем (заказчиком задачи), или админом.

  1. Пройти авторизацию.
  2. Выбрать эндпоинт редактирования задачи: 
    [PATCH/api/tasks/{task_id}](http://localhost:8001/docs#/Tasks%20POST/partially_update_task_by_form_api_tasks__task_id__patch)
  ![Изображение](media/tasks_patch.jpg)
  3. Нажать кнопку `Try it out`.
  4. Ввести уникальный номер задачи в БД, которую необходимо отредактировать.
  > **Note**
  >
  > - Доступ лишь у заказчика задачи и админа;
  > - Уникальный номер задачи можно получить в эндпоинте выданных пользователем задач:
  > [GET/api/tasks/my_tasks_ordered](http://localhost:8001/docs#/Tasks%20GET/get_my_tasks_ordered_api_tasks_my_tasks_ordered_get)
  
  5. Заполнить поля формы и отметить, выполнена ли задача
  > **Note**
  >
  > - `«True»` - выполнена, `«False»` - еще в работе.
  > - если поля `«задача»` и `«описание задачи»` не заполнять, они останутся прежними.
  

  7. Нажать кнопку `Execute`.
  8. Удостовериться, что задача отредактирована: ![Изображение](media/tasks_patch_200.png)
  > **Note**
  >
  > - Ответ содержит описание отредактированной задачи в формате `json`.
  > - Имеется возможность скопировать данные в буфер обмана, 
  или экспортировать в `файл json`, (открывается любым текстовым редактором).
</details>


<details>
  <summary><h3>Выданные задачи</h3></summary>
  Список задач, выданных пользователем.
  
  1. Пройти авторизацию.
  2. Выбрать эндпоинт выданных пользователем задач: 
    [GET/api/tasks/my_tasks_ordered](http://localhost:8001/docs#/Tasks%20GET/get_my_tasks_ordered_api_tasks_my_tasks_ordered_get)
  ![Изображение](media/my_tasks_ordered.png)
  3. Нажать кнопку `Try it out`.
  4. Нажать кнопку `Execute`.
  > **Note**
  >
  > - Ответ содержит отстортированный по сроку исполнения
  > список выданных пользователем еще нерешенных задач в формате `json`.
  > - Имеется возможность скопировать данные в буфер обмана, 
  или экспортировать в `файл json`, (открывается любым текстовым редактором).
</details>


<details>
  <summary><h3>Полученные задачи</h3></summary>
  Список задач, полученных пользователем.
  
  1. Пройти авторизацию.
  2. Выбрать эндпоинт полученных пользователем задач: 
    [GET/api/tasks/my_tasks_todo](http://localhost:8001/docs#/Tasks%20GET/get_my_tasks_todo_api_tasks_my_tasks_todo_get)
  ![Изображение](media/my_tasks_todo.png)
  3. Нажать кнопку `Try it out`.
  4. Нажать кнопку `Execute`.
  > **Note**
  >
  > - Ответ содержит отстортированный по сроку исполнения
  > список полученных пользователем еще нерешенных задач в формате `json`.
  > - Имеется возможность скопировать данные в буфер обмана, 
  или экспортировать в `файл json`, (открывается любым текстовым редактором).
</details>


### Разработчики
  [Артем Баландин](https://github.com/ArtemBalandin81)


<!-- MARKDOWN LINKS & BADGES -->
[Python-url]: https://www.python.org/
[Python-badge]: https://www.python.org/static/community_logos/python-powered-w-70x28.png

[FastAPI-url]: https://fastapi.tiangolo.com/
[FastAPI-badge]: https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi

[SQLite-url]: https://www.sqlite.org/
[SQLite-badge]: https://img.shields.io/badge/sqlite-%2307405e.svg?style=for-the-badge&logo=sqlite&logoColor=white

[Docker-url]: https://www.docker.com/
[Docker-badge]: https://img.shields.io/badge/docker-%230db7ed.svg?style=for-the-badge&logo=docker&logoColor=white

[Postgres-url]: https://www.postgresql.org/
[Postgres-badge]: https://img.shields.io/badge/postgres-%23316192.svg?style=for-the-badge&logo=postgresql&logoColor=white
