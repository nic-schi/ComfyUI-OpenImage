import os
import shutil

def find_program(possible_paths, exe_name):
    for path in possible_paths:
        expanded = os.path.expandvars(path)
        if os.path.isfile(expanded):
            return expanded
    # fallback: check in PATH
    return shutil.which(exe_name)

# --- Module-level helpers & settings ------------------------------------

# Choices for the UI dropdown
PROGRAM_CHOICES = [
    "Default-Program",
    "Default-Browser",
    "Firefox",
    "Chrome",
    "Microsoft Edge",
    "Paint",
    "Paint.NET",
    "Adobe Photoshop",
]

# Resolve known program executable paths once at import time
PROGRAM_MAP = {
    "Firefox": find_program([
        r"C:\Program Files\Mozilla Firefox\firefox.exe",
        r"C:\Program Files (x86)\Mozilla Firefox\firefox.exe"
    ], "firefox.exe"),
    "Chrome": find_program([
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
    ], "chrome.exe"),
    "Microsoft Edge": find_program([
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"
    ], "msedge.exe"),
    # "VLC Media Player": find_program([
    #     r"C:\Program Files\VideoLAN\VLC\vlc.exe",
    #     r"C:\Program Files (x86)\VideoLAN\VLC\vlc.exe"
    # ], "vlc.exe"),
    "Paint": find_program([
        "%LOCALAPPDATA%\Microsoft\WindowsApps\mspaint.exe",
        r"C:\Windows\System32\mspaint.exe",
    ], "mspaint.exe"),
    "Paint.NET": find_program([
        r"C:\Program Files\Paint.NET\paintdotnet.exe"
    ], "paintdotnet.exe"),
    "Adobe Photoshop": find_program([
        r"C:\Program Files\Adobe\Adobe Photoshop\Photoshop.exe",
        r"C:\Program Files (x86)\Adobe\Adobe Photoshop\Photoshop.exe"
    ], "Photoshop.exe"),
}

def get_browser_executables():
    """Return a list of available browser executable paths in preference order.

    This extends beyond PROGRAM_MAP to include Brave, Opera, Vivaldi, Chromium.
    Computed at call time to pick up PATH-installed browsers too.
    """
    browsers = []

    def add_if_found(paths, exe):
        p = find_program(paths, exe)
        if p and os.path.isfile(p) and p not in browsers:
            browsers.append(p)

    # Edge / Chrome / Firefox first (match PROGRAM_MAP locations + PATH)
    add_if_found([
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    ], "msedge.exe")
    add_if_found([
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    ], "chrome.exe")
    add_if_found([
        r"C:\Program Files\Mozilla Firefox\firefox.exe",
        r"C:\Program Files (x86)\Mozilla Firefox\firefox.exe",
    ], "firefox.exe")

    # Brave
    add_if_found([
        r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
        r"C:\Program Files (x86)\BraveSoftware\Brave-Browser\Application\brave.exe",
        r"%LOCALAPPDATA%\BraveSoftware\Brave-Browser\Application\brave.exe",
    ], "brave.exe")

    # Opera and Opera GX (launcher.exe is the typical entry)
    add_if_found([
        r"C:\Program Files\Opera\launcher.exe",
        r"C:\Program Files (x86)\Opera\launcher.exe",
        r"%LOCALAPPDATA%\Programs\Opera\launcher.exe",
    ], "opera.exe")
    add_if_found([
        r"%LOCALAPPDATA%\Programs\Opera GX\launcher.exe",
    ], "opera.exe")

    # Vivaldi
    add_if_found([
        r"C:\Program Files\Vivaldi\Application\vivaldi.exe",
        r"C:\Program Files (x86)\Vivaldi\Application\vivaldi.exe",
    ], "vivaldi.exe")

    # Chromium
    add_if_found([
        r"C:\Program Files\Chromium\Application\chromium.exe",
        r"C:\Program Files (x86)\Chromium\Application\chromium.exe",
    ], "chromium.exe")

    return browsers


