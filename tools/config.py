import os.path
import sys
from argparse import Namespace
from typing import Any, Callable, Dict, Optional

import pytoml as toml


# TODO add tests for this
def load_config(config_file: str, profile: Optional[str] = None):
    """
    Load profile from the config file.

    :param config_file:
    :param profile: If default, use the value of the default key in the config file
    :return:
    """
    config_filepath = os.path.expanduser(config_file)
    config = load_user_config_file(config_filepath)

    # set profile to the value of the default key
    if not profile:
        if "default_profile" not in config:
            print(
                f"No profile supplied, or default profile set in {config_filepath}", file=sys.stderr,
            )
            exit(1)
        profile = config["default_profile"]

    # make top level keys available in the profile
    if config.get("additional_tags", None):
        config[profile]["additional_tags"] = config["additional_tags"]

    try:
        return config[profile]
    except KeyError:
        print(f"Missing profile {profile} in {config_filepath}", file=sys.stderr)
        exit(1)


def load_user_config_file(config_filepath) -> Dict[str, Any]:
    if not os.path.isfile(config_filepath):
        print(f"No config file {config_filepath}", file=sys.stderr)
        exit(1)

    with open(config_filepath) as config_file:
        return toml.load(config_file)


def inject_config(config_file: str) -> Callable[[Namespace], None]:
    def inner(namespace: Namespace) -> None:
        # replace the "config" arg value with a dict loaded from the config file
        if "config" in namespace:
            setattr(namespace, "config", load_config(config_file, namespace.config))

    return inner
