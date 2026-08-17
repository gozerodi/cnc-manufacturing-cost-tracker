import configparser
import os
import sys


class ConfigError(Exception):
    pass


def get_base_dir() -> str:
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def get_config_path() -> str:
    return os.path.join(get_base_dir(), "config.ini")


class DatabaseConfig:
    def __init__(self, host: str, port: int, dbname: str, user: str, password: str):
        self.host = host
        self.port = port
        self.dbname = dbname
        self.user = user
        self.password = password

    @property
    def sqlalchemy_url(self) -> str:
        return (
            f"postgresql+psycopg2://{self.user}:{self.password}"
            f"@{self.host}:{self.port}/{self.dbname}"
        )


def load_database_config() -> DatabaseConfig:
    config_path = get_config_path()
    if not os.path.isfile(config_path):
        raise ConfigError(
            f"config.ini not found: {config_path}\n"
            "Please copy config.example.ini to config.ini and fill in "
            "your database credentials."
        )

    parser = configparser.ConfigParser()
    try:
        parser.read(config_path, encoding="utf-8")
        section = parser["database"]
        return DatabaseConfig(
            host=section["host"],
            port=section.getint("port"),
            dbname=section["dbname"],
            user=section["user"],
            password=section["password"],
        )
    except (configparser.Error, KeyError, ValueError) as exc:
        raise ConfigError(
            f"config.ini could not be read or is missing/invalid: {exc}\n"
            "Please make sure the [database] section has valid host, port, "
            "dbname, user, and password values."
        ) from exc
