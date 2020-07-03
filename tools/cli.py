import functools
import json
from functools import wraps
from typing import Callable, Tuple

from argh import arg
import typer
import typer.models

from tools import config
from tools.config import load_config
from tools.display import as_table, pretty_table


class Cli:
    def __init__(self, config_file):
        self.config_file = config_file

    def cli(self, func):
        """
        A decorator that defines common args, injects config, and pretty prints the results of the function it wraps
        when called from the CLI. When called by other functions, treat it as usual familiar (undecorated) function call,
        ie: just pass through to the wrapped function. This means we can treat the function as a familiar function,
        and easily provide the extra CLI functionality only when needed.

        :param func:
        :return:
        """

        @wraps(func)
        @arg("--profile", help="Profile in the config file to use", default="default")
        def wrapper(*args, **kwargs):
            # print(args)
            # print(kwargs)

            # we are being called from tests, or by other functions, just pass through
            if args or "config" in kwargs:
                return func(*args, **kwargs)

            # we are being called from the cli, so load the config and prettify the result
            profile = kwargs.pop("profile", "default")
            kwargs["config"] = load_config(self.config_file, profile)

            result = func(*args, **kwargs)

            if isinstance(result, list):
                prettified = pretty_table(as_table(result))
                return prettified if prettified else "No results"
            elif isinstance(result, dict):
                return json.dumps(result, default=str)
            else:
                return result

        return wrapper


def cli_result(result) -> None:
    def pretty(result):
        if isinstance(result, list):
            prettified = pretty_table(as_table(result))
            return prettified if prettified else "No results"
        elif isinstance(result, dict):
            return json.dumps(result, default=str)
        else:
            return result

    print(pretty(result))


def ProfileOption(config_file: str) -> typer.models.OptionInfo:
    def load(profile: str):
        return config.load_config(config_file, profile)

    return typer.Option(
        None,
        "--profile",
        help="Profile in the config file to use",
        callback=load,
    )


def Typer() -> typer.Typer:
    return typer.Typer(context_settings=dict(help_option_names=["-h", "--help"]), result_callback=cli_result)
