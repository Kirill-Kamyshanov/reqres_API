import json
import warnings
from collections.abc import Callable, Generator
from pathlib import Path

import pytest

from config.environments import Environment, EnvironmentConfig, load_environment
from services.reqres_in.api import ReqresApi


def pytest_addoption(parser: pytest.Parser) -> None:
    """Регистрирует CLI-опцию --env для выбора окружения запуска."""
    parser.addoption("--env", action="store", default="stage", help="Окружение для запуска тестов (dev/stage)")


@pytest.fixture(scope="session")
def env(request: pytest.FixtureRequest) -> Environment:
    """Возвращает выбранное окружение из CLI-опции --env."""
    env_name = request.config.getoption("--env")
    try:
        return Environment(env_name.lower())
    except ValueError as exc:
        raise ValueError(f"Некорректное окружение: {env_name}. Используйте одно из: dev/stage") from exc


@pytest.fixture(scope="session")
def env_config(env: Environment) -> EnvironmentConfig:
    """Загружает конфиг текущего окружения (URL + секреты)."""
    config = load_environment(env)
    print(f"\nОкружение: {env}\n{config}\n")
    return config


@pytest.fixture(scope="session")
def test_data(env: Environment) -> dict:
    """Загружает тестовые данные окружения из test_data/{env}.json."""
    path = Path(__file__).parent / "test_data" / f"{env.value}.json"
    with path.open(encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def api(env_config: EnvironmentConfig) -> ReqresApi:
    """Главный фасад над сервисом reqres.in: api.users / api.auth / api.resources."""
    return ReqresApi(env_config)


@pytest.fixture
def cleanup() -> Generator[list[Callable[[], None]], None, None]:
    """Список действий очистки, которые выполнятся после теста (в обратном порядке).

    Сразу после создания сущности тест добавляет действие удаления:
        cleanup.append(lambda: api.users.remove(user_id))
    После теста все действия выполняются с конца списка. Ошибка одного не прерывает остальные.
    """
    tasks: list[Callable[[], None]] = []
    yield tasks
    errors: list[Exception] = []
    for task in reversed(tasks):
        try:
            task()
        except Exception as exc:
            errors.append(exc)
    if errors:
        warnings.warn(f"Cleanup errors: {errors}", stacklevel=2)
