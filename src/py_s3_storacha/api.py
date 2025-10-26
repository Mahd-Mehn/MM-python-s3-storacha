"""Python API layer for S3 to Storacha migration operations."""

import asyncio
import logging
import time
from typing import Optional, Dict, Any, List
from datetime import datetime

from .config import S3Config, StorachaConfig, MigrationConfig
from .js_wrapper import JSWrapperManager
from .models import (
    MigrationRequest, 
    MigrationResult, 
    MigrationProgress, 
    MigrationStatus,
    ProgressCallback
)
from .progress import ProgressReporter
from .exceptions import MigrationError, ConfigurationError, JSWrapperError
from .error_handler import with_error_handling, get_retry_handler
from .logging_config import get_logger


logger = get_logger(__name__)


class S3ToStorachaMigrator:
    """Main class for orchestrating S3 to Storacha migrations."""
    
    def __init__(
        self,
        s3_config: S3Config,
        storacha_config: StorachaConfig,
        migration_config: Optional[MigrationConfig] = None,
        js_script_path: Optional[str] = None
    ) -> None:
        """Initialize the migrator with configuration.
        
        Args:
            s3_config: S3 connection and authentication configuration
            storacha_config: Storacha connection and authentication configuration
            migration_config: Migration-specific settings (optional)
            js_script_path: Path to JavaScript implementation (optional)
        """
        self.s3_config = s3_config
        self.storacha_config = storacha_config
        self.migration_config = migration_config or MigrationConfig()
        
        # Initialize JavaScript wrapper manager
        self.js_wrapper = JSWrapperManager(js_script_path)
        
        # Initialize progress reporter
        self._progress_reporter = ProgressReporter()
        
        # Migration state
        self._current_migration: Optional[MigrationRequest] = None
        self._migration_start_time: Optional[float] = None
        self._cancelled = False
    
    @with_error_handling("migration", error_types=(MigrationError, JSWrapperError, asyncio.TimeoutError))
    async def migrate(
        self,
        request: MigrationRequest,
        progress_callback: Optional[ProgressCallback] = None
    ) -> MigrationResult:
        """Execute a migration operation.
        
        Args:
            request: Migration request parameters
            progress_callback: Optional callback for progress updates
            
        Returns:
            Migration result with status and statistics
            
        Raises:
            MigrationError: If migration fails
            ConfigurationError: If configuration is invalid
        """
        logger.info(f"Starting migration from {request.source_path} to {request.destination_path}")
        
        # Validate inputs
        self._validate_migration_request(request)
        
        # Set up migration state
        self._current_migration = request
        self._migration_start_time = time.time()
        self._cancelled = False
        
        # Set up progress reporting
        self._progress_reporter.reset()
        if progress_callback:
            self._progress_reporter.add_callback(progress_callback)
        
        try:
            # Validate environment before starting
            await self.js_wrapper.validate_environment()
            
            # Execute migration workflow
            result = await self._execute_migration_workflow(request)
            
            logger.info(f"Migration completed successfully: {result.objects_migrated} objects migrated")
            return result
            
        except Exception as e:
            logger.error(f"Migration failed: {e}")
            
            # Create failure result
            duration = time.time() - self._migration_start_time if self._migration_start_time else 0
            result = MigrationResult(
                success=False,
                status=MigrationStatus.FAILED,
                objects_migrated=0,
                total_size_bytes=0,
                duration_seconds=duration,
                errors=[str(e)]
            )
            
            # Re-raise as MigrationError if not already
            if not isinstance(e, MigrationError):
                raise MigrationError(
                    f"Migration failed: {e}",
                    operation="migrate",
                    source_path=request.source_path,
                    destination_path=request.destination_path,
                    original_error=e
                )
            raise
            
        finally:
            # Clean up migration state
            self._current_migration = None
            self._migration_start_time = None
            self._cancelled = False
            
            # Clean up progress reporting
            if progress_callback:
                self._progress_reporter.remove_callback(progress_callback)
    
    async def _execute_migration_workflow(self, request: MigrationRequest) -> MigrationResult:
        """Execute the core migration workflow.
        
        Args:
            request: Migration request parameters
            
        Returns:
            Migration result
            
        Raises:
            MigrationError: If any step of the workflow fails
        """
        # Prepare JavaScript wrapper input
        js_input = self._prepare_js_input(request)
        
        # Report initial progress
        self._progress_reporter.update_progress(
            current_object="Initializing migration...",
            current_operation="initialization",
            completed_objects=0,
            transferred_bytes=0
        )
        
        try:
            # Execute JavaScript wrapper with progress monitoring
            js_result = await self._execute_with_progress_monitoring(js_input)
            
            # Parse and validate JavaScript result
            result = self._parse_js_result(js_result, request)
            
            return result
            
        except asyncio.TimeoutError:
            raise MigrationError.timeout_error(
                operation="migration",
                timeout_seconds=self.migration_config.timeout_seconds
            )
        except JSWrapperError as e:
            raise MigrationError(
                f"JavaScript wrapper execution failed: {e.message}",
                operation="javascript_execution",
                source_path=request.source_path,
                destination_path=request.destination_path,
                original_error=e
            )
    
    def _validate_migration_request(self, request: MigrationRequest) -> None:
        """Validate migration request parameters.
        
        Args:
            request: Migration request to validate
            
        Raises:
            MigrationError: If request validation fails
        """
        try:
            # Basic request validation is handled by MigrationRequest.__post_init__
            # Additional validation can be added here
            
            # Validate path formats (basic checks)
            if not request.source_path.strip():
                raise MigrationError.validation_error(
                    "Source path cannot be empty or whitespace only",
                    source_path=request.source_path
                )
            
            if not request.destination_path.strip():
                raise MigrationError.validation_error(
                    "Destination path cannot be empty or whitespace only",
                    destination_path=request.destination_path
                )
            
            # Validate pattern syntax if provided
            if request.include_pattern and not request.include_pattern.strip():
                raise MigrationError.validation_error(
                    "Include pattern cannot be empty or whitespace only"
                )
            
            if request.exclude_pattern and not request.exclude_pattern.strip():
                raise MigrationError.validation_error(
                    "Exclude pattern cannot be empty or whitespace only"
                )
            
        except ValueError as e:
            raise MigrationError.validation_error(
                str(e),
                source_path=request.source_path,
                destination_path=request.destination_path
            )
    
    def _prepare_js_input(self, request: MigrationRequest) -> Dict[str, Any]:
        """Prepare input data for JavaScript wrapper execution.
        
        Args:
            request: Migration request parameters
            
        Returns:
            Dictionary containing all data needed by JavaScript wrapper
        """
        # Convert configuration objects to dictionaries
        s3_data = {
            "accessKeyId": self.s3_config.access_key_id,
            "secretAccessKey": self.s3_config.secret_access_key,
            "region": self.s3_config.region,
            "bucketName": self.s3_config.bucket_name,
        }
        
        if self.s3_config.endpoint_url:
            s3_data["endpointUrl"] = self.s3_config.endpoint_url
        
        storacha_data = {
            "apiKey": self.storacha_config.api_key,
            "endpointUrl": self.storacha_config.endpoint_url,
            "spaceName": self.storacha_config.space_name,
        }
        
        migration_data = {
            "sourcePath": request.source_path,
            "destinationPath": request.destination_path,
            "batchSize": self.migration_config.batch_size,
            "timeoutSeconds": self.migration_config.timeout_seconds,
            "retryAttempts": self.migration_config.retry_attempts,
            "verbose": self.migration_config.verbose,
            "dryRun": self.migration_config.dry_run,
            "overwriteExisting": request.overwrite_existing,
            "verifyChecksums": request.verify_checksums,
        }
        
        if request.include_pattern:
            migration_data["includePattern"] = request.include_pattern
        
        if request.exclude_pattern:
            migration_data["excludePattern"] = request.exclude_pattern
        
        return {
            "s3": s3_data,
            "storacha": storacha_data,
            "migration": migration_data
        }
    
    async def _execute_with_progress_monitoring(self, js_input: Dict[str, Any]) -> Dict[str, Any]:
        """Execute JavaScript wrapper with progress monitoring and timeout handling.
        
        Args:
            js_input: Input data for JavaScript wrapper
            
        Returns:
            JavaScript wrapper result
            
        Raises:
            asyncio.TimeoutError: If operation times out
            MigrationError: If operation is cancelled
        """
        # Create a task for the JavaScript execution
        js_task = asyncio.create_task(
            self.js_wrapper.execute_migration(
                js_input["s3"],
                js_input["storacha"],
                js_input["migration"]
            )
        )
        
        # Create a task for progress monitoring
        progress_task = asyncio.create_task(
            self._monitor_progress()
        )
        
        try:
            # Wait for either completion or timeout
            done, pending = await asyncio.wait(
                [js_task, progress_task],
                timeout=self.migration_config.timeout_seconds,
                return_when=asyncio.FIRST_COMPLETED
            )
            
            # Cancel any pending tasks
            for task in pending:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
            
            # Check if we timed out
            if not done:
                js_task.cancel()
                progress_task.cancel()
                raise asyncio.TimeoutError()
            
            # Check if migration was cancelled
            if self._cancelled:
                js_task.cancel()
                progress_task.cancel()
                raise MigrationError(
                    "Migration was cancelled by user",
                    operation="migration_cancelled"
                )
            
            # Get the result from the JavaScript task
            if js_task in done:
                return await js_task
            else:
                # This shouldn't happen, but handle it gracefully
                raise MigrationError(
                    "JavaScript execution completed unexpectedly",
                    operation="javascript_execution"
                )
                
        except asyncio.TimeoutError:
            # Clean up tasks
            js_task.cancel()
            progress_task.cancel()
            raise
    
    async def _monitor_progress(self) -> None:
        """Monitor migration progress and provide periodic updates.
        
        This method runs in parallel with the JavaScript execution and provides
        periodic progress updates based on estimated progress.
        """
        progress_interval = 2.0  # Update progress every 2 seconds
        start_time = time.time()
        
        # Simulate progress updates (in a real implementation, this would
        # communicate with the JavaScript process to get actual progress)
        estimated_objects = 100  # Default estimate
        estimated_bytes = 1024 * 1024 * 100  # 100MB default estimate
        
        # Set initial totals
        self._progress_reporter.update_progress(
            total_objects=estimated_objects,
            total_bytes=estimated_bytes,
            current_operation="migrating"
        )
        
        while not self._cancelled:
            try:
                await asyncio.sleep(progress_interval)
                
                elapsed_time = time.time() - start_time
                
                # Create estimated progress (this is a placeholder - in a real
                # implementation, we would get actual progress from the JS process)
                estimated_completion = min(elapsed_time / self.migration_config.timeout_seconds, 0.95)
                
                self._progress_reporter.update_progress(
                    current_object=f"Processing objects... (estimated)",
                    completed_objects=int(estimated_objects * estimated_completion),
                    transferred_bytes=int(estimated_bytes * estimated_completion),
                    current_operation="migrating"
                )
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning(f"Error in progress monitoring: {e}")
                break
    
    def _parse_js_result(self, js_result: Dict[str, Any], request: MigrationRequest) -> MigrationResult:
        """Parse JavaScript wrapper result into Python-native types.
        
        Args:
            js_result: Raw result from JavaScript wrapper
            request: Original migration request
            
        Returns:
            Parsed migration result
            
        Raises:
            MigrationError: If result parsing fails
        """
        try:
            # Calculate duration
            duration = time.time() - self._migration_start_time if self._migration_start_time else 0
            
            # Extract basic result data
            success = js_result.get("success", False)
            objects_migrated = js_result.get("objectsMigrated", 0)
            total_size_bytes = js_result.get("totalSizeBytes", 0)
            
            # Extract error and warning lists
            errors = js_result.get("errors", [])
            warnings = js_result.get("warnings", [])
            skipped_objects = js_result.get("skippedObjects", [])
            failed_objects = js_result.get("failedObjects", [])
            
            # Determine status
            if success and not errors and not failed_objects:
                status = MigrationStatus.COMPLETED
            elif not success or errors or failed_objects:
                status = MigrationStatus.FAILED
            else:
                status = MigrationStatus.COMPLETED  # Completed with warnings
            
            # Create result object
            result = MigrationResult(
                success=success,
                status=status,
                objects_migrated=objects_migrated,
                total_size_bytes=total_size_bytes,
                duration_seconds=duration,
                errors=errors if isinstance(errors, list) else [str(errors)],
                warnings=warnings if isinstance(warnings, list) else [str(warnings)],
                skipped_objects=skipped_objects if isinstance(skipped_objects, list) else [],
                failed_objects=failed_objects if isinstance(failed_objects, list) else []
            )
            
            # Report final progress
            self._progress_reporter.update_progress(
                current_object="Migration completed",
                completed_objects=objects_migrated,
                total_objects=objects_migrated,
                transferred_bytes=total_size_bytes,
                total_bytes=total_size_bytes,
                current_operation="completed"
            )
            
            return result
            
        except (KeyError, TypeError, ValueError) as e:
            raise MigrationError(
                f"Failed to parse JavaScript wrapper result: {e}",
                operation="result_parsing",
                source_path=request.source_path,
                destination_path=request.destination_path,
                original_error=e
            )
    
    def cancel_migration(self) -> None:
        """Cancel the current migration operation.
        
        Note: This sets a cancellation flag, but the actual cancellation
        depends on the JavaScript wrapper implementation.
        """
        if self._current_migration:
            logger.info("Migration cancellation requested")
            self._cancelled = True
        else:
            logger.warning("No active migration to cancel")
    
    @property
    def is_migration_active(self) -> bool:
        """Check if a migration is currently active."""
        return self._current_migration is not None
    
    @property
    def current_migration_request(self) -> Optional[MigrationRequest]:
        """Get the current migration request if active."""
        return self._current_migration
    
    def add_progress_callback(self, callback: ProgressCallback) -> None:
        """Add a progress callback to receive updates during migration.
        
        Args:
            callback: Function to call with progress updates
        """
        self._progress_reporter.add_callback(callback)
    
    def remove_progress_callback(self, callback: ProgressCallback) -> None:
        """Remove a progress callback.
        
        Args:
            callback: Function to remove from callbacks
        """
        self._progress_reporter.remove_callback(callback)
    
    def get_current_progress(self) -> Optional[MigrationProgress]:
        """Get current migration progress if a migration is active.
        
        Returns:
            Current migration progress, or None if no migration is active
        """
        if not self.is_migration_active:
            return None
        
        return self._progress_reporter.get_current_progress()
    
    @property
    def migration_duration(self) -> Optional[float]:
        """Get the duration of the current migration in seconds.
        
        Returns:
            Duration in seconds, or None if no migration is active
        """
        if not self._migration_start_time:
            return None
        
        return time.time() - self._migration_start_time