def detect_default_browser_exe():
    """Detect the default browser executable on Windows by reading registry.

    Returns absolute path to the browser executable if detected, else None.
    """
    if os.name != 'nt':
        return None
    try:
        import winreg  # type: ignore

        def _read_default(key_path: str):
            try:
                with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, key_path) as k:
                    val, _ = winreg.QueryValueEx(k, None)
                    return val
            except OSError:
                return None

        # Get ProgId for http/https
        prog_id = None
        for scheme in ("http", "https"):
            try:
                with winreg.OpenKey(
                    winreg.HKEY_CURRENT_USER,
                    fr"Software\Microsoft\Windows\Shell\Associations\UrlAssociations\{scheme}\UserChoice",
                ) as key:
                    prog_id, _ = winreg.QueryValueEx(key, "ProgId")
                    if prog_id:
                        break
            except OSError:
                continue

        # If no ProgId, fall back to the default handler under HKCR for http
        command = None
        if prog_id:
            command = _read_default(fr"{prog_id}\shell\open\command")
        if not command:
            command = _read_default(r"http\shell\open\command")
        if not command:
            return None

        # Parse the executable path from the command string
        cmd = command.strip()
        exe_path = None
        if cmd.startswith('"'):
            # path is between first pair of quotes
            end = cmd.find('"', 1)
            if end != -1:
                exe_path = cmd[1:end]
        if not exe_path:
            # take up to .exe
            lower = cmd.lower()
            idx = lower.find('.exe')
            if idx != -1:
                exe_path = cmd[: idx + 4]

        if exe_path and os.path.isfile(exe_path):
            return exe_path

        # If parsing didn't yield a valid file, try mapping by ProgId keywords
        if prog_id:
            name = prog_id.upper()
            if "CHROME" in name:
                return PROGRAM_MAP.get("Chrome")
            if "EDGE" in name or "MSEDGE" in name:
                return PROGRAM_MAP.get("Microsoft Edge")
            if "FIREFOX" in name:
                return PROGRAM_MAP.get("Firefox")
    except Exception:
        return None
    return None


def generate_unique_filename(idx, ext=".png"):
    """Generate a unique, ordered filename using an index prefix and a time-based hash.
    Result looks like: 0001_<40-hex-sha1>.png
    Using the index as a prefix keeps album ordering stable while ensuring uniqueness.
    """
    import time
    import uuid
    import hashlib

    # Combine high-resolution time with a random salt and the index, then hash
    raw = f"{time.time_ns()}_{uuid.uuid4().hex}_{idx}".encode("utf-8")
    digest = hashlib.sha1(raw).hexdigest()
    return f"{idx+1:04d}_{digest}{ext}"


def create_temp_image_files(image):
    """Converts a ComfyUI image tensor to PNG files in a unique temp directory.
    Supports single images and batches. Returns (temp_dir, [file_paths])."""
    import PIL.Image as Image
    import numpy as np
    import tempfile
    import uuid

    # Prepare temp directory unique to this invocation
    base_temp = tempfile.gettempdir()
    temp_dir = os.path.join(base_temp, f"openimage_{uuid.uuid4().hex}")
    os.makedirs(temp_dir, exist_ok=True)

    # Convert to numpy
    try:
        arr = image.cpu().numpy()
    except AttributeError:
        # Fallback if already numpy array
        arr = image

    # Normalize and handle shape
    # Expected shapes: [B,H,W,C] or [H,W,C]. Values assumed in [0,1].
    if getattr(arr, 'ndim', None) == 3:
        arr = arr[None, ...]  # add batch dim
    if getattr(arr, 'ndim', None) != 4:
        return temp_dir, []

    file_paths = []
    for idx in range(arr.shape[0]):
        frame = arr[idx]
        # Scale to uint8 and clamp
        import numpy as _np  # local alias to avoid shadowing
        img_np = _np.clip(255.0 * frame, 0, 255).astype(_np.uint8)
        # Some pipelines may store channels first/last; assume last as per ComfyUI [H,W,C]
        # If needed, adjust when detected as [C,H,W]
        if img_np.ndim == 3 and img_np.shape[0] in (1, 3, 4) and img_np.shape[2] not in (1, 3, 4):
            # Likely [C,H,W] -> transpose to [H,W,C]
            img_np = img_np.transpose(1, 2, 0)

        # Drop extra channels if any
        if img_np.shape[2] > 4:
            img_np = img_np[:, :, :4]

        img = Image.fromarray(img_np)
        filename = generate_unique_filename(idx, ext=".png")
        file_path = os.path.join(temp_dir, filename)
        img.save(file_path)
        file_paths.append(file_path)

    return temp_dir, file_paths


def create_temp_image_file(image):
    """Legacy helper: saves only a single image to a temp file and returns the path.
    Kept for backward compatibility; the new logic uses create_temp_image_files."""
    temp_dir, files = create_temp_image_files(image)
    return files[0] if files else None


def resolve_executable(program, custom_executable):
    """Resolves which executable to use. Returns (exe_path, use_browser)."""
    exe_path = None
    use_browser = False

    # Custom executable path takes precedence
    if custom_executable and os.path.isfile(custom_executable):
        exe_path = custom_executable
    else:
        if program == "Default-Browser":
            use_browser = True
        else:
            exe_path = PROGRAM_MAP.get(program)

    return exe_path, use_browser


