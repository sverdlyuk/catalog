
import os
import yaml
import requests
import argparse
import html
import json
from PIL import Image
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import queue
import sys
import time
from datetime import datetime
from enum import Enum

args = argparse.ArgumentParser(description="Builds the keira app and mod files")
args.add_argument("--build", help="Build json files for mods and apps", action='store_true', default=False)
args.add_argument("--shortjson", help="Build short json files for mods and apps", action='store_true', default=False)
args.add_argument("--workers", help="Number of parallel workers", type=int, default=8)
args.add_argument("--verbose", "-v", help="Verbose output", action='store_true', default=False)
args = args.parse_args()

# ============================================================================
# Thread-safe Progress Tracker with Live Display
# ============================================================================

class ProgressTracker:
    """Thread-safe progress tracker with live terminal display"""
    
    # Status symbols and colors
    PENDING = ('⏳', '\033[90m')      # Gray
    RUNNING = ('🔄', '\033[94m')      # Blue  
    SUCCESS = ('✅', '\033[92m')      # Green
    WARNING = ('⚠️ ', '\033[93m')      # Yellow
    ERROR = ('❌', '\033[91m')        # Red
    RESET = '\033[0m'
    BOLD = '\033[1m'
    CLEAR_LINE = '\033[2K'
    
    def __init__(self, title: str, total: int, item_type: str = "item"):
        self.title = title
        self.total = total
        self.item_type = item_type
        self.items = {}  # name -> (status, message)
        self.lock = threading.Lock()
        self.completed = 0
        self.warnings_count = 0
        self.errors_count = 0
        self.start_time = time.time()
        self.messages = []  # Log messages to display after progress
        
    def add_item(self, name: str):
        """Add item to track"""
        with self.lock:
            self.items[name] = (self.PENDING, "Waiting...")
    
    def update(self, name: str, status: tuple, message: str = ""):
        """Update item status"""
        with self.lock:
            self.items[name] = (status, message)
            if status == self.SUCCESS:
                self.completed += 1
            elif status == self.WARNING:
                self.completed += 1
                self.warnings_count += 1
            elif status == self.ERROR:
                self.completed += 1
                self.errors_count += 1
    
    def log(self, message: str):
        """Add a log message"""
        with self.lock:
            self.messages.append(message)
    
    def start(self, name: str):
        """Mark item as running"""
        self.update(name, self.RUNNING, "Processing...")
    
    def success(self, name: str, message: str = "Done"):
        """Mark item as successful"""
        self.update(name, self.SUCCESS, message)
    
    def warn(self, name: str, message: str = "Completed with warnings"):
        """Mark item as completed with warnings"""
        self.update(name, self.WARNING, message)
    
    def error(self, name: str, message: str = "Failed"):
        """Mark item as failed"""
        self.update(name, self.ERROR, message)
    
    def get_progress_bar(self, width: int = 30) -> str:
        """Generate progress bar string"""
        with self.lock:
            if self.total == 0:
                return f"[{'=' * width}] 100%"
            
            progress = self.completed / self.total
            filled = int(width * progress)
            bar = '█' * filled + '░' * (width - filled)
            percent = int(progress * 100)
            return f"[{bar}] {percent}%"
    
    def display(self):
        """Display current progress state"""
        with self.lock:
            elapsed = time.time() - self.start_time
            
            # Header
            print(f"\n{self.BOLD}{'═' * 60}{self.RESET}")
            print(f"{self.BOLD}📦 {self.title}{self.RESET}")
            print(f"{'─' * 60}")
            
            # Progress bar
            progress_bar = self.get_progress_bar(40)
            print(f"\n{progress_bar} ({self.completed}/{self.total} {self.item_type}s)")
            print(f"⏱️  Elapsed: {elapsed:.1f}s | ✅ {self.completed - self.warnings_count - self.errors_count} | ⚠️  {self.warnings_count} | ❌ {self.errors_count}")
            
            # Items status
            print(f"\n{'─' * 60}")
            
            # Group by status
            running = [(n, s, m) for n, (s, m) in self.items.items() if s == self.RUNNING]
            pending = [(n, s, m) for n, (s, m) in self.items.items() if s == self.PENDING]
            done = [(n, s, m) for n, (s, m) in self.items.items() if s in (self.SUCCESS, self.WARNING, self.ERROR)]
            
            # Show running items
            if running:
                for name, status, msg in running[:5]:
                    icon, color = status
                    print(f"  {color}{icon} {name}: {msg}{self.RESET}")
            
            # Show pending count
            if pending:
                print(f"  {self.PENDING[1]}⏳ {len(pending)} {self.item_type}(s) waiting...{self.RESET}")
            
            # Show recent completed
            recent_done = done[-3:] if done else []
            for name, status, msg in recent_done:
                icon, color = status
                print(f"  {color}{icon} {name}: {msg}{self.RESET}")
            
            print(f"{'═' * 60}\n")
    
    def final_summary(self):
        """Display final summary"""
        elapsed = time.time() - self.start_time
        
        print(f"\n{self.BOLD}{'═' * 60}{self.RESET}")
        print(f"{self.BOLD}📊 {self.title} - COMPLETED{self.RESET}")
        print(f"{'─' * 60}")
        print(f"  ⏱️  Total time: {elapsed:.2f}s")
        print(f"  📦 Total {self.item_type}s: {self.total}")
        print(f"  ✅ Successful: {self.completed - self.warnings_count - self.errors_count}")
        print(f"  ⚠️  With warnings: {self.warnings_count}")
        print(f"  ❌ Failed: {self.errors_count}")
        
        # Show all errors and warnings
        errors_warnings = [(n, s, m) for n, (s, m) in self.items.items() if s in (self.WARNING, self.ERROR)]
        if errors_warnings:
            print(f"\n{'─' * 60}")
            print(f"{self.BOLD}Issues:{self.RESET}")
            for name, status, msg in errors_warnings:
                icon, color = status
                print(f"  {color}{icon} {name}: {msg}{self.RESET}")
        
        print(f"{'═' * 60}\n")


