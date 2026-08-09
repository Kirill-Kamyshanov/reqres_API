### Запуск контейнеров в Docker

Перед запуском тестов необходимо настроить переменные окружения.

#### Переменные для запуска:
- REQRES_API_KEY (авторизационный токен. Обязательный)
- ENV (тестовое окружение. Опционально. По умолчанию 'stage')


#### Примеры настройки переменных окружения:
```
 $env:REQRES_API_KEY="значение"
 $env:ENV="dev";
```

#### Примеры команд для запуска сервиса:
```
docker-compose up   # стандартный запуск всех тестов по умолчанию
docker-compose up --build  # запуск тестов с пересборкой docker-образа (при внесении изменений в Dockerfile)
docker-compose run tests -m smoke # запуск тестов с определённым маркером 
```
После запуска тестов результаты будут доступны вне контейнера в папке /allure-results
#### Получение доступа к allure-отчёту
```
allure serve # просмотр на локальном сервере
allure generate -c allure-results -o allure-report allure-results # генерация файлов с отчётами
```
---


# Framework — API-автотесты для reqres.in

Учебный фреймворк для тестирования REST API на Python: `pytest` + `requests` + `pydantic` + `allure`.

Этот документ — не просто инструкция «как запустить». Здесь по каждому решению расписано **что было до**, **что стало после** и **почему так лучше**. Цель — чтобы человек, который только начал писать автотесты, понял не только «как», но и «зачем».

---

## Содержание

