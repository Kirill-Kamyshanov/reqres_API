# Framework — API-автотесты для reqres.in

Фреймворк для тестирования REST API на Python: `pytest` + `requests` + `pydantic` + `allure`.

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