class SimpleLogger:
    """Simple thread-safe logger for non-progress messages"""
    
    RESET = '\033[0m'
    COLORS = {
        'debug': '\033[90m',
        'info': '\033[94m',
        'success': '\033[92m',
        'warning': '\033[93m',
        'error': '\033[91m',
    }
    ICONS = {
        'debug': '🔍',
        'info': 'ℹ️ ',
        'success': '✅',
        'warning': '⚠️ ',
        'error': '❌',
    }
    
    def __init__(self, verbose=False):
        self.verbose = verbose
        self.lock = threading.Lock()
    
    def _log(self, level: str, message: str, context: str = None):
        if level == 'debug' and not self.verbose:
            return
        with self.lock:
            color = self.COLORS.get(level, '')
            icon = self.ICONS.get(level, '')
            if context:
                print(f"{color}{icon} [{context}] {message}{self.RESET}", flush=True)
            else:
                print(f"{color}{icon} {message}{self.RESET}", flush=True)
    
    def debug(self, msg, ctx=None): self._log('debug', msg, ctx)
    def info(self, msg, ctx=None): self._log('info', msg, ctx)
    def success(self, msg, ctx=None): self._log('success', msg, ctx)
    def warning(self, msg, ctx=None): self._log('warning', msg, ctx)
    def error(self, msg, ctx=None): self._log('error', msg, ctx)
    def flush(self): pass
    def shutdown(self): pass


# Initialize global logger
logger = SimpleLogger(verbose=args.verbose)

# Global warnings tracker
build_warnings = []
warnings_lock = threading.Lock()

def add_warning(name, warning_type, message, item_type=None):
    """Add a warning to the global warnings list (thread-safe)"""
    warning = {
        "name": name,
        "type": warning_type,
        "message": message
    }
    if item_type:
        warning["item_type"] = item_type
    with warnings_lock:
        build_warnings.append(warning)
    logger.warning(message, name)

# Maximum dimensions for images (width, height)
MAX_IMAGE_WIDTH = 1920
MAX_IMAGE_HEIGHT = 1080
MAX_ICON_SIZE = 512
MIN_ICON_SIZE = 64  # For ESP32-S3 display
JPEG_QUALITY = 85

