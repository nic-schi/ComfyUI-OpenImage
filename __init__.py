# /__init__.py

from .scripts import logger
from .nodes import ProgramChooser, OpenImageNode, DisplayJSONNode

NODE_CLASS_MAPPINGS = {
    "OpenImageNode": OpenImageNode,
    "ProgramChooserNode": ProgramChooser,
    # utils
    "DisplayJSONNode": DisplayJSONNode
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "OpenImageNode": "Open Generated Image",
    "ProgramChooserNode": "Program Chooser",
    # utils
    "DisplayJSONNode": "Display JSON"
}

WEB_DIRECTORY = "./web"

__all__ = ['NODE_CLASS_MAPPINGS', 'NODE_DISPLAY_NAME_MAPPINGS', 'WEB_DIRECTORY']

# logger
program_count = len(ProgramChooser.load_programs_simple())
logger.info(f"Loaded {program_count} Programs!")

logger.info("OpenImage successfully loaded! Have fun :^)")
