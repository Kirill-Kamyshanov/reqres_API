from config.environments import EnvironmentConfig
from services.reqres_in.auth.client import AuthClient
from services.reqres_in.resources.client import ResourcesClient
from services.reqres_in.users.client import UsersClient


class ReqresApi:
    """Точка входа для тестов: один объект с фасадами по всем ресурсам сервиса reqres.in."""

    def __init__(self, env_config: EnvironmentConfig) -> None:
        """Инициализирует клиенты всех ресурсов на одном env_config (общая конфигурация и api-key)."""
        self.users = UsersClient(env_config)
        self.auth = AuthClient(env_config)
        self.resources = ResourcesClient(env_config)