def generate_min_icon(icon_path, output_path):
    """Generate 64x64 minimized icon for ESP32-S3 in RGB565 binary format"""
    try:
        with Image.open(icon_path) as img:
            # Convert to RGB if needed
            if img.mode in ('RGBA', 'LA', 'P'):
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                if img.mode in ('RGBA', 'LA'):
                    background.paste(img, mask=img.split()[-1])
                else:
                    background.paste(img)
                img = background
            elif img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Resize to 64x64
            img_resized = img.resize((MIN_ICON_SIZE, MIN_ICON_SIZE), Image.Resampling.LANCZOS)
            
            # Convert to RGB565 binary format
            pixels = img_resized.load()
            rgb565_data = bytearray()
            
            for y in range(MIN_ICON_SIZE):
                for x in range(MIN_ICON_SIZE):
                    r, g, b = pixels[x, y]
                    # Convert RGB888 to RGB565
                    r5 = (r >> 3) & 0x1F
                    g6 = (g >> 2) & 0x3F
                    b5 = (b >> 3) & 0x1F
                    rgb565 = (r5 << 11) | (g6 << 5) | b5
                    # Write as little-endian 16-bit value
                    rgb565_data.append(rgb565 & 0xFF)
                    rgb565_data.append((rgb565 >> 8) & 0xFF)
            
            # Save binary file
            with open(output_path, 'wb') as f:
                f.write(rgb565_data)
            
            logger.debug(f"Generated min icon: {output_path} (64x64 RGB565, {len(rgb565_data)} bytes)")
    except Exception as e:
        logger.warning(f"Could not generate min icon: {e}")

def compress_image(image_path, max_width=MAX_IMAGE_WIDTH, max_height=MAX_IMAGE_HEIGHT, quality=JPEG_QUALITY):
    """Compress and resize image if it's too large"""
    try:
        with Image.open(image_path) as img:
            # Get original size
            original_size = os.path.getsize(image_path)
            width, height = img.size
            
            # Check if image needs resizing
            if width > max_width or height > max_height:
                logger.debug(f"Resizing image from {width}x{height} to fit {max_width}x{max_height}")
                # Calculate new dimensions maintaining aspect ratio
                img.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
                
                # Save compressed image
                if image_path.lower().endswith('.png'):
                    img.save(image_path, 'PNG', optimize=True)
                else:
                    # Convert to RGB if needed (for JPEG)
                    if img.mode in ('RGBA', 'LA', 'P'):
                        background = Image.new('RGB', img.size, (255, 255, 255))
                        if img.mode == 'P':
                            img = img.convert('RGBA')
                        background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
                        img = background
                    img.save(image_path, 'JPEG', quality=quality, optimize=True)
                
                new_size = os.path.getsize(image_path)
                logger.debug(f"Compressed: {original_size} bytes -> {new_size} bytes ({100 - int(new_size/original_size*100)}% reduction)")
            elif original_size > 500 * 1024:  # If larger than 500KB, optimize anyway
                logger.debug(f"Optimizing large image ({original_size} bytes)")
                if image_path.lower().endswith('.png'):
                    img.save(image_path, 'PNG', optimize=True)
                else:
                    if img.mode in ('RGBA', 'LA', 'P'):
                        background = Image.new('RGB', img.size, (255, 255, 255))
                        if img.mode == 'P':
                            img = img.convert('RGBA')
                        background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
                        img = background
                    img.save(image_path, 'JPEG', quality=quality, optimize=True)
                
                new_size = os.path.getsize(image_path)
                logger.debug(f"Compressed: {original_size} bytes -> {new_size} bytes ({100 - int(new_size/original_size*100)}% reduction)")
    except Exception as e:
        logger.warning(f"Could not compress image {image_path}: {e}")

def download_file(path, output_dir) -> str:
    url = path['origin'] if isinstance(path, dict) else path
    response = requests.head(url)

    filename = url.split('/')[-1]
    output_path = os.path.join(output_dir, filename)

    if response.status_code == 404:
        raise FileNotFoundError(f"File not found: {url}")
    if(args.build):
        logger.debug(f"Downloading {url}")
        os.system(f"wget -q '{url}' -O '{output_path}'")

    return filename

