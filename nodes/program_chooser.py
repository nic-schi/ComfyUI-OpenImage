# program_chooser.py

import json
import os
from enum import Enum
import shlex
from typing import Any, Dict

import pathvalidate
from pydantic.v1.validators import path_validator

from ..scripts import logger, get_node_logger_prefix, CATEGORY as SCRIPT_CATEGORY


class Sources(Enum):
    SELECTED = "use Selected"
    INPUT = "use Input"
    CUSTOM = "use Custom"


class ProgramChooser:
    DISPLAY_NAME = "Program Chooser"

    # --------------------------------------------------------
    # REQUIRED: Define input types
    # --------------------------------------------------------
    @classmethod
    def INPUT_TYPES(cls):
        simple_programs = cls.load_programs_simple()

        """
        Defines node input parameters.
        Must return a dict with required/optional sections.
        """
        return {
            "required": {
                "use_source": ([e.value for e in Sources], {"default": Sources.SELECTED.value}),
                "program": (simple_programs, {}),
                "custom_executable": ("STRING", {"default": "", "placeholder": "Enter custom executable path.",
                                                 "multiline": False}),
                "override_args": ("STRING", {"default": "", "placeholder": "Enter override arguments. Use Placeholders:\n{file}: The Path to the image", "multiline": True})
            },
            "hidden": {
                "unique_id": "UNIQUE_ID",
                "extra_pnginfo": "EXTRA_PNGINFO"
            },
            "optional": {
                "program_input": ("PROGRAM", {"forceInput": True}),
            }
        }

    SEARCH_ALIASES = ["program", "selectable program", "program chooser", "program chooser node",
                      "program chooser node"]

    # --------------------------------------------------------
    # REQUIRED: Output types
    # --------------------------------------------------------
    RETURN_TYPES = ("PROGRAM",)
    RETURN_NAMES = ("chosen_program",)
    OUTPUT_NODE = True

    # --------------------------------------------------------
    # REQUIRED: Function name to execute
    # --------------------------------------------------------
    FUNCTION = "execute"

    # --------------------------------------------------------
    # REQUIRED: Category in UI
    # --------------------------------------------------------
    CATEGORY = SCRIPT_CATEGORY

    # --------------------------------------------------------
    # Program config loader
    # --------------------------------------------------------
    @classmethod
    def load_programs(cls) -> Dict[str, Dict[str, Any]]:
        """
        Reads data/programs.json and returns an index: { program_name: program_entry_dict }.

        Each entry contains at least:
          - name: str
          - category: str
          - launch: dict (e.g. {"method": "...", "args": [...]})
          - possible_paths: list[str] (environment variables expanded)

        Raises:
          - FileNotFoundError if the JSON file cannot be found
          - ValueError if the JSON structure is invalid
        """
        # nodes/program_chooser.py -> /data/programs.json
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        json_path = os.path.join(project_root, "data", "programs.json")

        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, dict) or "programs" not in data:
            raise ValueError("Expected JSON data to be a dictionary with 'programs' key")

        index: Dict[str, Dict[str, Any]] = {}

        for entry in data["programs"]:
            if not isinstance(entry, dict):
                raise ValueError("Each item in 'programs' must be an object")

            name = entry.get("name")
            category = entry.get("category")
            launch = entry.get("launch")
            possible_paths = entry.get("possible_paths", [])

            if not name or not category or not launch:
                raise ValueError(f"Each program entry must have 'name', 'category', and 'launch' keys")

            normalized_entry = dict(entry)
            normalized_entry["possible_paths"] = [os.path.expandvars(p) for p in possible_paths]

            index[name] = normalized_entry

        return index

    @classmethod
    def validate_program(cls, program) -> bool:
        for path in program["possible_paths"]:
            #logger.debug(f"Checking path: \"{path}\"; is_default=\"{program['is_default']}\"; exists=\"{os.path.exists(path)}\"")

            if program["is_default"] or os.path.exists(path) or program["launch"]["method"] in ["shell_open"]:
                return True
        return False

    @classmethod
    def load_programs_simple(cls):
        arr = []

        for program in cls.load_programs().values():
            if cls.validate_program(program):
                arr.append(program["name"])

        return arr

    @staticmethod
    def pretty(obj: Any, max_chars: int = 20_000) -> str:
        """
        Pretty-format JSON-ish python objects for console output.
        max_chars prevents flooding the ComfyUI console.
        """
        text = json.dumps(obj, indent=2, sort_keys=False, ensure_ascii=False)
        if len(text) > max_chars:
            return text[:max_chars] + "\n... <truncated> ..."
        return text

    @staticmethod
    def build_pass_dict(
            value: str,
            paths: list[str] = [],
            launch: Dict[str, Any] = None,
            original_source: str = None,
            previous_source: str = None
    ) -> Dict[str, Any]:
        return {
            "value": value,
            "paths": paths,
            "launch": launch,
            "original_source": original_source,
            "previous_source": previous_source
        }

    @staticmethod
    def apply_args_to_launch(launch: Dict[str, Any], override_args: str) -> Dict[str, Any]:
        formatted_args = None

        logger.debug(f"Override args: {override_args.strip() if override_args is not None else None}")

        if override_args is not None and override_args.strip() != "":
            formatted_args = override_args.strip()
            formatted_args = " ".join(formatted_args.splitlines())
            formatted_args = shlex.split(formatted_args, posix=False)

        logger.debug(f"Formatted args: {formatted_args}")

        if formatted_args is None:
            return launch

        new_launch = launch.copy()
        #new_launch["args"] = launch.get("args", []) + [formatted_args]
        new_launch["args"] = formatted_args

        return new_launch

    @staticmethod
    def determine_program_from_source(
            source: str,
            program: str,
            custom_executable: str,
            override_args: str,
            passthrough: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        if source == Sources.SELECTED.value:
            found_program = ProgramChooser.load_programs().get(program)
            return ProgramChooser.build_pass_dict(
                value=program,
                original_source=source,
                previous_source=source,
                launch=ProgramChooser.apply_args_to_launch(found_program["launch"], override_args),
                paths=found_program.get("possible_paths", []) or []
            )
        elif source == Sources.CUSTOM.value:
            return ProgramChooser.build_pass_dict(
                value=custom_executable,
                original_source=source,
                previous_source=source,
                launch=ProgramChooser.apply_args_to_launch({
                    "method": "exe",
                    "args": ["{file}"]
                }, override_args),
                paths=[custom_executable]
            )
        elif source == Sources.INPUT.value and passthrough is not None:
            return ProgramChooser.build_pass_dict(
                value=passthrough["value"],
                original_source=passthrough["original_source"],
                previous_source=source,
                launch=passthrough["launch"],
                paths=passthrough["paths"]
            )
        else:
            raise ValueError(f"Invalid source: {source}")

    # --------------------------------------------------------
    # Main execution logic
    # --------------------------------------------------------
    def execute(self, use_source, program, custom_executable="", override_args="", unique_id=None, extra_pnginfo=None,
                program_input=None):
        """
        This method runs when the node executes.
        Arguments MUST match INPUT_TYPES names.
        """
        logger.debug(
            f"{get_node_logger_prefix(extra_pnginfo, unique_id, self.DISPLAY_NAME)} use_source={use_source}, custom_executable={custom_executable}, program={program}, program_input={self.pretty(program_input)}")

        determined_program = self.determine_program_from_source(
            use_source,
            program,
            custom_executable,
            override_args,
            program_input
        )

        logger.debug(
            f"{get_node_logger_prefix(extra_pnginfo, unique_id, self.DISPLAY_NAME)} determined_program={self.pretty(determined_program)}")

        return (determined_program,)