# Convenience function for simple migrations
@with_error_handling("simple_migration", error_types=(MigrationError, ConfigurationError, JSWrapperError))
async def migrate_s3_to_storacha(
    s3_config: S3Config,
    storacha_config: StorachaConfig,
    source_path: str,
    destination_path: str,
    migration_config: Optional[MigrationConfig] = None,
    progress_callback: Optional[ProgressCallback] = None,
    **kwargs
) -> MigrationResult:
    """Convenience function for simple S3 to Storacha migrations.
    
    Args:
        s3_config: S3 connection and authentication configuration
        storacha_config: Storacha connection and authentication configuration
        source_path: Source path in S3 (e.g., 'folder/' or 'file.txt')
        destination_path: Destination path in Storacha
        migration_config: Migration-specific settings (optional)
        progress_callback: Optional callback for progress updates
        **kwargs: Additional parameters for MigrationRequest
        
    Returns:
        Migration result with status and statistics
        
    Raises:
        MigrationError: If migration fails
        ConfigurationError: If configuration is invalid
    """
    # Create migration request
    request = MigrationRequest(
        source_path=source_path,
        destination_path=destination_path,
        **kwargs
    )
    
    # Create migrator and execute
    migrator = S3ToStorachaMigrator(
        s3_config=s3_config,
        storacha_config=storacha_config,
        migration_config=migration_config
    )
    
    return await migrator.migrate(request, progress_callback)