def gen_static_folder(manifest, type, output_dir) -> dict:
    static_files_path = output_dir+"/static"

    os.makedirs(static_files_path, exist_ok=True)

    path_to_modapp = type+"s/"+manifest['path']
    
    # Collect all download tasks
    download_tasks = []
    
    # Handle entryfile (main execution file) - new format
    if type == "app" and manifest.get('entryfile'):
        download_tasks.append(('entryfile', manifest['entryfile']['location'], static_files_path))
    # Handle executionfile (legacy format) - keep for backwards compatibility
    elif type == "app" and manifest.get('executionfile'):
        download_tasks.append(('executionfile', manifest['executionfile']['location'], static_files_path))
    
    # Handle additional files
    if manifest.get('files'):
        for i, file in enumerate(manifest['files']):
            if file.get('location'):
                download_tasks.append((f'file_{i}', file['location'], static_files_path))
    
    # Handle modfiles for mods
    if type == "mod" and manifest.get('modfiles'):
        for i, file in enumerate(manifest['modfiles']):
            download_tasks.append((f'modfile_{i}', file['location'], static_files_path))
    
    # Execute downloads in parallel
    if download_tasks:
        download_results = {}
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {executor.submit(download_file, task[1], task[2]): task[0] for task in download_tasks}
            for future in as_completed(futures):
                task_id = futures[future]
                try:
                    download_results[task_id] = future.result()
                except Exception as e:
                    logger.warning(f"Failed to download {task_id}: {e}")
        
        # Update manifest with downloaded filenames
        if 'entryfile' in download_results:
            manifest['entryfile']['location'] = download_results['entryfile']
        elif 'executionfile' in download_results:
            manifest['executionfile']['location'] = download_results['executionfile']
        
        if manifest.get('files'):
            for i, file in enumerate(manifest['files']):
                if f'file_{i}' in download_results:
                    file['location'] = download_results[f'file_{i}']
        
        if type == "mod" and manifest.get('modfiles'):
            for i, file in enumerate(manifest['modfiles']):
                if f'modfile_{i}' in download_results:
                    file['location'] = download_results[f'modfile_{i}']

    # Process screenshots in parallel
    def process_screenshot(screenshot):
        try:
            if screenshot.startswith('https://') or screenshot.startswith('http://'):
                download_file(screenshot, static_files_path)
            else:
                source_path = os.path.join(path_to_modapp, screenshot)
                dest_path = os.path.join(static_files_path, screenshot)
                if os.path.exists(source_path):
                    os.system(f"cp '{source_path}' '{dest_path}'")
                    if os.path.exists(dest_path):
                        compress_image(dest_path, MAX_IMAGE_WIDTH, MAX_IMAGE_HEIGHT)
                else:
                    logger.warning(f"Screenshot not found, skipping: {screenshot}")
        except Exception as e:
            logger.warning(f"Failed to process screenshot {screenshot}: {str(e)}")
    
    if manifest.get('screenshots'):
        with ThreadPoolExecutor(max_workers=4) as executor:
            executor.map(process_screenshot, manifest['screenshots'])
    
    # Copy and compress icon
    if manifest.get('icon'):
        try:
            if manifest['icon'].startswith('https://') or manifest['icon'].startswith('http://'):
                download_file(manifest['icon'], static_files_path)
                icon_dest_path = os.path.join(static_files_path, manifest['icon'].split('/')[-1])
            else:
                source_path = os.path.join(path_to_modapp, manifest['icon'])
                dest_path = os.path.join(static_files_path, manifest['icon'])
                if os.path.exists(source_path):
                    os.system(f"cp '{source_path}' '{dest_path}'")
                    icon_dest_path = dest_path
                    # Compress the icon (smaller size for icons)
                    if os.path.exists(dest_path):
                        compress_image(dest_path, MAX_ICON_SIZE, MAX_ICON_SIZE)
                else:
                    logger.warning(f"Icon not found, skipping: {manifest['icon']}")
                    icon_dest_path = None
            
            # Generate minimized 64x64 icon for ESP32-S3 in RGB565 format
            if icon_dest_path and os.path.exists(icon_dest_path):
                icon_name = os.path.splitext(manifest['icon'])[0]
                min_icon_name = f"{icon_name}_min.bin"
                min_icon_path = os.path.join(static_files_path, min_icon_name)
                generate_min_icon(icon_dest_path, min_icon_path)
                manifest['icon_min'] = min_icon_name
        except Exception as e:
            logger.warning(f"Failed to process icon: {str(e)}")

    return manifest

