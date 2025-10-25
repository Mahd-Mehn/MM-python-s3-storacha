"""Command-line interface for S3 to Storacha migration."""

import argparse
import asyncio
import logging
import os
import sys
from typing import Optional, Dict, Any, List
from pathlib import Path

from .config import S3Config, StorachaConfig, MigrationConfig, ConfigurationParser
from .api import S3ToStorachaMigrator
from .models import MigrationRequest, MigrationResult, MigrationProgress
from .progress import create_console_progress_callback
from .exceptions import S3StorachaError, ConfigurationError, MigrationError


# Configure logging for CLI
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class CLIArgumentParser:
    """Handles command-line argument parsing and validation."""
    
    def __init__(self) -> None:
        """Initialize the argument parser."""
        self.parser = self._create_parser()
    
    def _create_parser(self) -> argparse.ArgumentParser:
        """Create and configure the argument parser."""
        parser = argparse.ArgumentParser(
            prog='py-s3-storacha',
            description='Migrate objects from AWS S3 to Storacha storage',
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  # Basic migration
  py-s3-storacha --s3-bucket my-bucket --s3-region us-east-1 \\
                 --storacha-space my-space --storacha-key YOUR_KEY \\
                 --source-path folder/ --dest-path backup/

  # Migration with patterns
  py-s3-storacha --s3-bucket my-bucket --s3-region us-east-1 \\
                 --storacha-space my-space --storacha-key YOUR_KEY \\
                 --source-path folder/ --dest-path backup/ \\
                 --include-pattern "*.jpg" --exclude-pattern "temp/*"

  # Dry run with verbose output
  py-s3-storacha --s3-bucket my-bucket --s3-region us-east-1 \\
                 --storacha-space my-space --storacha-key YOUR_KEY \\
                 --source-path folder/ --dest-path backup/ \\
                 --dry-run --verbose

Environment Variables:
  AWS_ACCESS_KEY_ID       S3 access key ID
  AWS_SECRET_ACCESS_KEY   S3 secret access key
  AWS_DEFAULT_REGION      S3 region
  S3_ENDPOINT_URL         Custom S3 endpoint URL
  STORACHA_API_KEY        Storacha API key
  STORACHA_ENDPOINT_URL   Storacha endpoint URL
            """
        )
        
        # S3 Configuration
        s3_group = parser.add_argument_group('S3 Configuration')
        s3_group.add_argument(
            '--s3-access-key',
            help='S3 access key ID (default: AWS_ACCESS_KEY_ID env var)'
        )
        s3_group.add_argument(
            '--s3-secret-key',
            help='S3 secret access key (default: AWS_SECRET_ACCESS_KEY env var)'
        )
        s3_group.add_argument(
            '--s3-region',
            help='S3 region (default: AWS_DEFAULT_REGION env var or us-east-1)'
        )
        s3_group.add_argument(
            '--s3-bucket',
            required=True,
            help='S3 bucket name (required)'
        )
        s3_group.add_argument(
            '--s3-endpoint-url',
            help='Custom S3 endpoint URL (default: S3_ENDPOINT_URL env var)'
        )
        
        # Storacha Configuration
        storacha_group = parser.add_argument_group('Storacha Configuration')
        storacha_group.add_argument(
            '--storacha-api-key',
            help='Storacha API key (default: STORACHA_API_KEY env var)'
        )
        storacha_group.add_argument(
            '--storacha-endpoint-url',
            help='Storacha endpoint URL (default: STORACHA_ENDPOINT_URL env var or https://api.storacha.network)'
        )
        storacha_group.add_argument(
            '--storacha-space',
            required=True,
            help='Storacha space name (required)'
        )
        
        # Migration Parameters
        migration_group = parser.add_argument_group('Migration Parameters')
        migration_group.add_argument(
            '--source-path',
            required=True,
            help='Source path in S3 (e.g., "folder/" or "file.txt") (required)'
        )
        migration_group.add_argument(
            '--dest-path',
            required=True,
            help='Destination path in Storacha (required)'
        )
        migration_group.add_argument(
            '--include-pattern',
            help='Include only objects matching this pattern (glob syntax)'
        )
        migration_group.add_argument(
            '--exclude-pattern',
            help='Exclude objects matching this pattern (glob syntax)'
        )
        migration_group.add_argument(
            '--overwrite-existing',
            action='store_true',
            help='Overwrite existing objects in destination'
        )
        migration_group.add_argument(
            '--no-verify-checksums',
            action='store_true',
            help='Skip checksum verification during migration'
        )
        
        # Migration Options
        options_group = parser.add_argument_group('Migration Options')
        options_group.add_argument(
            '--batch-size',
            type=int,
            default=100,
            help='Number of objects to process in each batch (default: 100)'
        )
        options_group.add_argument(
            '--timeout',
            type=int,
            default=300,
            help='Timeout for migration operation in seconds (default: 300)'
        )
        options_group.add_argument(
            '--retry-attempts',
            type=int,
            default=3,
            help='Number of retry attempts for failed operations (default: 3)'
        )
        options_group.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be migrated without actually doing it'
        )
        options_group.add_argument(
            '--verbose',
            action='store_true',
            help='Enable verbose output'
        )
        options_group.add_argument(
            '--quiet',
            action='store_true',
            help='Suppress progress output (errors still shown)'
        )
        
        # Configuration File
        config_group = parser.add_argument_group('Configuration')
        config_group.add_argument(
            '--config-file',
            type=Path,
            help='Load configuration from file (JSON, YAML, or TOML)'
        )
        
        # Version
        parser.add_argument(
            '--version',
            action='version',
            version=f'%(prog)s {self._get_version()}'
        )
        
        return parser
    
    def _get_version(self) -> str:
        """Get the package version."""
        try:
            from . import __version__
            return __version__
        except ImportError:
            return "unknown"
    
    def parse_args(self, args: Optional[List[str]] = None) -> argparse.Namespace:
        """Parse command-line arguments.
        
        Args:
            args: List of arguments to parse (default: sys.argv)
            
        Returns:
            Parsed arguments namespace
        """
        return self.parser.parse_args(args)
    
    def validate_args(self, args: argparse.Namespace) -> None:
        """Validate parsed arguments.
        
        Args:
            args: Parsed arguments to validate
            
        Raises:
            ConfigurationError: If validation fails
        """
        errors = []
        
        # Validate batch size
        if args.batch_size <= 0:
            errors.append("Batch size must be greater than 0")
        
        # Validate timeout
        if args.timeout <= 0:
            errors.append("Timeout must be greater than 0")
        
        # Validate retry attempts
        if args.retry_attempts < 0:
            errors.append("Retry attempts cannot be negative")
        
        # Validate paths
        if not args.source_path.strip():
            errors.append("Source path cannot be empty or whitespace only")
        
        if not args.dest_path.strip():
            errors.append("Destination path cannot be empty or whitespace only")
        
        # Validate patterns
        if args.include_pattern and not args.include_pattern.strip():
            errors.append("Include pattern cannot be empty or whitespace only")
        
        if args.exclude_pattern and not args.exclude_pattern.strip():
            errors.append("Exclude pattern cannot be empty or whitespace only")
        
        # Validate conflicting options
        if args.verbose and args.quiet:
            errors.append("Cannot specify both --verbose and --quiet")
        
        # Validate config file exists if specified
        if args.config_file and not args.config_file.exists():
            errors.append(f"Configuration file not found: {args.config_file}")
        
        if errors:
            raise ConfigurationError(
                f"Argument validation failed: {'; '.join(errors)}"
            )


class CLIConfigurationLoader:
    """Loads configuration from various sources."""
    
    def __init__(self) -> None:
        """Initialize the configuration loader."""
        self.config_parser = ConfigurationParser()
    
    def load_configuration(
        self, 
        args: argparse.Namespace
    ) -> tuple[S3Config, StorachaConfig, MigrationConfig]:
        """Load configuration from arguments, environment, and config files.
        
        Args:
            args: Parsed command-line arguments
            
        Returns:
            Tuple of (S3Config, StorachaConfig, MigrationConfig)
            
        Raises:
            ConfigurationError: If configuration loading fails
        """
        # Start with empty configuration
        config_data: Dict[str, Any] = {}
        
        # Load from config file if specified
        if args.config_file:
            try:
                file_config = self.config_parser.parse_from_file(args.config_file)
                config_data.update(file_config)
            except Exception as e:
                raise ConfigurationError(
                    f"Failed to load configuration file {args.config_file}: {e}"
                )
        
        # Load from environment variables
        env_config = self._load_from_environment()
        config_data.update(env_config)
        
        # Override with command-line arguments
        cli_config = self._load_from_cli_args(args)
        config_data.update(cli_config)
        
        # Create configuration objects
        try:
            s3_config = self._create_s3_config(config_data)
            storacha_config = self._create_storacha_config(config_data)
            migration_config = self._create_migration_config(config_data)
            
            return s3_config, storacha_config, migration_config
            
        except Exception as e:
            raise ConfigurationError(f"Failed to create configuration: {e}")
    
    def _load_from_environment(self) -> Dict[str, Any]:
        """Load configuration from environment variables."""
        env_config = {}
        
        # S3 environment variables
        if os.getenv('AWS_ACCESS_KEY_ID'):
            env_config['s3_access_key_id'] = os.getenv('AWS_ACCESS_KEY_ID')
        
        if os.getenv('AWS_SECRET_ACCESS_KEY'):
            env_config['s3_secret_access_key'] = os.getenv('AWS_SECRET_ACCESS_KEY')
        
        if os.getenv('AWS_DEFAULT_REGION'):
            env_config['s3_region'] = os.getenv('AWS_DEFAULT_REGION')
        
        if os.getenv('S3_ENDPOINT_URL'):
            env_config['s3_endpoint_url'] = os.getenv('S3_ENDPOINT_URL')
        
        # Storacha environment variables
        if os.getenv('STORACHA_API_KEY'):
            env_config['storacha_api_key'] = os.getenv('STORACHA_API_KEY')
        
        if os.getenv('STORACHA_ENDPOINT_URL'):
            env_config['storacha_endpoint_url'] = os.getenv('STORACHA_ENDPOINT_URL')
        
        return env_config
    
    def _load_from_cli_args(self, args: argparse.Namespace) -> Dict[str, Any]:
        """Load configuration from command-line arguments."""
        cli_config = {}
        
        # S3 configuration
        if args.s3_access_key:
            cli_config['s3_access_key_id'] = args.s3_access_key
        
        if args.s3_secret_key:
            cli_config['s3_secret_access_key'] = args.s3_secret_key
        
        if args.s3_region:
            cli_config['s3_region'] = args.s3_region
        
        if args.s3_bucket:
            cli_config['s3_bucket_name'] = args.s3_bucket
        
        if args.s3_endpoint_url:
            cli_config['s3_endpoint_url'] = args.s3_endpoint_url
        
        # Storacha configuration
        if args.storacha_api_key:
            cli_config['storacha_api_key'] = args.storacha_api_key
        
        if args.storacha_endpoint_url:
            cli_config['storacha_endpoint_url'] = args.storacha_endpoint_url
        
        if args.storacha_space:
            cli_config['storacha_space_name'] = args.storacha_space
        
        # Migration configuration
        cli_config['batch_size'] = args.batch_size
        cli_config['timeout_seconds'] = args.timeout
        cli_config['retry_attempts'] = args.retry_attempts
        cli_config['dry_run'] = args.dry_run
        cli_config['verbose'] = args.verbose
        
        return cli_config
    
    def _create_s3_config(self, config_data: Dict[str, Any]) -> S3Config:
        """Create S3Config from configuration data."""
        # Required fields
        access_key_id = config_data.get('s3_access_key_id')
        secret_access_key = config_data.get('s3_secret_access_key')
        bucket_name = config_data.get('s3_bucket_name')
        
        # Check for required fields
        if not access_key_id:
            raise ConfigurationError(
                "S3 access key ID is required (use --s3-access-key or AWS_ACCESS_KEY_ID)"
            )
        
        if not secret_access_key:
            raise ConfigurationError(
                "S3 secret access key is required (use --s3-secret-key or AWS_SECRET_ACCESS_KEY)"
            )
        
        if not bucket_name:
            raise ConfigurationError(
                "S3 bucket name is required (use --s3-bucket)"
            )
        
        # Optional fields with defaults
        region = config_data.get('s3_region', 'us-east-1')
        endpoint_url = config_data.get('s3_endpoint_url')
        
        return S3Config(
            access_key_id=access_key_id,
            secret_access_key=secret_access_key,
            region=region,
            bucket_name=bucket_name,
            endpoint_url=endpoint_url
        )
    
    def _create_storacha_config(self, config_data: Dict[str, Any]) -> StorachaConfig:
        """Create StorachaConfig from configuration data."""
        # Required fields
        api_key = config_data.get('storacha_api_key')
        space_name = config_data.get('storacha_space_name')
        
        # Check for required fields
        if not api_key:
            raise ConfigurationError(
                "Storacha API key is required (use --storacha-api-key or STORACHA_API_KEY)"
            )
        
        if not space_name:
            raise ConfigurationError(
                "Storacha space name is required (use --storacha-space)"
            )
        
        # Optional fields with defaults
        endpoint_url = config_data.get('storacha_endpoint_url', 'https://api.storacha.network')
        
        return StorachaConfig(
            api_key=api_key,
            endpoint_url=endpoint_url,
            space_name=space_name
        )
    
    def _create_migration_config(self, config_data: Dict[str, Any]) -> MigrationConfig:
        """Create MigrationConfig from configuration data."""
        return MigrationConfig(
            batch_size=config_data.get('batch_size', 100),
            timeout_seconds=config_data.get('timeout_seconds', 300),
            retry_attempts=config_data.get('retry_attempts', 3),
            dry_run=config_data.get('dry_run', False),
            verbose=config_data.get('verbose', False)
        )


class CLIProgressDisplay:
    """Handles progress display for CLI operations."""
    
    def __init__(self, quiet: bool = False, verbose: bool = False) -> None:
        """Initialize progress display.
        
        Args:
            quiet: Suppress progress output
            verbose: Enable verbose output
        """
        self.quiet = quiet
        self.verbose = verbose
        self._last_progress_line = ""
    
    def create_progress_callback(self):
        """Create a progress callback function for the CLI."""
        if self.quiet:
            return None
        
        def progress_callback(progress: MigrationProgress) -> None:
            """Handle progress updates."""
            if self.verbose:
                # Verbose mode: show detailed progress
                print(f"[{progress.current_operation or 'migrating'}] "
                      f"{progress.current_object} "
                      f"({progress.objects_completed}/{progress.total_objects} objects, "
                      f"{progress.bytes_transferred:,}/{progress.total_bytes:,} bytes, "
                      f"{progress.progress_percentage:.1f}%)")
            else:
                # Normal mode: show progress bar
                progress_bar = self._create_progress_bar(
                    progress.progress_percentage,
                    width=40
                )
                
                # Clear previous line and show new progress
                if self._last_progress_line:
                    print('\r' + ' ' * len(self._last_progress_line) + '\r', end='')
                
                progress_line = (
                    f"Progress: {progress_bar} "
                    f"{progress.objects_completed}/{progress.total_objects} objects "
                    f"({progress.progress_percentage:.1f}%)"
                )
                
                print(progress_line, end='', flush=True)
                self._last_progress_line = progress_line
        
        return progress_callback
    
    def _create_progress_bar(self, percentage: float, width: int = 40) -> str:
        """Create a text-based progress bar."""
        filled = int(width * percentage / 100)
        bar = '█' * filled + '░' * (width - filled)
        return f"[{bar}]"
    
    def print_result(self, result: MigrationResult) -> None:
        """Print migration result."""
        # Clear progress line if needed
        if self._last_progress_line and not self.quiet:
            print('\r' + ' ' * len(self._last_progress_line) + '\r', end='')
        
        if result.success:
            print(f"✓ Migration completed successfully!")
            print(f"  Objects migrated: {result.objects_migrated:,}")
            print(f"  Total size: {result.total_size_bytes:,} bytes")
            print(f"  Duration: {result.duration_seconds:.2f} seconds")
            
            if result.warnings:
                print(f"  Warnings: {len(result.warnings)}")
                if self.verbose:
                    for warning in result.warnings:
                        print(f"    - {warning}")
            
            if result.skipped_objects:
                print(f"  Skipped objects: {len(result.skipped_objects)}")
                if self.verbose:
                    for skipped in result.skipped_objects:
                        print(f"    - {skipped}")
        else:
            print(f"✗ Migration failed!")
            print(f"  Objects migrated: {result.objects_migrated:,}")
            print(f"  Duration: {result.duration_seconds:.2f} seconds")
            
            if result.errors:
                print(f"  Errors: {len(result.errors)}")
                for error in result.errors:
                    print(f"    - {error}")
            
            if result.failed_objects:
                print(f"  Failed objects: {len(result.failed_objects)}")
                if self.verbose:
                    for failed in result.failed_objects:
                        print(f"    - {failed}")
                elif len(result.failed_objects) <= 5:
                    for failed in result.failed_objects:
                        print(f"    - {failed}")
                else:
                    for failed in result.failed_objects[:5]:
                        print(f"    - {failed}")
                    print(f"    ... and {len(result.failed_objects) - 5} more")


class CLIExecutor:
    """Handles CLI execution workflow."""
    
    def __init__(self) -> None:
        """Initialize CLI executor."""
        self.arg_parser = CLIArgumentParser()
        self.config_loader = CLIConfigurationLoader()
    
    async def execute(self, args: Optional[List[str]] = None) -> int:
        """Execute CLI workflow.
        
        Args:
            args: Command-line arguments (default: sys.argv)
            
        Returns:
            Exit code (0 for success, non-zero for failure)
        """
        try:
            # Parse arguments
            parsed_args = self.arg_parser.parse_args(args)
            
            # Validate arguments
            self.arg_parser.validate_args(parsed_args)
            
            # Configure logging
            self._configure_logging(parsed_args)
            
            # Load configuration
            s3_config, storacha_config, migration_config = self.config_loader.load_configuration(parsed_args)
            
            # Create migration request
            migration_request = self._create_migration_request(parsed_args)
            
            # Set up progress display
            progress_display = CLIProgressDisplay(
                quiet=parsed_args.quiet,
                verbose=parsed_args.verbose
            )
            progress_callback = progress_display.create_progress_callback()
            
            # Execute migration
            logger.info("Starting S3 to Storacha migration")
            
            if migration_config.dry_run:
                print("DRY RUN MODE - No actual migration will be performed")
            
            migrator = S3ToStorachaMigrator(
                s3_config=s3_config,
                storacha_config=storacha_config,
                migration_config=migration_config
            )
            
            result = await migrator.migrate(
                request=migration_request,
                progress_callback=progress_callback
            )
            
            # Display result
            progress_display.print_result(result)
            
            # Return appropriate exit code
            return 0 if result.success else 1
            
        except KeyboardInterrupt:
            print("\n✗ Migration cancelled by user")
            logger.info("Migration cancelled by user")
            return 130  # Standard exit code for SIGINT
            
        except ConfigurationError as e:
            print(f"✗ Configuration error: {e}")
            logger.error(f"Configuration error: {e}")
            return 2
            
        except MigrationError as e:
            print(f"✗ Migration error: {e}")
            logger.error(f"Migration error: {e}")
            return 3
            
        except S3StorachaError as e:
            print(f"✗ Error: {e}")
            logger.error(f"S3StorachaError: {e}")
            return 4
            
        except Exception as e:
            print(f"✗ Unexpected error: {e}")
            logger.exception("Unexpected error during CLI execution")
            return 5
    
    def _configure_logging(self, args: argparse.Namespace) -> None:
        """Configure logging based on CLI arguments."""
        if args.verbose:
            logging.getLogger().setLevel(logging.DEBUG)
            logging.getLogger('py_s3_storacha').setLevel(logging.DEBUG)
        elif args.quiet:
            logging.getLogger().setLevel(logging.ERROR)
            logging.getLogger('py_s3_storacha').setLevel(logging.ERROR)
        else:
            logging.getLogger().setLevel(logging.INFO)
            logging.getLogger('py_s3_storacha').setLevel(logging.INFO)
    
    def _create_migration_request(self, args: argparse.Namespace) -> MigrationRequest:
        """Create migration request from CLI arguments."""
        return MigrationRequest(
            source_path=args.source_path,
            destination_path=args.dest_path,
            include_pattern=args.include_pattern,
            exclude_pattern=args.exclude_pattern,
            overwrite_existing=args.overwrite_existing,
            verify_checksums=not args.no_verify_checksums
        )


def main(args: Optional[List[str]] = None) -> int:
    """Main CLI entry point.
    
    Args:
        args: Command-line arguments (default: sys.argv)
        
    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    executor = CLIExecutor()
    
    try:
        # Run the async executor
        return asyncio.run(executor.execute(args))
    except KeyboardInterrupt:
        print("\n✗ Operation cancelled")
        return 130
    except Exception as e:
        print(f"✗ Fatal error: {e}")
        logger.exception("Fatal error in main")
        return 5


if __name__ == '__main__':
    sys.exit(main())