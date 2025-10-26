"""JavaScript wrapper management for subprocess execution and communication."""

import asyncio
import json
import shutil
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

from .exceptions import JSWrapperError, ConfigurationError
from .error_handler import (
    with_error_handling,
    handle_subprocess_error,
)
from .logging_config import get_logger


logger = get_logger(__name__)


class JSWrapperManager:
    """Manages JavaScript subprocess execution and communication."""

    def __init__(self, js_script_path: Optional[str] = None) -> None:
        """Initialize JavaScript wrapper manager.

        Args:
            js_script_path: Path to the JavaScript implementation script.
                          If None, will attempt to locate automatically.
        """
        self.js_script_path = js_script_path
        self._nodejs_path: Optional[str] = None
        self._nodejs_version: Optional[str] = None
        self._validated = False

    async def validate_environment(self) -> None:
        """Validate Node.js environment and JavaScript script availability.

        Raises:
            JSWrapperError: If Node.js is not available or version is incompatible
            ConfigurationError: If JavaScript script cannot be found
        """
        if self._validated:
            return

        # Validate Node.js availability
        await self._validate_nodejs()

        # Validate JavaScript script path
        self._validate_js_script_path()

        self._validated = True
        logger.info(
            f"JavaScript environment validated: Node.js {self._nodejs_version} at {self._nodejs_path}"
        )

    @with_error_handling(
        "javascript_migration",
        error_types=(JSWrapperError, OSError, asyncio.TimeoutError),
    )
    async def execute_migration(
        self,
        s3_config: Dict[str, Any],
        storacha_config: Dict[str, Any],
        migration_params: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Execute migration via JavaScript subprocess.

        Args:
            s3_config: S3 configuration dictionary
            storacha_config: Storacha configuration dictionary
            migration_params: Migration parameters dictionary

        Returns:
            Dictionary containing migration results

        Raises:
            JSWrapperError: If subprocess execution fails
            ConfigurationError: If environment is not properly configured
        """
        await self.validate_environment()

        # Prepare input data for JavaScript process
        input_data = {
            "s3": s3_config,
            "storacha": storacha_config,
            "migration": migration_params,
        }

        logger.debug(f"Executing JavaScript migration with params: {migration_params}")

        # Execute JavaScript subprocess
        result = await self._execute_js_subprocess(input_data)

        logger.info("JavaScript migration completed successfully")
        return result

    async def _execute_js_subprocess(
        self, input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute JavaScript subprocess with JSON communication.

        Args:
            input_data: Data to send to JavaScript process via stdin

        Returns:
            Parsed JSON response from JavaScript process

        Raises:
            JSWrapperError: If subprocess execution fails or returns invalid data
        """
        if not self._nodejs_path or not self.js_script_path:
            raise JSWrapperError("JavaScript environment not properly validated")

        # Prepare command
        cmd = [self._nodejs_path, str(self.js_script_path)]
        input_json = json.dumps(input_data)

        logger.debug(f"Executing command: {' '.join(cmd)}")

        try:
            # Create subprocess
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=Path(self.js_script_path).parent if self.js_script_path else None,
            )

            # Communicate with subprocess
            stdout_data, stderr_data = await process.communicate(
                input_json.encode("utf-8")
            )

            # Decode output
            stdout = stdout_data.decode("utf-8") if stdout_data else ""
            stderr = stderr_data.decode("utf-8") if stderr_data else ""

            logger.debug(f"Process return code: {process.returncode}")
            if stderr:
                logger.debug(f"Process stderr: {stderr}")

            # Check return code
            if process.returncode != 0:
                raise handle_subprocess_error(
                    returncode=process.returncode, stderr=stderr, command=" ".join(cmd)
                )

            # Parse JSON response
            try:
                result = json.loads(stdout)
                return result
            except json.JSONDecodeError as e:
                raise JSWrapperError(
                    f"Invalid JSON response from JavaScript process: {e}",
                    context={"stdout": stdout[:500], "stderr": stderr[:500]},
                    original_error=e,
                )

        except asyncio.TimeoutError as e:
            raise JSWrapperError(
                "JavaScript subprocess execution timed out", original_error=e
            )
        except OSError as e:
            raise JSWrapperError(
                f"Failed to execute JavaScript subprocess: {e}", original_error=e
            )

    async def _validate_nodejs(self) -> None:
        """Validate Node.js availability and version.

        Raises:
            JSWrapperError: If Node.js is not available or version is incompatible
        """
        # Try to find Node.js executable
        nodejs_candidates = ["node", "nodejs"]

        for candidate in nodejs_candidates:
            nodejs_path = shutil.which(candidate)
            if nodejs_path:
                self._nodejs_path = nodejs_path
                break

        if not self._nodejs_path:
            raise JSWrapperError(
                "Node.js not found. Please install Node.js to use this library.",
                context={
                    "installation_guide": "Visit https://nodejs.org/ for installation instructions",
                    "searched_executables": nodejs_candidates,
                },
            )

        # Check Node.js version
        try:
            process = await asyncio.create_subprocess_exec(
                self._nodejs_path,
                "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout_data, stderr_data = await process.communicate()

            if process.returncode != 0:
                stderr = stderr_data.decode("utf-8") if stderr_data else ""
                raise JSWrapperError(
                    f"Failed to get Node.js version: {stderr}",
                    return_code=process.returncode,
                )

            version_output = stdout_data.decode("utf-8").strip()
            self._nodejs_version = version_output

            # Basic version validation (Node.js versions start with 'v')
            if not version_output.startswith("v"):
                raise JSWrapperError(
                    f"Unexpected Node.js version format: {version_output}",
                    context={"expected_format": "v<major>.<minor>.<patch>"},
                )

            # Extract major version for compatibility check
            try:
                major_version = int(version_output[1:].split(".")[0])
                if major_version < 14:
                    logger.warning(
                        f"Node.js version {version_output} may not be fully supported. "
                        "Recommended version is 14 or higher."
                    )
            except (ValueError, IndexError):
                logger.warning(f"Could not parse Node.js version: {version_output}")

        except OSError as e:
            raise JSWrapperError(
                f"Failed to execute Node.js version check: {e}", original_error=e
            )

    def _validate_js_script_path(self) -> None:
        """Validate JavaScript script path availability.

        Raises:
            ConfigurationError: If JavaScript script cannot be found or accessed
        """
        if not self.js_script_path:
            # Try to auto-detect JavaScript script in common locations
            possible_paths = [
                Path(__file__).parent / "js" / "s3-to-storacha.js",
                Path(__file__).parent.parent.parent / "js" / "s3-to-storacha.js",
                Path.cwd() / "js" / "s3-to-storacha.js",
                Path.cwd() / "s3-to-storacha.js",
            ]

            for path in possible_paths:
                if path.exists() and path.is_file():
                    self.js_script_path = str(path)
                    break

            if not self.js_script_path:
                raise ConfigurationError(
                    "JavaScript script not found. Please specify js_script_path or ensure "
                    "the JavaScript implementation is available in a standard location.",
                    context={
                        "searched_paths": [str(p) for p in possible_paths],
                        "config_field": "js_script_path",
                    },
                )

        # Validate the specified or found path
        script_path = Path(self.js_script_path)

        if not script_path.exists():
            raise ConfigurationError(
                f"JavaScript script not found at specified path: {self.js_script_path}",
                field_name="js_script_path",
                field_value=self.js_script_path,
            )

        if not script_path.is_file():
            raise ConfigurationError(
                f"JavaScript script path is not a file: {self.js_script_path}",
                field_name="js_script_path",
                field_value=self.js_script_path,
            )

        if script_path.suffix.lower() not in [".js", ".mjs"]:
            logger.warning(
                f"JavaScript script does not have a .js or .mjs extension: {self.js_script_path}"
            )


def validate_nodejs_environment() -> Tuple[str, str]:
    """Validate Node.js environment synchronously.

    Returns:
        Tuple of (nodejs_path, nodejs_version)

    Raises:
        JSWrapperError: If Node.js is not available
    """
    # Try to find Node.js executable
    nodejs_candidates = ["node", "nodejs"]
    nodejs_path = None

    for candidate in nodejs_candidates:
        path = shutil.which(candidate)
        if path:
            nodejs_path = path
            break

    if not nodejs_path:
        raise JSWrapperError(
            "Node.js not found. Please install Node.js to use this library.",
            context={
                "installation_guide": "Visit https://nodejs.org/ for installation instructions",
                "searched_executables": nodejs_candidates,
            },
        )

    # Check Node.js version
    try:
        result = subprocess.run(
            [nodejs_path, "--version"], capture_output=True, text=True, timeout=10
        )

        if result.returncode != 0:
            raise JSWrapperError(
                f"Failed to get Node.js version: {result.stderr}",
                return_code=result.returncode,
            )

        version = result.stdout.strip()

        # Basic version validation
        if not version.startswith("v"):
            raise JSWrapperError(
                f"Unexpected Node.js version format: {version}",
                context={"expected_format": "v<major>.<minor>.<patch>"},
            )

        return nodejs_path, version

    except subprocess.TimeoutExpired:
        raise JSWrapperError("Node.js version check timed out")
    except OSError as e:
        raise JSWrapperError(
            f"Failed to execute Node.js version check: {e}", original_error=e
        )


def find_js_script(script_name: str = "s3-to-storacha.js") -> Optional[str]:
    """Find JavaScript script in common locations.

    Args:
        script_name: Name of the JavaScript script to find

    Returns:
        Path to the JavaScript script if found, None otherwise
    """
    possible_paths = [
        Path(__file__).parent / "js" / script_name,
        Path(__file__).parent.parent.parent / "js" / script_name,
        Path.cwd() / "js" / script_name,
        Path.cwd() / script_name,
    ]

    for path in possible_paths:
        if path.exists() and path.is_file():
            return str(path)

    return None