def process_manifest(manifest, type) -> None:
    output_dir = os.path.join("./build", type+"s", manifest['path'])

    if args.build:
        os.makedirs("./build", exist_ok=True)
        os.makedirs(output_dir, exist_ok=True)
        
        manifest = gen_static_folder(manifest, type, output_dir)

        if type == "app":
            short_data = {
                "name": manifest["name"],
                "short_description": manifest["short_description"]
            }
            # Include entryfile if it exists (new format)
            if manifest.get("entryfile"):
                short_data["entryfile"] = manifest["entryfile"]
            # Include executionfile if it exists (legacy format)
            elif manifest.get("executionfile"):
                short_data["entryfile"] = manifest["executionfile"]  # Map to entryfile for consistency
            
            with open(os.path.join(output_dir, 'index_short.json'), 'w', encoding='utf-8') as file:
                json.dump(short_data, file, indent=2, ensure_ascii=False)
            
        full_data = {
            "name": manifest["name"],
            "description": manifest["description"],
            "short_description": manifest["short_description"],
            "author": manifest["author"],
            "sources": manifest["sources"],
            "screenshots": manifest.get("screenshots", [])
        }
        
        # Only include icon if it exists
        if manifest.get("icon"):
            full_data["icon"] = manifest["icon"]
        
        # Include minimized icon for ESP32-S3 if it exists
        if manifest.get("icon_min"):
            full_data["icon_min"] = manifest["icon_min"]
        
        # Only include changelog if it exists and is not empty
        if manifest.get("changelog"):
            full_data["changelog"] = manifest["changelog"]
        
        if type == "app":
            # Include entryfile if it exists (new format)
            if manifest.get("entryfile"):
                full_data["entryfile"] = manifest["entryfile"]
            # Include executionfile if it exists (legacy format) - map to entryfile
            elif manifest.get("executionfile"):
                full_data["entryfile"] = manifest["executionfile"]
            
            # Include additional files if they exist
            if manifest.get("files"):
                full_data["files"] = manifest["files"]
        elif type == "mod":
            # Only include modfiles if they exist
            if manifest.get("modfiles"):
                full_data["modfiles"] = manifest["modfiles"]
        
        with open(os.path.join(output_dir, 'index.json'), 'w', encoding='utf-8') as file:
            json.dump(full_data, file, indent=2, ensure_ascii=False)


def gen_json_index_manifests(manifests, type) -> None:
    jsons_per_page = 12
    page = 1
    jsons = []
    pages = len(manifests) // jsons_per_page
    if len(manifests) % jsons_per_page != 0:
        pages += 1
    output_dir = os.path.join("./build", type+"s")
    os.makedirs(output_dir, exist_ok=True)
    for i in range(0, pages):
        with open(os.path.join("./build", type+"s", f"index_{i}.json"), 'w') as file:
            file.write('{\n')
            file.write(f'  "page": {i},\n')
            file.write(f'  "total_pages": {pages},\n')
            file.write(f'  "manifests": [\n')
            page_manifests = []
            for j in range(0, jsons_per_page):
                if i*jsons_per_page+j >= len(manifests):
                    break
                page_manifests.append(f'    "{manifests[i*jsons_per_page+j]}"')
            file.write(',\n'.join(page_manifests) + '\n')
            file.write('  ]\n')
            file.write('}\n')
        

def check_folder_sturcture(folder) -> bool:
    return os.path.isfile(os.path.join(folder, 'manifest.yml'))

def infer_type_from_extension(filename: str) -> str:
    """Infer the expected entryfile type from the file extension.
    
    Returns:
        'lua' for .lua files
        'archive' for .zip, .tar, .tar.gz, .tgz files
        'binary' for .bin files
        None if extension is unknown
    """
    filename_lower = filename.lower()
    if filename_lower.endswith('.lua'):
        return 'lua'
    elif filename_lower.endswith(('.zip', '.tar', '.tar.gz', '.tgz')):
        return 'archive'
    elif filename_lower.endswith('.bin'):
        return 'binary'
    return None

