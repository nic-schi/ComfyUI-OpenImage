from .open_image_node import OpenImageNode

# Mapping the internal class name to the name that appears in the search menu
NODE_CLASS_MAPPINGS = {
    "Open Image": OpenImageNode,
}

# Optional: Mapping the internal name to a display name in the UI
NODE_DISPLAY_NAME_MAPPINGS = {
    "Open Image": "Open Generated Image",
}

# The line below is important for Python to recognize the module
__all__ = ['NODE_CLASS_MAPPINGS', 'NODE_DISPLAY_NAME_MAPPINGS']