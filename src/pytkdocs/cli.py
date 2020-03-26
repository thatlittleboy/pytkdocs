"""
This module contains the command line application.

Why does this file exist, and why not put this in `__main__`?

You might be tempted to import things from __main__ later,
but that will cause problems; the code will get executed twice:

- When you run `python -m pytkdocs` python will execute
  `__main__.py` as a script. That means there won't be any
  `pytkdocs.__main__` in `sys.modules`.
- When you import __main__ it will get executed again (as a module) because
  there's no `pytkdocs.__main__` in `sys.modules`.

Also see http://click.pocoo.org/5/setuptools/#setuptools-integration.
"""

import argparse
import json
import sys
import traceback
from typing import List, Optional

from .loader import Loader
from .objects import ObjectUnion
from .serializer import serialize_object


def process_config(config: dict) -> dict:
    """
    Process a loading configuration.

    The `config` argument is a dictionary looking like this:

    ```python
    {
        "objects": [
            {"path": "python.dotted.path.to.the.object1"},
            {"path": "python.dotted.path.to.the.object2"}
        ]
    }
    ```

    The result is a dictionary looking like this:

    ```python
    {
        "loading_errors": [
            "message1",
            "message2",
        ],
        "parsing_errors": {
            "path.to.object1": [
                "message1",
                "message2",
            ],
            "path.to.object2": [
                "message1",
                "message2",
            ]
        },
        "objects": [
            {
                "path": "path.to.object1",
                # other attributes, see the documentation for `pytkdocs.objects` or `pytkdocs.serializer`
            },
            {
                "path": "path.to.object2",
                # other attributes, see the documentation for `pytkdocs.objects` or `pytkdocs.serializer`
            },
        ]
    }
    ```

    Arguments:
        config: The configuration.

    Returns:
        The collected documentation along with the errors that occurred.
    """
    global_config = config.get("global_config", {})
    collected = []
    loading_errors = []
    parsing_errors = {}

    for obj in config["objects"]:
        loader_config = dict(global_config)
        loader_config.update(obj.get("config", {}))
        loader = Loader(**loader_config)

        obj = loader.get_object_documentation(obj["path"])

        loading_errors.extend(loader.errors)
        parsing_errors.update(extract_errors(obj))

        serialized_obj = serialize_object(obj)
        collected.append(serialized_obj)

    print(json.dumps(dict(loading_errors=loading_errors, parsing_errors=parsing_errors, objects=collected)))

def process_json(json_input: str) -> dict:
    """
    Process JSON input.

    Simply load the JSON as a Python dictionary, then pass it to [`process_config`][pytkdocs.cli.process_config].

    Arguments:
        json_input: The JSON to load.

    Returns:
        The result of the call to [`process_config`][pytkdocs.cli.process_config].
    """
    return process_config(json.loads(json_input))


def extract_docstring_parsing_errors(errors: dict, o: ObjectUnion) -> None:
    """
    Recursion helper.

    Update the `errors` dictionary by side-effect. Recurse on the object's children.

    Arguments:
        errors: The dictionary to update.
        o: The object.
    """
    if hasattr(o, "docstring_errors"):
        errors[o.path] = o.docstring_errors
    for child in o.children:
        extract_docstring_parsing_errors(errors, child)


def extract_errors(obj: ObjectUnion) -> dict:
    """
    Extract the docstring parsing errors of each object, recursively, into a flat dictionary.

    Arguments:
        obj: An object from `pytkdocs.objects`.

    Returns:
        A flat dictionary. Keys are the objects' names.
    """
    parsing_errors = {}
    extract_docstring_parsing_errors(parsing_errors, obj)
    return parsing_errors


def get_parser() -> argparse.ArgumentParser:
    """Return the program argument parser."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-1",
        "--line-by-line",
        action="store_true",
        dest="line_by_line",
        help="Process each line read on stdin, one by one.",
    )
    return parser


def main(args: Optional[List[str]] = None) -> int:
    """
    The main function, which is executed when you type `pytkdocs` or `python -m pytkdocs`.

    Parameters:
        args: The list of arguments.

    Returns:
        An exit code between 0 and 255.
    """
    parser = get_parser()
    args = parser.parse_args(args)

    if args.line_by_line:
        for line in sys.stdin:
            try:
                process_json(line)
            except Exception as error:
                # Don't fail on error. We must handle the next inputs.
                # Instead, print error as JSON.
                print(json.dumps({"error": str(error), "traceback": traceback.format_exc()}))
    else:
        process_json(sys.stdin.read())

    return 0