def validate_entryfile_type(src, entryfile: dict, item_type: str) -> None:
    """Validate that the declared entryfile type matches the actual file extension.
    
    Args:
        src: The source app/mod name for warning messages
        entryfile: The entryfile dict containing 'type' and 'location'
        item_type: 'app' or 'mod'
    """
    if not entryfile:
        return
    
    declared_type = entryfile.get('type')
    location = entryfile.get('location')
    
    if not declared_type or not location:
        return
    
    # Handle location as dict with 'origin' or as plain string
    if isinstance(location, dict):
        filename = location.get('origin', '')
    else:
        filename = str(location)
    
    # Get the filename from URL or path
    if filename:
        filename = filename.split('/')[-1].split('?')[0]  # Handle URLs with query params
    
    inferred_type = infer_type_from_extension(filename)
    
    if inferred_type and inferred_type != declared_type:
        add_warning(
            src, 
            "type_mismatch", 
            f"Entryfile type mismatch: declared '{declared_type}' but file '{filename}' suggests '{inferred_type}'",
            item_type
        )

def validate_app_files(src, manifest, type) -> bool:
    """Validate that all required files exist. Returns True if valid, False otherwise.
    Only returns False for critical errors that should skip the app/mod.
    Uses parallel HTTP requests for faster validation."""
    path_to_app = os.path.join(type + "s", src)
    is_valid = True
    validation_results = {'is_valid': True}
    results_lock = threading.Lock()
    
    logger.debug(f"Validating files...", src)
    
    # Validate entryfile type matches file extension
    if type == "app":
        entryfile = manifest.get('entryfile') or manifest.get('executionfile')
        validate_entryfile_type(src, entryfile, type)
    
    # Local file checks (fast, no need to parallelize)
    if manifest.get('icon'):
        icon_path = os.path.join(path_to_app, manifest['icon'])
        if not os.path.exists(icon_path) and not (manifest['icon'].startswith('http://') or manifest['icon'].startswith('https://')):
            add_warning(src, "missing_icon", f"Icon file not found: {manifest['icon']}", type)
    
    if manifest.get('screenshots'):
        for screenshot in manifest['screenshots']:
            if not (screenshot.startswith('http://') or screenshot.startswith('https://')):
                screenshot_path = os.path.join(path_to_app, screenshot)
                if not os.path.exists(screenshot_path):
                    add_warning(src, "missing_screenshot", f"Screenshot file not found: {screenshot}", type)
    
    # Collect HTTP validation tasks
    http_tasks = []
    
    if manifest.get('sources'):
        sources = manifest['sources']
        if isinstance(sources, dict) and sources.get('location', {}).get('origin'):
            repo_url = sources['location']['origin']
            if 'github.com' in repo_url:
                http_tasks.append(('repo', repo_url, True))  # (type, url, is_critical)
    
    if type == "app" and manifest.get('executionfile'):
        exec_file = manifest['executionfile']
        if isinstance(exec_file, dict) and exec_file.get('location'):
            location = exec_file['location']
            if isinstance(location, dict) and location.get('origin'):
                exec_url = location['origin']
                http_tasks.append(('exec', exec_url, False))  # Not critical
    
    def check_url(task):
        task_type, url, is_critical = task
        try:
            response = requests.head(url, timeout=5)
            if response.status_code == 404:
                if task_type == 'repo':
                    add_warning(src, "repo_not_found", f"Repository not found: {url}", type)
                    if is_critical:
                        with results_lock:
                            validation_results['is_valid'] = False
                elif task_type == 'exec':
                    add_warning(src, "exec_file_not_found", f"Execution file not found: {url}", type)
        except Exception as e:
            if task_type == 'repo':
                add_warning(src, "repo_check_failed", f"Could not verify repository: {str(e)}", type)
            elif task_type == 'exec':
                add_warning(src, "exec_file_check_failed", f"Could not verify execution file: {str(e)}", type)
    
    # Execute HTTP checks in parallel
    if http_tasks:
        with ThreadPoolExecutor(max_workers=4) as executor:
            executor.map(check_url, http_tasks)
    
    return validation_results['is_valid']