def open_in_default_browser(target_path_or_url):
    """Open a local file path or URL in the system default browser, reliably.

    - Properly converts Windows paths to a file URI using Path.as_uri()
      so spaces and backslashes are handled.
    - Uses open_new_tab to force tabbed behavior when possible.
    - Falls back to os.startfile on Windows if the webbrowser module fails.
    """
    import os
    import webbrowser
    from pathlib import Path

    url: str
    t = target_path_or_url

    # Convert local file paths to a valid file:// URI
    if isinstance(t, str) and not t.lower().startswith(("http://", "https://", "file://")):
        try:
            url = Path(t).resolve().as_uri()
        except Exception:
            # Last‑resort formatting; replace backslashes for URI compatibility
            p = str(Path(t).resolve()).replace("\\", "/")
            if not p.startswith("/"):
                # Ensure an absolute path has a leading slash in the URI component on Windows
                p = "/" + p
            url = f"file://{p}"
    else:
        url = t

    # On Windows, prefer launching the default browser executable directly
    try:
        if os.name == 'nt':
            exe = detect_default_browser_exe()
            if exe and os.path.isfile(exe):
                import subprocess
                subprocess.Popen([exe, url])
                return
    except Exception:
        pass

    # Try Python's webbrowser controller next (may fall back to file handler for file://)
    try:
        if webbrowser.open_new_tab(url):
            return
    except Exception:
        pass

    # Try common browsers explicitly (broader list, includes Brave/Opera/Vivaldi)
    try:
        import subprocess
        for exe2 in get_browser_executables():
            try:
                subprocess.Popen([exe2, url])
                return
            except Exception:
                continue
    except Exception:
        pass

    # Last resort: fall back to the OS default handler
    try:
        if os.name == 'nt':
            os.startfile(url)
        else:
            import subprocess
            subprocess.Popen(['xdg-open', url])
    except Exception:
        # Give up silently; ComfyUI shouldn't crash because the browser couldn't open
        pass


def open_with_specific_executable(targets, exe_path):
    """Open one or many targets (file paths) with a specific executable."""
    import subprocess
    if isinstance(targets, str):
        args = [exe_path, targets]
    else:
        args = [exe_path] + list(targets)
    subprocess.Popen(args)


def open_with_system_default(file_path):
    """Opens the file using the OS default associated application."""
    import subprocess
    if os.name == 'nt':
        os.startfile(file_path)
    else:
        subprocess.Popen(['xdg-open', file_path])


def open_album_with_system_default(file_paths):
    """Opens the first image with the system default. Most viewers will let the user browse the folder."""
    if not file_paths:
        return
    open_with_system_default(file_paths[0])

class OpenImageNode:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "images": ("IMAGE",),
            },
            "optional": {
                # Proper dropdown list so it shows in the UI
                "program": (PROGRAM_CHOICES, {"default": "Default-Browser"}),
                "custom_executable": ("STRING", {"default": "", "file_path": True, "file_ext": "exe"}),
            },
        }

    CATEGORY = "image"
    RETURN_TYPES = ()
    FUNCTION = "execute_node"
    OUTPUT_NODE = True

    def execute_node(self, images, program="Default-Browser", custom_executable=""):
        """
        Entry point for the node execution.
        Splits responsibilities into smaller helper functions.
        """
        # Create temp files (supports single image or batches)
        _temp_dir, file_paths = create_temp_image_files(images)
        exe_path, use_browser = resolve_executable(program, custom_executable)

        # Nothing to open
        if not file_paths:
            return ()

        # Browsers: open one image per tab
        if use_browser or program in ("Firefox", "Chrome", "Microsoft Edge"):
            if use_browser or not exe_path:
                # Use system default browser (or fallback if specific browser not found)
                for fp in file_paths:
                    open_in_default_browser(fp)
            else:
                # Specific browser executable: pass all files so they open as separate tabs
                open_with_specific_executable(file_paths, exe_path)
        else:
            # Specific executable or Default-Program (system default)
            if exe_path and os.path.isfile(exe_path):
                # Try to open all files with the selected program (many apps support multiple args)
                open_with_specific_executable(file_paths, exe_path)
            else:
                # Default-Program: open first image; most viewers will let user browse folder
                open_album_with_system_default(file_paths)

        return ()

    # Backwards-compat: keep the old entry but delegate to the new split logic
    def open_image(self, image, program="Default-Browser", custom_executable=""):
        return self.execute_node(image, program, custom_executable)

    # (No class-level helpers; all helpers are module-level now)
