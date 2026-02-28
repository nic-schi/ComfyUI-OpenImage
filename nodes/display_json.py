# display_json.py
from ..scripts import get_node_logger_prefix, logger, CATEGORY as SCRIPT_CATEGORY
from .program_chooser import ProgramChooser
import json


class DisplayJSONNode:
    DISPLAY_NAME = "Display JSON"

    # --------------------------------------------------------
    # REQUIRED: Define input types
    # --------------------------------------------------------
    @classmethod
    def INPUT_TYPES(cls):
        """
        Defines node input parameters.
        Must return a dict with required/optional sections.
        """
        return {
            "required": {
                "pretty_print": ("BOOLEAN", {"default": True}),
            },
            "hidden": {
                "unique_id": "UNIQUE_ID",
                "extra_pnginfo": "EXTRA_PNGINFO"
            },
            "optional": {
                "json_input": ("*", {"forceInput": True})
            }
        }

    SEARCH_ALIASES = ["output", "display", "print", "json", "json display", "json display node", "json display node", "pretty print", "json pretty print", "json pretty", "json formatter"]

    # --------------------------------------------------------
    # REQUIRED: Output types
    # --------------------------------------------------------
    RETURN_TYPES = ()
    RETURN_NAMES = ()
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
    # Main execution logic
    # --------------------------------------------------------
    def execute(self, pretty_print=True, unique_id=None, extra_pnginfo=None, json_input=None):
        """
        This method runs when the node executes.
        Arguments MUST match INPUT_TYPES names.
        """
        if json_input is None:
            return {"ui": {"text": ""}}

        text = ""

        if isinstance(json_input, (dict, list)):
            if pretty_print:
                text = ProgramChooser.pretty(json_input)
            else:
                text = json.dumps(json_input, ensure_ascii=False)
        elif isinstance(json_input, str):
            if pretty_print:
                try:
                    obj = json.loads(json_input)
                    text = ProgramChooser.pretty(obj)
                except Exception:
                    text = json_input
            else:
                text = json_input
        else:
            text = str(json_input)

        logger.info(f"{get_node_logger_prefix(extra_pnginfo, unique_id, self.DISPLAY_NAME)} Received {len(text)} characters of data! (Pretty Print: {pretty_print})")

        return {
            "ui": {
                "text": [text]
            }
        }