def check_manifest(src, type) -> dict:
    manifest_path = os.path.join(type+"s", src, 'manifest.yml')
    logger.debug(f"Reading {manifest_path}", src)
    
    try:
        with open(manifest_path, 'r') as file:
            manifest = yaml.safe_load(file)
    except Exception as e:
        add_warning(src, "manifest_error", f"Failed to read manifest.yml: {str(e)}", type)
        return None
    
    if 'name' in manifest:
        logger.debug(f"Name: {manifest['name']}", src)
    else:
        add_warning(src, "missing_field", "Name not found in manifest file", type)
        return None
    
    if type == "app":
        if 'keira_version' in manifest:
            logger.debug(f"keira_version: {manifest['keira_version']}", src)
        else:
            add_warning(src, "missing_field", "keira_version not found in manifest file", type)
            return None

    if 'description' in manifest:
        if manifest['description'][0] == '@':
            try:
                manifest['description'] = open(os.path.join(type+"s", src, manifest['description'][1:]), 'r').read()
            except Exception as e:
                add_warning(src, "file_read_error", f"Failed to read description file: {str(e)}", type)
                manifest['description'] = ""
    else:
        manifest['description'] = ""
    
    if 'short_description' in manifest:
        if manifest['short_description'][0] == '@':
            try:
                manifest['short_description'] = open(os.path.join(type+"s", src, manifest['short_description'][1:]), 'r').read()
            except Exception as e:
                add_warning(src, "file_read_error", f"Failed to read short_description file: {str(e)}", type)
                return None
    else:
        add_warning(src, "missing_field", "Short Description not found in manifest file", type)
        return None
    
    if 'changelog' in manifest:
        if(manifest['changelog'][0] == '@'):
            try:
                manifest['changelog'] = open(os.path.join(type+"s", src, manifest['changelog'][1:]), 'r').read()
            except Exception as e:
                add_warning(src, "file_read_error", f"Failed to read changelog file: {str(e)}", type)
                manifest['changelog'] = ""
    else:
        manifest['changelog'] = ""

    if 'author' not in manifest:
        add_warning(src, "missing_field", "Author not found in manifest file", type)
        return None
    
    if 'icon' not in manifest:
        add_warning(src, "missing_field", "Icon not found in manifest file (optional)", type)
        # Don't return None - icon is now optional
    
    if 'sources' in manifest:
        if 'type' not in manifest['sources']:
            add_warning(src, "missing_field", "sources type not found in manifest file", type)
            return None
        if 'location' in manifest['sources']:
            if 'origin' not in manifest['sources']['location']:
                add_warning(src, "missing_field", "sources origin not found in manifest file", type)
                return None
        else:
            add_warning(src, "missing_field", "sources location not found in manifest file", type)
            return None
    else:
        add_warning(src, "missing_field", "sources not found in manifest file", type)
        return None
    
    if type == "app":
        # Check for entryfile (new format) or executionfile (legacy)
        if 'entryfile' not in manifest and 'executionfile' not in manifest:
            add_warning(src, "missing_field", "entryfile/executionfile not found in manifest file (optional)", type)
    elif type == "mod":
        if 'modfiles' not in manifest:
            add_warning(src, "missing_field", "modfiles not found in manifest file (optional)", type)
            manifest['modfiles'] = []
    else:
        add_warning(src, "unknown_type", f"Unknown type: {type}", type)
        return None
    
    # Validate all files exist
    if not validate_app_files(src, manifest, type):
        return None
    
    manifest['path'] = src.split('/')[-1]

    return manifest
        

def scan_apps_folder() -> list[str]:
    folders_list = [d for d in os.listdir('./apps') if os.path.isdir(os.path.join('./apps', d))]
    folders_list = sorted(folders_list)
    return folders_list

def scan_mods_folder() -> list[str]:
    folder_list = [d for d in os.listdir('./mods') if os.path.isdir(os.path.join('./mods', d))]
    folder_list = sorted(folder_list)
    return folder_list

def process_apps_folder(apps):
    """Process apps in parallel with progress tracking"""
    results = []
    progress = ProgressTracker("Processing Apps", len(apps), "app")
    
    # Initialize all items
    for app in apps:
        progress.add_item(app)
    
    def process_single_app(app):
        progress.start(app)
        try:
            if check_folder_sturcture(os.path.join('./apps', app)):
                manifest = check_manifest(app, 'app')
                if manifest is not None:
                    process_manifest(manifest, 'app')
                    # Check if there were warnings for this app
                    app_warnings = [w for w in build_warnings if w.get('name') == app]
                    if app_warnings:
                        progress.warn(app, f"Done with {len(app_warnings)} warning(s)")
                    else:
                        progress.success(app, "Built successfully")
                    return app
                else:
                    progress.error(app, "Validation failed")
                    return None
            else:
                add_warning(app, "missing_manifest", "manifest.yml file not found", "app")
                progress.error(app, "manifest.yml not found")
                return None
        except Exception as e:
            progress.error(app, f"Error: {str(e)[:30]}")
            return None
    
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {executor.submit(process_single_app, app): app for app in apps}
        for future in as_completed(futures):
            app = futures[future]
            try:
                result = future.result()
                if result:
                    results.append(result)
            except Exception as e:
                progress.error(app, f"Exception: {str(e)[:30]}")
    
    progress.final_summary()
    return sorted(results)
        
