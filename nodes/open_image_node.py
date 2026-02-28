# open_image_node.py

import os
import shlex
import subprocess
import tempfile
import time
import winreg
from typing import Dict, Any

import numpy as np
from PIL import Image

from .program_chooser import ProgramChooser
from ..scripts import logger, get_node_logger_prefix, CATEGORY as SCRIPT_CATEGORY


class OpenImageNode:
    DISPLAY_NAME = "Open Generated Image"

    # --------------------------------------------------------
    # REQUIRED: Define input types
    # --------------------------------------------------------
    @classmethod
    def INPUT_TYPES(cls):
        input_types_pc = ProgramChooser.INPUT_TYPES()

        """
        Defines node input parameters.
        Must return a dict with required/optional sections.
        """
        return {
            "required": {
                            "image": ("IMAGE", {"forceInput": True})
                        } | input_types_pc["required"],
            "hidden": input_types_pc["hidden"],
            "optional": input_types_pc["optional"]
        }

    SEARCH_ALIASES = ["program opener", "open", "open image", "open image node", "open image program",
                      "open image program node", "open image program node"]

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
    # Main execution logic
    # --------------------------------------------------------
    def execute(self, image, use_source, program, custom_executable="", override_args="", unique_id=None,
                extra_pnginfo=None,
                program_input=None):
        """
        This method runs when the node executes.
        Arguments MUST match INPUT_TYPES names.
        """
        logger_prefix = get_node_logger_prefix(extra_pnginfo, unique_id, self.DISPLAY_NAME)

        logger.debug(
            f"{logger_prefix} use_source={use_source}, program={program}, custom_executable={custom_executable}, program_input={ProgramChooser.pretty(program_input)}")

        determined_program = ProgramChooser.determine_program_from_source(
            use_source,
            program,
            custom_executable,
            override_args,
            program_input
        )

        logger.debug(f"{logger_prefix} determined_program={ProgramChooser.pretty(determined_program)}")

        # Open the image & measure time
        start = time.perf_counter()

        success = self.open_image(logger_prefix, image, determined_program)

        end = time.perf_counter()
        duration = end - start

        if duration > 1.0:
            time_took = f"{duration:.2f} s"
        else:
            time_took = f"{duration * 1000:.2f} ms"

        if not success:
            logger.error(f"{logger_prefix} Failed to open image in {time_took}")
        else:
            logger.info(f"{logger_prefix} Successfully opened image in {time_took}")

        return (determined_program,)

    @staticmethod
    def process_image(image_tensor):
        img_data = image_tensor[0].cpu().numpy()
        img_data = (img_data * 255).astype(np.uint8)

        img = Image.fromarray(img_data)

        return img

    def open_image(
            self,
            logger_prefix,
            image,
            pass_dict: Dict[str, Any]
    ) -> bool:
        """
        Opens an image using the provided image tensor and pass dictionary.
        Saves the image to a temporary file and logs the operation.
        Returns True if successful, False otherwise.
        """
        img = self.process_image(image)

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as temp_file:
            img.save(temp_file.name)
            tmp_file_path = temp_file.name

        logger.info(f"{logger_prefix} Saved Image to temporary File: \"{tmp_file_path}\"")
        logger.info(f"{logger_prefix} \"{pass_dict['original_source']}\" with \"{pass_dict['value']}\" to Open Image.")

        exceptions = []
        success = False

        launch = pass_dict.get("launch", {})
        method = launch.get("method", "exe")
        launch_args = launch.get("args", ["{file}"])

        for raw_path in pass_dict["paths"]:
            try:
                # Handle placeholders
                # System default
                if raw_path == "<SYSTEM_DEFAULT>" or raw_path == "<SYSTEM_DEFAULT_PROGRAM>":
                    if method == "shell_open":
                        os.startfile(tmp_file_path)
                        success = True
                        break
                    continue

                # Default browser
                if raw_path == "<SYSTEM_DEFAULT_BROWSER>":
                    cmd_parts = self.detect_default_browser_exe()
                    if cmd_parts is not None:
                        subprocess.Popen(cmd_parts + [tmp_file_path])
                        success = True
                        break
                    continue

                # Prepare arguments
                cmd_args = []
                for arg in launch_args:
                    arg = arg.replace("{file}", tmp_file_path)
                    cmd_args.append(arg)

                logger.debug(f"{logger_prefix} Launching program: \"{raw_path}\" with args: {cmd_args}")
                logger.debug(f"{logger_prefix} Full command: \"{raw_path}\" {' '.join(cmd_args)}")

                if method == "exe":
                    subprocess.Popen([raw_path] + cmd_args)
                    success = True
                    break
                elif method == "shell_open":
                    subprocess.Popen([raw_path] + cmd_args)
                    success = True
                    break

                if success:
                    break

            except FileNotFoundError as f:
                logger.debug(f"{logger_prefix} File not found: \"{raw_path}\"")
                exceptions.append({
                    "path": raw_path,
                    "exception": f
                })
                continue
            except Exception as e:
                logger.error(f"{logger_prefix} Failed to open image with \"{raw_path}\": {e}")
                exceptions.append({
                    "path": raw_path,
                    "exception": e
                })
                continue

        if not success:
            logger.debug(f"{logger_prefix} No valid program found to open image: \"{tmp_file_path}\"")
            logger.debug(f"{logger_prefix} Exceptions ({len(exceptions)}):")

            for exception in exceptions:
                logger.debug(f"{logger_prefix} - \"{exception['path']}\": {exception['exception']}")
            return False
        else:
            return True

    def detect_default_browser_exe(self):
        if os.name != 'nt':
            return None

        def get_cmd_from_reg(prog_id):
            # Search roots for Registry
            search_roots = [
                (winreg.HKEY_CURRENT_USER, rf"Software\Classes\{prog_id}\shell\open\command"),
                (winreg.HKEY_CLASSES_ROOT, rf"{prog_id}\shell\open\command")
            ]
            for root, path in search_roots:
                try:
                    with winreg.OpenKey(root, path) as key:
                        value, _ = winreg.QueryValueEx(key, None)
                        return value
                except OSError:
                    continue
            return None

        try:
            # 1. determine ProgId
            prog_id = None
            user_choice_path = r"Software\Microsoft\Windows\Shell\Associations\UrlAssociations\http\UserChoice"
            try:
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, user_choice_path) as key:
                    prog_id, _ = winreg.QueryValueEx(key, "ProgId")
            except OSError:
                pass

            # 2. Extract command
            command = get_cmd_from_reg(prog_id) if prog_id else get_cmd_from_reg("http")

            if not command:
                return None

            # 3. Sauber extrahieren: shlex trennt den Pfad von den Argumenten (z.B. -osint)
            # posix=False ist wichtig für Windows-Backslashes
            parts = shlex.split(command, posix=False)
            if not parts:
                return None

            exe_path = parts[0].strip('"')

            # 4. Validate
            if os.path.exists(exe_path):
                return parts

            return None

        except Exception:
            return None
