"""Authentication helper for Storacha."""

import subprocess
import sys
from typing import Optional, List, Tuple
import logging

logger = logging.getLogger(__name__)


class StorachaAuthHelper:
    """Helper class for managing Storacha authentication."""

    @staticmethod
    def check_cli_installed() -> Tuple[bool, Optional[str]]:
        """Check if Storacha CLI is installed.

        Returns:
            Tuple of (is_installed, version_string)
        """
        try:
            result = subprocess.run(
                ["storacha", "--version"], capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                version = result.stdout.strip()
                return True, version
            return False, None
        except (subprocess.SubprocessError, FileNotFoundError):
            return False, None

    @staticmethod
    def check_authenticated() -> Tuple[bool, Optional[str]]:
        """Check if user is authenticated with Storacha CLI.

        Returns:
            Tuple of (is_authenticated, user_did)
        """
        try:
            result = subprocess.run(
                ["storacha", "whoami"], capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                user_did = result.stdout.strip()
                return True, user_did
            return False, None
        except (subprocess.SubprocessError, FileNotFoundError):
            return False, None

    @staticmethod
    def list_spaces() -> List[dict]:
        """List available Storacha spaces.

        Returns:
            List of space dictionaries with 'did', 'name', and 'current' keys
        """
        try:
            result = subprocess.run(
                ["storacha", "space", "ls"], capture_output=True, text=True, timeout=10
            )

            if result.returncode != 0:
                return []

            spaces = []
            for line in result.stdout.strip().split("\n"):
                if not line.strip():
                    continue

                # Parse format: "* did:key:... space-name" or "  did:key:... space-name"
                is_current = line.startswith("*")
                parts = line.strip().lstrip("*").strip().split(None, 1)

                if len(parts) >= 1:
                    space = {
                        "did": parts[0],
                        "name": parts[1] if len(parts) > 1 else None,
                        "current": is_current,
                    }
                    spaces.append(space)

            return spaces

        except (subprocess.SubprocessError, FileNotFoundError):
            return []

    @staticmethod
    def install_cli() -> bool:
        """Install Storacha CLI using npm.

        Returns:
            True if installation successful
        """
        try:
            print("Installing Storacha CLI...")
            result = subprocess.run(
                ["npm", "install", "-g", "@storacha/cli"],
                capture_output=True,
                text=True,
                timeout=120,
            )

            if result.returncode == 0:
                print("✓ Storacha CLI installed successfully")
                return True
            else:
                print(f"✗ Installation failed: {result.stderr}")
                return False

        except Exception as e:
            print(f"✗ Installation failed: {e}")
            return False

    @staticmethod
    def login(email: str) -> bool:
        """Login to Storacha with email.

        Args:
            email: Email address for authentication

        Returns:
            True if login successful
        """
        try:
            print(f"\nLogging in to Storacha with: {email}")
            print("⚠️  Check your email for verification link!\n")

            result = subprocess.run(
                ["storacha", "login", email],
                timeout=300,  # 5 minutes for user to verify email
            )

            return result.returncode == 0

        except subprocess.TimeoutExpired:
            print("\n✗ Login timed out - verification link not clicked")
            return False
        except Exception as e:
            print(f"\n✗ Login failed: {e}")
            return False

    @staticmethod
    def create_space(name: str) -> bool:
        """Create a new Storacha space.

        Args:
            name: Name for the new space

        Returns:
            True if space created successfully
        """
        try:
            print(f"\nCreating space: {name}")

            result = subprocess.run(
                ["storacha", "space", "create", name],
                capture_output=True,
                text=True,
                timeout=60,
            )

            if result.returncode == 0:
                print(f"✓ Space '{name}' created successfully")
                return True
            else:
                print(f"✗ Failed to create space: {result.stderr}")
                return False

        except Exception as e:
            print(f"✗ Failed to create space: {e}")
            return False

    @classmethod
    def setup_authentication(
        cls, email: Optional[str] = None, space_name: Optional[str] = None
    ) -> bool:
        """Interactive setup for Storacha authentication.

        Args:
            email: Email address (will prompt if not provided)
            space_name: Space name (will prompt if not provided)

        Returns:
            True if setup successful
        """
        print("\n" + "=" * 60)
        print("Storacha Authentication Setup")
        print("=" * 60 + "\n")

        # Check if CLI is installed
        cli_installed, version = cls.check_cli_installed()

        if not cli_installed:
            print("Storacha CLI is not installed.")
            response = input("Install it now? (y/n): ").strip().lower()

            if response == "y":
                if not cls.install_cli():
                    return False
            else:
                print("\nPlease install manually:")
                print("  npm install -g @storacha/cli")
                return False
        else:
            print(f"✓ Storacha CLI installed: {version}")

        # Check if authenticated
        authenticated, user_did = cls.check_authenticated()

        if not authenticated:
            print("\nNot authenticated with Storacha.")

            if not email:
                email = input("Enter your email address: ").strip()

            if not cls.login(email):
                return False

            print("✓ Authentication successful")
        else:
            print(f"✓ Already authenticated: {user_did}")

        # Check spaces
        spaces = cls.list_spaces()

        if spaces:
            print(f"\n✓ Found {len(spaces)} space(s):")
            for space in spaces:
                marker = "*" if space["current"] else " "
                name = space["name"] or "(unnamed)"
                print(f"  {marker} {name} - {space['did']}")
        else:
            print("\nNo spaces found.")

            if not space_name:
                space_name = input("Enter name for new space: ").strip()

            if not cls.create_space(space_name):
                return False

        print("\n" + "=" * 60)
        print("✓ Setup Complete!")
        print("=" * 60)
        print("\nYou can now use py-s3-storacha for migrations.")
        print("The JavaScript client will use these credentials automatically.\n")

        return True

    @classmethod
    def print_status(cls):
        """Print current authentication status."""
        print("\n" + "=" * 60)
        print("Storacha Authentication Status")
        print("=" * 60 + "\n")

        # Check CLI
        cli_installed, version = cls.check_cli_installed()
        if cli_installed:
            print(f"✓ CLI installed: {version}")
        else:
            print("✗ CLI not installed")
            print("  Install: npm install -g @storacha/cli")

        # Check authentication
        authenticated, user_did = cls.check_authenticated()
        if authenticated:
            print(f"✓ Authenticated: {user_did}")
        else:
            print("✗ Not authenticated")
            print("  Login: storacha login your-email@example.com")

        # List spaces
        spaces = cls.list_spaces()
        if spaces:
            print(f"\n✓ Spaces ({len(spaces)}):")
            for space in spaces:
                marker = "*" if space["current"] else " "
                name = space["name"] or "(unnamed)"
                print(f"  {marker} {name}")
                print(f"    DID: {space['did']}")
        else:
            print("\n✗ No spaces found")
            print("  Create: storacha space create my-space")

        print("\n" + "=" * 60 + "\n")


def main():
    """Main entry point for auth helper."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Manage Storacha authentication for py-s3-storacha"
    )
    parser.add_argument("--setup", action="store_true", help="Run interactive setup")
    parser.add_argument("--email", help="Email address for authentication")
    parser.add_argument("--space", help="Space name to create")
    parser.add_argument(
        "--status", action="store_true", help="Show authentication status"
    )

    args = parser.parse_args()

    helper = StorachaAuthHelper()

    if args.status:
        helper.print_status()
        sys.exit(0)

    if args.setup:
        success = helper.setup_authentication(email=args.email, space_name=args.space)
        sys.exit(0 if success else 1)

    # Default: show status
    helper.print_status()


if __name__ == "__main__":
    main()