1. [Как запустить](#как-запустить)
2. [Структура проекта](#структура-проекта)
3. [Что улучшили и почему](#что-улучшили-и-почему)
   - [3.1 Базовый HTTP-клиент (BaseAPI)](#31-базовый-http-клиент-baseapi)
   - [3.2 Клиенты-фасады вместо «один эндпоинт = один класс»](#32-клиенты-фасады-вместо-один-эндпоинт--один-класс)
   - [3.3 Проверки (assertions) отделены от транспорта](#33-проверки-assertions-отделены-от-транспорта)
   - [3.4 Конфиг через pydantic-settings](#34-конфиг-через-pydantic-settings)
   - [3.5 Плагины pytest: xdist / rerunfailures / timeout](#35-плагины-pytest-xdist--rerunfailures--timeout)
   - [3.6 pyproject.toml + ruff](#36-pyprojecttoml--ruff)
   - [3.7 Фикстура cleanup для очистки данных](#37-фикстура-cleanup-для-очистки-данных)
   - [3.8 Allure-шаги в тестах](#38-allure-шаги-в-тестах)

---

## Как запустить

```bash
# 1. Создать виртуальное окружение
python3.11 -m venv venv
source venv/bin/activate

# 2. Установить зависимости
pip install -r requirements.txt

# 3. Прописать .env (если нужен ключ к API)
echo "REQRES_API_KEY=ваш_ключ" > .env

# 4. Прогнать все тесты
pytest

# Только smoke
pytest -m smoke

# В 4 потока параллельно
pytest -n 4

# Конкретное окружение
pytest --env=stage

# С отчётом Allure
pytest
allure serve allure-results
```

---

## Структура проекта

```
framework2/
├── config/
│   └── environments.py        # окружения (dev/stage) и загрузка конфига
├── services/
│   ├── base_api.py            # базовый HTTP-клиент с retry/логами/маскированием секретов
│   ├── exceptions.py          # типизированные исключения транспорта
│   └── reqres_in/
│       ├── api.py             # ReqresApi — точка входа: api.users / api.auth / api.resources
│       ├── auth/              # клиент + проверки + модели для /login и /register
│       ├── users/              # клиент + проверки + модели для /users
│       └── resources/          # клиент + проверки + модели для /resources
├── tests/
│   ├── test_auth.py
│   ├── test_resources.py
│   └── test_users.py
├── test_data/
│   ├── dev.json               # тестовые данные для окружения dev
│   └── stage.json             # для stage
├── utils/
│   └── assertions.py          # общие проверки (assert_status_code)
├── conftest.py                # pytest-фикстуры (env, api, cleanup, test_data)
├── pyproject.toml             # конфиг pytest + ruff
└── requirements.txt
```

---

## Что улучшили и почему

### 3.1 Базовый HTTP-клиент (BaseAPI)

#### Как было

```python
class BaseAPI:
    def __init__(self, env_config):
        self.base_url = env_config.reqres_url
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json", ...})
```

В каждом эндпоинте свой код:

```python
class GetUser(BaseAPI):
    def get_user(self, user_id):
        response = self.session.get(f"{self.base_url}/users/{user_id}")
        attach_response(response)  # ручной вызов в каждом методе
        ...
```

#### Что плохо

1. **Нет retry.** Если у `reqres.in` случилась временная ошибка `503`, тест упадёт. CI станет «красным» из-за чужих проблем — это называют **flaky-тесты** (нестабильные).
2. **Нет таймаута.** Если сервер «висит», тест будет ждать **бесконечно** и заблокирует CI.
3. **Нет логов.** Если тест упал — непонятно, что реально произошло. Какой URL, какой статус, сколько ждали ответ?
4. **Нет связи между запросом и ответом в логах.** Если тестов параллельно идёт 50 — логи перемешиваются. Не понять, какой ответ к какому запросу относится.
5. **Каждый эндпоинт сам вызывает `attach_response()`** — это **дублирование**. Забудешь вызвать в одном из 30 классов — потеряешь информацию в отчёте.

#### Как стало

`services/base_api.py`:

```python
class BaseAPI:
    def __init__(self, env_config, timeout=30):
        self.base_url = env_config.reqres_url.rstrip("/")
        self.timeout = timeout
        self.session = self._build_session(env_config)

    def _request(self, method, path, **kwargs):
        url = ... # склейка с base_url
        request_id = uuid.uuid4().hex
        kwargs.setdefault("timeout", self.timeout)
        kwargs["headers"]["X-Request-Id"] = request_id

        # прикрепляем запрос к Allure
        self._attach_request(...)

        try:
            response = self.session.request(method, url, **kwargs)
        except Timeout as exc:
            raise ApiTimeoutError(...) from exc
        except ConnectionError as exc:
            raise ApiConnectionError(...) from exc

        # логи + прикрепляем ответ к Allure
        logger.info("api_request method=%s url=%s status=%s ...")
        self._attach_response(response, elapsed_ms, request_id)
        return response

    def get(self, path, **kwargs):  return self._request("GET", path, **kwargs)
    def post(self, path, **kwargs): return self._request("POST", path, **kwargs)
    # put / patch / delete — аналогично
```

И настройка сессии с retry:

```python
retry = Retry(
    total=3,                                          # до 3 повторов
    backoff_factor=0.3,                               # пауза между попытками растёт: 0.3 → 0.6 → 1.2 сек
    status_forcelist=(500, 502, 503, 504),            # повторяем только эти коды
    allowed_methods=("HEAD","GET","OPTIONS","PUT","DELETE"),  # POST/PATCH не повторяем (могут не быть идемпотентными)
)
adapter = HTTPAdapter(max_retries=retry, pool_connections=20, pool_maxsize=20)
session.mount("https://", adapter)
```

#### Зачем именно так

| Проблема | Решение | Почему |
|----------|---------|--------|
| Flaky-тесты от 5xx | `Retry` с backoff | Сетевая ошибка — не баг приложения, ретрай отделит «реальные баги» от «дёрнулась сеть». **Backoff** (нарастающая пауза) — чтобы не долбить сервер сразу повторами. |
| Зависшие тесты | `timeout=30` по умолчанию | Любой запрос завершится максимум за 30 секунд. Тест упадёт быстро и понятно. |
| Не понять, что упало | Структурированные логи + типизированные исключения | `ApiTimeoutError` — таймаут, `ApiConnectionError` — сеть, `ApiError` — всё остальное. По exception-у сразу видно класс проблемы. |
| Спутанные логи в параллели | `request_id = uuid.uuid4().hex` | Уникальный ID добавляется в заголовок `X-Request-Id`, в логи и в отчёт. Можно найти запрос по этому ID на стороне backend (если они логируют этот заголовок). |
| Дублирование `attach_response` | Перенесли в `_request` | Любой запрос автоматически прикрепляется к Allure. Невозможно забыть. |
| `POST` не повторяется автоматически | `allowed_methods` без POST/PATCH | Создание/изменение могут быть **не идемпотентными** — повтор создаст дубль. Идемпотентные методы (GET, PUT, DELETE) повторять безопасно. |

> **Идемпотентность** — свойство операции, при котором повторное выполнение не меняет результат. `GET /users/1` можно вызвать 100 раз — данные не поменяются. А `POST /users` создаст 100 пользователей.

---

### 3.2 Клиенты-фасады вместо «один эндпоинт = один класс»

#### Как было

10 файлов, по одному классу с одним методом в каждом:

```
services/reqres_in/users/
├── get_user.py        # class GetUser   с методом get_user()
├── get_users.py       # class GetUsers  с методом get_users()
├── post_create.py     # class CreateUser
├── put_update.py      # class UpdateUserPut
├── patch_update.py    # class UpdateUserPatch
└── delete_user.py     # class DeleteUser
```

В тесте надо импортировать каждый и инстанцировать каждый отдельно:

```python
from services.reqres_in.users.get_user import GetUser
from services.reqres_in.users.post_create import CreateUser
from services.reqres_in.users.delete_user import DeleteUser

def test_x(env_config):
    response, _ = GetUser(env_config).get_user(1)
    response, _ = CreateUser(env_config).create_user("Bob", "Dev")
    DeleteUser(env_config).delete(1)
```

#### Что плохо

1. **Взрыв количества файлов.** На 10 эндпоинтов — 10 файлов. На реальном сервисе с 200 эндпоинтами — 200 файлов. Это ад навигации.
2. **Куча импортов в каждом тесте.** Если тест работает с 5 эндпоинтами — 5 импортов и 5 инстанцирований клиента.
3. **Каждое инстанцирование создаёт новый `Session`** — новые соединения, нет переиспользования. Медленнее.
4. **Логически связанные действия размазаны по файлам.** Чтобы понять, как работать с пользователями, нужно открыть 6 файлов.

#### Как стало

Один клиент-**фасад** на ресурс:

```python
# services/reqres_in/users/client.py
class UsersClient(BaseAPI):
    """Фасад над ресурсом /users — единый клиент на все операции с пользователями."""

    resource = "/users"

    def list(self, page=1):           ...    # GET /users
    def get_by_id(self, user_id):     ...    # GET /users/{id}
    def create(self, name, job):      ...    # POST /users
    def update_put(self, ...):        ...    # PUT /users/{id}
    def update_patch(self, ...):      ...    # PATCH /users/{id}
    def remove(self, user_id):        ...    # DELETE /users/{id}
```

И ещё одна точка входа сверху:

```python
# services/reqres_in/api.py
class ReqresApi:
    def __init__(self, env_config):
        self.users = UsersClient(env_config)
        self.auth = AuthClient(env_config)
        self.resources = ResourcesClient(env_config)
```

В тесте — один импорт через фикстуру:

```python
def test_x(api):                       # api — фикстура из conftest.py
    response, _ = api.users.get_by_id(1)
    response, validated = api.users.create("Bob", "Dev")
    api.users.remove(validated.id)
```

#### Зачем именно так

- **Группировка по ресурсу.** Всё про `users` — в одном файле. Открыл — увидел все 6 операций.
- **Один импорт на весь сервис.** В тесте импортируется только то, что специфично (модели запросов, проверки), а сам клиент — через фикстуру `api`.
- **Шаблон проектирования «Фасад».** ReqresApi — единая «витрина», за которой спрятаны детали. Если завтра поменяется внутренняя структура клиентов — тесты не сломаются.
- **Одна `Session` на ресурс.** Connection pooling работает — соединения переиспользуются.
- **Расширяемость.** Добавить новый эндпоинт = добавить метод в существующий класс. Не плодим файлы.

---

### 3.3 Проверки (assertions) отделены от транспорта

#### Как было

В одном файле и HTTP-вызов, и проверка:

```python
# services/reqres_in/users/get_user.py
class GetUser(BaseAPI):
    def get_user(self, user_id): ...        # делает HTTP-запрос

def assert_user_data_is_correct(...):       # тут же — проверка
    ...
```

#### Что плохо

- Смешаны **два разных слоя**: транспорт (как сходить за данными) и валидация (что должно быть в ответе).
- Если функция проверки растёт — файл с клиентом раздувается.
- Невозможно переиспользовать проверки отдельно (например, в нагрузочных тестах, где Allure не нужен).

#### Как стало

Проверки вынесены в отдельный файл рядом:

```
services/reqres_in/users/
├── client.py          # только HTTP-вызовы и Pydantic-валидация структуры
└── assertions.py      # только проверки (assert_user_data, assert_user_created, ...)
```

```python
# assertions.py
@allure.step("Проверка созданного пользователя: {expected_name}")
def assert_user_created(response, validated, expected_name, expected_job):
    """Проверяет успешное создание пользователя: статус 201, имя, должность, наличие id и createdAt."""
    assert_status_code(response, 201)
    assert validated.name == expected_name, ...
    ...
```

#### Зачем именно так

- **Принцип единственной ответственности (SRP).** Один модуль — одна задача. `client.py` отвечает за HTTP, `assertions.py` — за проверки.
- **Тонкий клиент.** Клиент можно переиспользовать в любом контексте (тесты, нагрузка, скрипты-ассистенты), не таща с собой проверки.
- **Удобство навигации.** Если упал тест — открываешь `assertions.py` и сразу видишь, что именно проверяется.

---

### 3.4 Конфиг через pydantic-settings

#### Как было

```python
# config/environments.py
import os
from dotenv import load_dotenv
load_dotenv(...)

@dataclass
class EnvironmentConfig:
    reqres_url: str
    reqres_api_key: str

_api_key = os.environ.get("REQRES_API_KEY", "")    # ручное чтение

environments = {
    Environment.DEV: EnvironmentConfig(reqres_url="...", reqres_api_key=_api_key),
    ...
}
```

#### Что плохо

- **Нет валидации.** Если в `.env` опечатка — узнаешь только при первом тесте, который использует переменную.
- **Ручное `os.environ.get(...)`** — везде дублируется при добавлении новых переменных.
- **Нет типов для окружения.** `os.environ.get()` всегда возвращает строку. Если ждёшь число или булево — конвертируй вручную.
- **Глобальный словарь `environments`** — антипаттерн, привязка к импорту.

#### Как стало

```python
# config/environments.py
from pydantic_settings import BaseSettings, SettingsConfigDict

class EnvironmentConfig(BaseSettings):
    """Конфиг окружения. URL фиксированы в коде, секреты — из .env / переменных окружения."""

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")

    reqres_url: str
    reqres_api_key: str = Field(default="")


_URLS = {
    Environment.DEV: "https://reqres.in/api",
    Environment.STAGE: "https://reqres.in/api",
}


def load_environment(env):
    return EnvironmentConfig(reqres_url=_URLS[env])
```

#### Зачем именно так

- **Pydantic валидирует автоматически.** Если поле объявлено как `int`, а в `.env` строка — упадёт сразу с понятным сообщением.
- **Поля = декларативный список.** Хочешь новую переменную — добавил поле в класс. Никаких `os.environ.get()`.
- **Источники в одном месте.** В `SettingsConfigDict` указано откуда брать значения: `.env`-файл, переменные окружения. Можно докрутить YAML/Vault/AWS Secrets — без изменения остального кода.
- **Типизация.** В тестах `env_config.reqres_url` имеет тип `str`, IDE подсказывает.
- **URL хардкодом — это нормально для статичного конфига.** YAML/JSON-слой имеет смысл, только если URL различаются между окружениями. У нас одинаковые — лишний слой не нужен.

---

### 3.5 Плагины pytest: xdist / rerunfailures / timeout

В `requirements.txt` добавлено:

- **`pytest-xdist`** — запускает тесты параллельно на нескольких процессах.

  ```bash
  pytest -n 4   # в 4 потока
  pytest -n auto # по числу ядер
  ```

  **Зачем:** на 10 тестах разница незаметна, на 1000 — это часы vs минуты.

- **`pytest-rerunfailures`** — автоматически перезапускает упавшие тесты.

  ```toml
  # в pyproject.toml
  addopts = ["--reruns=2", "--reruns-delay=1"]
  ```

  **Зачем:** если тест упал из-за случайного сетевого сбоя — пусть pytest попробует ещё 2 раза, прежде чем красить билд. **Важно:** это страховка, не повод оставлять flaky-тесты как есть.

- **`pytest-timeout`** — глобальный таймаут на тест.

  ```toml
  addopts = ["--timeout=60"]
  ```

  **Зачем:** даже если retry в `BaseAPI` пропустит зависание — pytest принудительно убьёт тест через 60 секунд. Двойная страховка.

---

### 3.6 pyproject.toml + ruff

#### Как было

- `pytest.ini` — конфиг pytest.
- Никакого линтера / форматтера.
- Стиль кода — на усмотрение того, кто пишет.

#### Что плохо

- **Конфиги размазаны.** `pytest.ini`, `requirements.txt`, потом ещё `setup.py` появится — никакой единой точки.
- **Каждый пишет в своём стиле.** Одни кавычки, другие, разный отступ, неотсортированные импорты — ревью превращается в обсуждение точек с запятыми вместо логики.
- **Ошибки находишь только при запуске.** Неиспользованный импорт, опечатка в имени переменной — всплывут на ревью или в проде.

#### Как стало

`pyproject.toml` — единый конфиг проекта:

```toml
[tool.pytest.ini_options]
markers = ["smoke", "regression"]
addopts = ["--alluredir=allure-results", "--strict-markers", "--reruns=2", "--timeout=60"]

[tool.ruff]
line-length = 120
target-version = "py311"

[tool.ruff.lint]
select = ["E", "W", "F", "I", "B", "UP", "RUF", "SIM", "C4"]
```

Запуск:

```bash
ruff check .            # найти проблемы
ruff check --fix .      # автоисправить
ruff format .           # форматирование (как black)
```

#### Зачем именно так

- **Единый конфиг.** `pyproject.toml` — стандарт PEP 518. В нём pytest, ruff, в будущем — всё остальное.
- **`ruff` — один инструмент вместо пяти.** Заменяет `flake8` + `isort` + `black` + `pyupgrade` + `bandit` (частично). И в 100 раз быстрее (написан на Rust).
- **Правила** (что значат буквы в `select`):
  - `E/W` — стиль (PEP 8): отступы, длинные строки.
  - `F` — pyflakes: неиспользованные импорты, обращения к несуществующим переменным.
  - `I` — isort: автоматическая сортировка импортов.
  - `B` — flake8-bugbear: типичные баги (например, `except:` без типа).
  - `UP` — pyupgrade: подсказки по новому синтаксису Python (`Optional[X]` → `X | None`).
  - `SIM` — упрощения (`if x == True` → `if x`).
  - `C4` — comprehensions (использовать `[x for x in ...]` где уместно).
- **`--strict-markers`** — если в тесте опечатка в маркере (`@pytest.mark.smok` вместо `smoke`), pytest упадёт сразу. Без этого флага он молча проигнорирует.

---

### 3.7 Фикстура cleanup для очистки данных

#### Как было

Узкоспециализированная фикстура только для удаления пользователя:

```python
@pytest.fixture
def user_data():
    return {}

@pytest.fixture
def delete_user(env_config, user_data):
    yield
    user_id = user_data.get('id')
    if user_id:
        DeleteUser(env_config).delete(user_id)
```

В тесте:

```python
def test_create_user(env_config, user_data, delete_user):
    response, validated = CreateUser(env_config).create_user(...)
    user_data.update(validated.model_dump())   # надо не забыть положить id
```

#### Что плохо

- **Узко.** Только пользователь, только один. Если тест создаёт два — не работает. Если тест создаёт ресурс — нужна другая фикстура.
- **Хрупко.** Забыл `user_data.update(...)` — данные не удалятся.
- **Магия.** Связь между `delete_user` и `user_data` неочевидна, надо лезть в `conftest.py`.

#### Как стало

Универсальная фикстура — обычный список действий:

```python
@pytest.fixture
def cleanup() -> Generator[list[Callable[[], None]], None, None]:
    """Список действий очистки, которые выполнятся после теста (в обратном порядке).

    Сразу после создания сущности тест добавляет действие удаления:
        cleanup.append(lambda: api.users.remove(user_id))
    После теста все действия выполняются с конца списка. Ошибка одного не прерывает остальные.
    """
    tasks = []
    yield tasks
    errors = []
    for task in reversed(tasks):
        try:
            task()
        except Exception as exc:
            errors.append(exc)
    if errors:
        warnings.warn(f"Cleanup errors: {errors}", stacklevel=2)
```

В тесте:

```python
def test_create_user(api, cleanup):
    response, validated = api.users.create(...)
    cleanup.append(lambda: api.users.remove(validated.id))   # сразу регистрируем удаление
    assert_user_created(...)
```

#### Зачем именно так

- **Универсальность.** Можно зарегистрировать любое действие: удаление пользователя, ресурса, отзыв токена, восстановление настройки. Все в одной фикстуре.
- **LIFO (последний вошёл — первый вышел).** Если тест создал пользователя, потом — токен на этого пользователя, удаление пойдёт в обратном порядке. Это важно: сначала надо отозвать токен, потом удалить пользователя.
- **Изолированные ошибки.** Если одно из действий упало — остальные всё равно выполнятся. Тест не оставит «мусор».
- **Простота.** Это просто `list`. Никаких классов, наследования, реестров. Новичок открыл `conftest.py` — всё видно за 10 секунд.
- **Регистрация рядом с созданием.** Сразу после `create()` сразу `cleanup.append(...)`. Невозможно «забыть» — потому что это **одна строка** ниже.

---

### 3.8 Allure-шаги в тестах

#### Как было

Тест выглядит как код:

```python
def test_create_user(self, env_config, user_data, delete_user):
    new_user = CreateUserRequest()
    response, validated = CreateUser(env_config).create_user(**new_user.model_dump())
    assert_user_created_correctly(response, validated, new_user.name, new_user.job)
    user_data.update(validated.model_dump())
```

В Allure отчёт уйдёт результат, но **что именно проверяет тест** — непонятно без чтения кода.

#### Как стало

```python
@allure.title("Создание нового пользователя")
def test_create_user(self, api, cleanup):
    """Проверяет успешное создание пользователя и корректность возвращаемых данных."""
    with allure.step("Создаём нового пользователя"):
        new_user = CreateUserRequest()
        response, validated = api.users.create(**new_user.model_dump())
        cleanup.append(lambda: api.users.remove(validated.id))

    with allure.step("Проверка корректности создания"):
        assert_user_created(response, validated, new_user.name, new_user.job)
```

#### Зачем именно так

- **Отчёт читается как ручной тест-кейс.** QA Manual открывает Allure и видит шаги:
  1. «Создаём нового пользователя»
  2. «Проверка корректности создания»
- **Связка между шагом и его результатом.** В каждом шаге — свой запрос с `request_id`, свой ответ. Можно свернуть/раскрыть.
- **Локализация ошибок.** Если упало в «Проверке корректности» — проблема в данных, а не в самом запросе. И обратно. В Allure это видно по тому, на каком именно шаге сломалось.
- **Документация без отдельного документа.** Чтобы понять, что покрывает тест, не нужно читать Python-код. Достаточно открыть отчёт.

**Правило проекта:** в каждом тесте минимум два `with allure.step(...)`-блока — «отправка запроса» и «проверка ответа». Если есть подготовка данных — выделять отдельным шагом.

---

