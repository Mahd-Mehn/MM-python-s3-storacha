"""Data models for S3 to Storacha migration operations."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Callable, Any, Dict
from enum import Enum


class MigrationStatus(Enum):
    """Status of a migration operation."""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class S3Object:
    """Represents an S3 object to be migrated."""
    key: str
    size: int
    last_modified: datetime
    etag: str
    storage_class: Optional[str] = None
    
    def __post_init__(self) -> None:
        """Validate S3 object data after initialization."""
        if not self.key:
            raise ValueError("S3 object key cannot be empty")
        if self.size < 0:
            raise ValueError("S3 object size cannot be negative")


@dataclass
class MigrationProgress:
    """Progress information for a migration operation."""
    current_object: str
    objects_completed: int
    total_objects: int
    bytes_transferred: int
    total_bytes: int
    estimated_time_remaining: Optional[float] = None
    current_operation: Optional[str] = None
    
    @property
    def progress_percentage(self) -> float:
        """Calculate progress as a percentage."""
        if self.total_objects == 0:
            return 0.0
        return (self.objects_completed / self.total_objects) * 100.0
    
    @property
    def bytes_percentage(self) -> float:
        """Calculate bytes transferred as a percentage."""
        if self.total_bytes == 0:
            return 0.0
        return (self.bytes_transferred / self.total_bytes) * 100.0


@dataclass
class MigrationResult:
    """Result of a migration operation."""
    success: bool
    status: MigrationStatus
    objects_migrated: int
    total_size_bytes: int
    duration_seconds: float
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    skipped_objects: List[str] = field(default_factory=list)
    failed_objects: List[str] = field(default_factory=list)
    
    @property
    def has_errors(self) -> bool:
        """Check if the migration had any errors."""
        return len(self.errors) > 0 or len(self.failed_objects) > 0
    
    @property
    def has_warnings(self) -> bool:
        """Check if the migration had any warnings."""
        return len(self.warnings) > 0 or len(self.skipped_objects) > 0


@dataclass
class MigrationRequest:
    """Request parameters for a migration operation."""
    source_path: str
    destination_path: str
    include_pattern: Optional[str] = None
    exclude_pattern: Optional[str] = None
    overwrite_existing: bool = False
    verify_checksums: bool = True
    
    def __post_init__(self) -> None:
        """Validate migration request after initialization."""
        if not self.source_path:
            raise ValueError("Source path cannot be empty")
        if not self.destination_path:
            raise ValueError("Destination path cannot be empty")


# Type alias for progress callback function
ProgressCallback = Callable[[MigrationProgress], None]