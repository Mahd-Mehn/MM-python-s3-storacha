"""Setup helpers for installing JavaScript dependencies and managing authentication."""

import subprocess
import sys
import shutil
from pathlib import Path
from typing import Optional, Tuple
import logging

logger = logging.getLogger(__name__)


def check_nodejs_installed() -> Tuple[bool, Optional[str]]:
    """Check if Node.js is installed and get version.
    
    Returns:
        Tuple of (is_installed, version_string)
    """
    try:
        result = subprocess.run(
            ["node", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            version = result.stdout.strip()
            return True, version
        return False, None
    except (subprocess.SubprocessError, FileNotFoundError):
        return False, None


def check_npm_installed() -> Tuple[bool, Optional[str]]:
    """Check if npm is installed and get version.
    
    Returns:
        Tuple of (is_installed, version_string)
    """
    try:
        result = subprocess.run(
            ["npm", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            version = result.stdout.strip()
            return True, version
        return False, None
    except (subprocess.SubprocessError, FileNotFoundError):
        return False, None


def get_js_directory() -> Path:
    """Get the JavaScript implementation directory.
    
    Returns:
        Path to the js directory
    """
    return Path(__file__).parent / "js"


def check_js_dependencies_installed() -> bool:
    """Check if JavaScript dependencies are installed.
    
    Returns:
        True if node_modules exists and has packages
    """
    js_dir = get_js_directory()
    node_modules = js_dir / "node_modules"
    
    if not node_modules.exists():
        return False
    
    # Check for key dependencies
    required_packages = ["@storacha/client", "@aws-sdk/client-s3"]
    for package in required_packages:
        # Handle scoped packages (e.g., @storacha/client)
        package_path = package.replace("/", str(Path("/")))
        package_dir = node_modules / package_path
        if not package_dir.exists():
            return False
    
    return True


def install_js_dependencies(force: bool = False) -> bool:
    """Install JavaScript dependencies using npm.
    
    Args:
        force: If True, reinstall even if already installed
        
    Returns:
        True if installation successful
        
    Raises:
        RuntimeError: If Node.js/npm not available or installation fails
    """
    # Check if already installed
    if not force and check_js_dependencies_installed():
        logger.info("JavaScript dependencies already installed")
        return True
    
    # Check Node.js
    node_installed, node_version = check_nodejs_installed()
    if not node_installed:
        raise RuntimeError(
            "Node.js is not installed. Please install Node.js 18+ from:\n"
            "  - https://nodejs.org\n"
            "  - Or use: brew install node (macOS)\n"
            "  - Or use: apt install nodejs (Ubuntu/Debian)"
        )
    
    logger.info(f"Found Node.js {node_version}")
    
    # Check npm
    npm_installed, npm_version = check_npm_installed()
    if not npm_installed:
        raise RuntimeError(
            "npm is not installed. Please install npm:\n"
            "  - Usually comes with Node.js\n"
            "  - Or install separately: https://www.npmjs.com/get-npm"
        )
    
    logger.info(f"Found npm {npm_version}")
    
    # Install dependencies
    js_dir = get_js_directory()
    
    if not js_dir.exists():
        raise RuntimeError(f"JavaScript directory not found: {js_dir}")
    
    package_json = js_dir / "package.json"
    if not package_json.exists():
        raise RuntimeError(f"package.json not found: {package_json}")
    
    logger.info("Installing JavaScript dependencies...")
    logger.info(f"Running: npm install in {js_dir}")
    
    try:
        result = subprocess.run(
            ["npm", "install"],
            cwd=str(js_dir),
            capture_output=True,
            text=True,
            timeout=300  # 5 minutes timeout
        )
        
        if result.returncode != 0:
            raise RuntimeError(
                f"npm install failed:\n"
                f"stdout: {result.stdout}\n"
                f"stderr: {result.stderr}"
            )
        
        logger.info("JavaScript dependencies installed successfully")
        return True
        
    except subprocess.TimeoutExpired:
        raise RuntimeError("npm install timed out after 5 minutes")
    except Exception as e:
        raise RuntimeError(f"Failed to install JavaScript dependencies: {e}")


def verify_installation() -> dict:
    """Verify the complete installation.
    
    Returns:
        Dictionary with installation status
    """
    status = {
        "nodejs_installed": False,
        "nodejs_version": None,
        "npm_installed": False,
        "npm_version": None,
        "js_dependencies_installed": False,
        "js_script_exists": False,
        "ready": False
    }
    
    # Check Node.js
    node_installed, node_version = check_nodejs_installed()
    status["nodejs_installed"] = node_installed
    status["nodejs_version"] = node_version
    
    # Check npm
    npm_installed, npm_version = check_npm_installed()
    status["npm_installed"] = npm_installed
    status["npm_version"] = npm_version
    
    # Check JS dependencies
    status["js_dependencies_installed"] = check_js_dependencies_installed()
    
    # Check JS script
    js_script = get_js_directory() / "s3-to-storacha.js"
    status["js_script_exists"] = js_script.exists()
    
    # Overall ready status
    status["ready"] = all([
        status["nodejs_installed"],
        status["npm_installed"],
        status["js_dependencies_installed"],
        status["js_script_exists"]
    ])
    
    return status


def print_installation_status():
    """Print installation status to console."""
    status = verify_installation()
    
    print("\n" + "="*60)
    print("py-s3-storacha Installation Status")
    print("="*60)
    
    # Node.js
    if status["nodejs_installed"]:
        print(f"✓ Node.js: {status['nodejs_version']}")
    else:
        print("✗ Node.js: Not installed")
        print("  Install from: https://nodejs.org")
    
    # npm
    if status["npm_installed"]:
        print(f"✓ npm: {status['npm_version']}")
    else:
        print("✗ npm: Not installed")
    
    # JS dependencies
    if status["js_dependencies_installed"]:
        print("✓ JavaScript dependencies: Installed")
    else:
        print("✗ JavaScript dependencies: Not installed")
        print("  Run: python -m py_s3_storacha.setup_helpers")
    
    # JS script
    if status["js_script_exists"]:
        print("✓ JavaScript implementation: Found")
    else:
        print("✗ JavaScript implementation: Not found")
    
    print("="*60)
    
    if status["ready"]:
        print("✓ Installation complete - ready to use!")
    else:
        print("⚠ Installation incomplete - see issues above")
    
    print("="*60 + "\n")
    
    return status["ready"]


def main():
    """Main entry point for setup helper."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Install JavaScript dependencies for py-s3-storacha"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force reinstall even if already installed"
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check installation status without installing"
    )
    
    args = parser.parse_args()
    
    if args.check:
        ready = print_installation_status()
        sys.exit(0 if ready else 1)
    
    # Install dependencies
    try:
        print("Installing JavaScript dependencies...")
        install_js_dependencies(force=args.force)
        print("\n✓ Installation successful!\n")
        print_installation_status()
        sys.exit(0)
    except RuntimeError as e:
        print(f"\n✗ Installation failed: {e}\n", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
