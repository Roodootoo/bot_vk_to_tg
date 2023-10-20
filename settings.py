"""Module for load settings form `.env` or if server running with parameter
`dev` from `.env.dev`"""
import pathlib
from functools import lru_cache

import pydantic
from dotenv import find_dotenv
from pydantic.env_settings import BaseSettings
from pydantic.types import PositiveInt, SecretStr

from app.pkg.models import UserRole
from app.pkg.models.types import EncryptedSecretBytes

__all__ = ["Settings", "get_settings"]


class _Settings(BaseSettings):
    class Config:
        """Configuration of settings."""

        #: str: env file encoding.
        env_file_encoding = "utf-8"
        #: str: allow custom fields in model.
        arbitrary_types_allowed = True


class Settings(_Settings):
    """Server settings.

    Formed from `.env` or `.env.dev`.
    """

    DOMAIN_VK = config.get('VK', 'DOMAIN')
    COUNT_VK = config.get('VK', 'COUNT')
    VK_TOKEN = config.get('VK', 'TOKEN', fallback=None)
    #: SecretStr: secret x-token for authority.
    BOT_TOKEN = config.get('Telegram', 'BOT_TOKEN')

    CHANNEL = config.get('Telegram', 'CHANNEL')
    INCLUDE_LINK = config.getboolean('Settings', 'INCLUDE_LINK')
    PREVIEW_LINK = config.getboolean('Settings', 'PREVIEW_LINK')
    REPOSTS = config.getboolean('Settings', 'REPOSTS')

    #: SecretStr: secret x-token for authority.
    X_API_TOKEN: SecretStr

    #: str: Postgresql host.
    POSTGRES_HOST: str
    #: PositiveInt: positive int (x > 0) port of postgresql.
    POSTGRES_PORT: PositiveInt
    #: str: Postgresql user.
    POSTGRES_USER: str
    #: SecretStr: Postgresql password.
    POSTGRES_PASSWORD: SecretStr
    #: str: Postgresql database name.
    POSTGRES_DATABASE_NAME: str

    #: SecretStr: Key for encrypt payload in jwt.
    JWT_SECRET_KEY: SecretStr
    #: str: Access token name in headers/body/cookies.
    JWT_ACCESS_TOKEN_NAME: str
    #: str: Refresh token name in headers/body/cookies.
    JWT_REFRESH_TOKEN_NAME: str

    #: StrictStr: Level of logging which outs in std
    LOGGER_LEVEL: pydantic.StrictStr
    #: pathlib.Path: Path of saving logs on local storage.
    LOGGER_FILE_PATH: pathlib.Path

    #: PositiveInt: Pages limit for article
    ARTICLES_PAGE_LIMIT: PositiveInt
    #: PositiveInt: Pages limit for pets
    ANIMALS_PAGE_LIMIT: PositiveInt
    #: PositiveInt: Pages limit for shelters and cat cafes
    SHELTERS_CATCAFES_PAGE_LIMIT: PositiveInt


@lru_cache()
def get_settings(env_file: str = ".env") -> Settings:
    """Create settings instance."""
    return Settings(_env_file=find_dotenv(env_file))