def process_mods_folder(mods):
    """Process mods in parallel with progress tracking"""
    results = []
    progress = ProgressTracker("Processing Mods", len(mods), "mod")
    
    # Initialize all items
    for mod in mods:
        progress.add_item(mod)
    
    def process_single_mod(mod):
        progress.start(mod)
        try:
            if check_folder_sturcture(os.path.join('./mods', mod)):
                manifest = check_manifest(mod, 'mod')
                if manifest is not None:
                    process_manifest(manifest, 'mod')
                    # Check if there were warnings for this mod
                    mod_warnings = [w for w in build_warnings if w.get('name') == mod]
                    if mod_warnings:
                        progress.warn(mod, f"Done with {len(mod_warnings)} warning(s)")
                    else:
                        progress.success(mod, "Built successfully")
                    return mod
                else:
                    progress.error(mod, "Validation failed")
                    return None
            else:
                add_warning(mod, "missing_manifest", "manifest.yml file not found", "mod")
                progress.error(mod, "manifest.yml not found")
                return None
        except Exception as e:
            progress.error(mod, f"Error: {str(e)[:30]}")
            return None
    
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {executor.submit(process_single_mod, mod): mod for mod in mods}
        for future in as_completed(futures):
            mod = futures[future]
            try:
                result = future.result()
                if result:
                    results.append(result)
            except Exception as e:
                progress.error(mod, f"Exception: {str(e)[:30]}")
    
    progress.final_summary()
    return sorted(results)
        
def main():
    start_time = time.time()
    
    # Header
    print(f"\n\033[1m{'═' * 60}\033[0m")
    print(f"\033[1m🚀 LILKA CATALOG BUILD SYSTEM\033[0m")
    print(f"\033[1m{'═' * 60}\033[0m")
    print(f"  📅 Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  👷 Workers: {args.workers}")
    print(f"  🔧 Build mode: {'FULL BUILD' if args.build else 'VALIDATION ONLY'}")
    print(f"{'─' * 60}\n")
    
    apps: list[str] = scan_apps_folder()
    mods: list[str] = scan_mods_folder()

    print(f"📱 Found \033[1m{len(apps)}\033[0m apps")
    print(f"🔩 Found \033[1m{len(mods)}\033[0m mods\n")

    # Process in parallel and get successfully processed items
    processed_apps = process_apps_folder(apps)
    processed_mods = process_mods_folder(mods)

    if args.build:
        print(f"\n\033[94mℹ️  Generating index files...\033[0m")
        gen_json_index_manifests(processed_apps, "app")
        gen_json_index_manifests(processed_mods, "mod")
        print(f"\033[92m✅ Index files generated\033[0m")
    
    # Write warnings to JSON file
    warnings_data = {
        "build_date": datetime.now().isoformat(),
        "total_warnings": len(build_warnings),
        "warnings": build_warnings
    }
    
    os.makedirs("./build", exist_ok=True)
    with open("./build/warnings.json", 'w') as f:
        json.dump(warnings_data, f, indent=2)
    
    elapsed_time = time.time() - start_time
    
    # Final Summary
    print(f"\n\033[1m{'═' * 60}\033[0m")
    print(f"\033[1m📊 BUILD SUMMARY\033[0m")
    print(f"{'─' * 60}")
    print(f"  ⏱️  Total time: \033[1m{elapsed_time:.2f}s\033[0m")
    print(f"  📱 Apps processed: \033[92m{len(processed_apps)}\033[0m / {len(apps)}")
    print(f"  🔩 Mods processed: \033[92m{len(processed_mods)}\033[0m / {len(mods)}")
    print(f"  ⚠️  Total warnings: \033[93m{len(build_warnings)}\033[0m")
    print(f"  📄 Warnings file: build/warnings.json")
    print(f"\033[1m{'═' * 60}\033[0m\n")

if __name__ == '__main__': 
    main()
