"""Progress reporting utilities for migration operations."""

import time
import threading
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from .models import MigrationProgress, ProgressCallback


@dataclass
class ProgressTracker:
    """Tracks migration progress with timing and estimation capabilities."""
    
    start_time: float = field(default_factory=time.time)
    total_objects: int = 0
    total_bytes: int = 0
    completed_objects: int = 0
    transferred_bytes: int = 0
    current_object: str = ""
    current_operation: str = ""
    
    # Progress history for rate calculation
    _progress_history: List[tuple[float, int, int]] = field(default_factory=list)
    _lock: threading.Lock = field(default_factory=threading.Lock)
    
    def update(
        self,
        completed_objects: Optional[int] = None,
        transferred_bytes: Optional[int] = None,
        current_object: Optional[str] = None,
        current_operation: Optional[str] = None,
        total_objects: Optional[int] = None,
        total_bytes: Optional[int] = None
    ) -> None:
        """Update progress tracking information.
        
        Args:
            completed_objects: Number of objects completed
            transferred_bytes: Number of bytes transferred
            current_object: Name of current object being processed
            current_operation: Current operation being performed
            total_objects: Total number of objects (if known)
            total_bytes: Total number of bytes (if known)
        """
        with self._lock:
            if completed_objects is not None:
                self.completed_objects = completed_objects
            if transferred_bytes is not None:
                self.transferred_bytes = transferred_bytes
            if current_object is not None:
                self.current_object = current_object
            if current_operation is not None:
                self.current_operation = current_operation
            if total_objects is not None:
                self.total_objects = total_objects
            if total_bytes is not None:
                self.total_bytes = total_bytes
            
            # Record progress history for rate calculation
            current_time = time.time()
            self._progress_history.append((current_time, self.completed_objects, self.transferred_bytes))
            
            # Keep only recent history (last 10 entries)
            if len(self._progress_history) > 10:
                self._progress_history = self._progress_history[-10:]
    
    def get_progress(self) -> MigrationProgress:
        """Get current progress information.
        
        Returns:
            MigrationProgress object with current state and estimates
        """
        with self._lock:
            estimated_time_remaining = self._calculate_estimated_time_remaining()
            
            return MigrationProgress(
                current_object=self.current_object,
                objects_completed=self.completed_objects,
                total_objects=self.total_objects,
                bytes_transferred=self.transferred_bytes,
                total_bytes=self.total_bytes,
                estimated_time_remaining=estimated_time_remaining,
                current_operation=self.current_operation
            )
    
    def _calculate_estimated_time_remaining(self) -> Optional[float]:
        """Calculate estimated time remaining based on progress history.
        
        Returns:
            Estimated seconds remaining, or None if cannot be calculated
        """
        if len(self._progress_history) < 2:
            return None
        
        # Use the most recent progress points to calculate rate
        recent_history = self._progress_history[-5:]  # Last 5 data points
        
        if len(recent_history) < 2:
            return None
        
        # Calculate rates
        time_diff = recent_history[-1][0] - recent_history[0][0]
        objects_diff = recent_history[-1][1] - recent_history[0][1]
        bytes_diff = recent_history[-1][2] - recent_history[0][2]
        
        if time_diff <= 0:
            return None
        
        # Calculate remaining work
        remaining_objects = max(0, self.total_objects - self.completed_objects)
        remaining_bytes = max(0, self.total_bytes - self.transferred_bytes)
        
        # Estimate time based on object rate and byte rate
        estimated_times = []
        
        if objects_diff > 0 and remaining_objects > 0:
            object_rate = objects_diff / time_diff
            time_by_objects = remaining_objects / object_rate
            estimated_times.append(time_by_objects)
        
        if bytes_diff > 0 and remaining_bytes > 0:
            byte_rate = bytes_diff / time_diff
            time_by_bytes = remaining_bytes / byte_rate
            estimated_times.append(time_by_bytes)
        
        if not estimated_times:
            return None
        
        # Return the average of available estimates
        return sum(estimated_times) / len(estimated_times)
    
    @property
    def elapsed_time(self) -> float:
        """Get elapsed time since tracking started."""
        return time.time() - self.start_time
    
    @property
    def objects_per_second(self) -> float:
        """Get current objects per second rate."""
        if self.elapsed_time <= 0:
            return 0.0
        return self.completed_objects / self.elapsed_time
    
    @property
    def bytes_per_second(self) -> float:
        """Get current bytes per second rate."""
        if self.elapsed_time <= 0:
            return 0.0
        return self.transferred_bytes / self.elapsed_time


class ProgressReporter:
    """Manages progress reporting with multiple callback support."""
    
    def __init__(self) -> None:
        """Initialize progress reporter."""
        self._callbacks: List[ProgressCallback] = []
        self._tracker = ProgressTracker()
        self._lock = threading.Lock()
    
    def add_callback(self, callback: ProgressCallback) -> None:
        """Add a progress callback.
        
        Args:
            callback: Function to call with progress updates
        """
        with self._lock:
            if callback not in self._callbacks:
                self._callbacks.append(callback)
    
    def remove_callback(self, callback: ProgressCallback) -> None:
        """Remove a progress callback.
        
        Args:
            callback: Function to remove from callbacks
        """
        with self._lock:
            if callback in self._callbacks:
                self._callbacks.remove(callback)
    
    def update_progress(
        self,
        completed_objects: Optional[int] = None,
        transferred_bytes: Optional[int] = None,
        current_object: Optional[str] = None,
        current_operation: Optional[str] = None,
        total_objects: Optional[int] = None,
        total_bytes: Optional[int] = None
    ) -> None:
        """Update progress and notify all callbacks.
        
        Args:
            completed_objects: Number of objects completed
            transferred_bytes: Number of bytes transferred
            current_object: Name of current object being processed
            current_operation: Current operation being performed
            total_objects: Total number of objects (if known)
            total_bytes: Total number of bytes (if known)
        """
        # Update tracker
        self._tracker.update(
            completed_objects=completed_objects,
            transferred_bytes=transferred_bytes,
            current_object=current_object,
            current_operation=current_operation,
            total_objects=total_objects,
            total_bytes=total_bytes
        )
        
        # Get current progress
        progress = self._tracker.get_progress()
        
        # Notify all callbacks
        with self._lock:
            callbacks_to_call = self._callbacks.copy()
        
        for callback in callbacks_to_call:
            try:
                callback(progress)
            except Exception as e:
                # Log error but don't let callback failures stop progress reporting
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Progress callback failed: {e}")
    
    def get_current_progress(self) -> MigrationProgress:
        """Get current progress without triggering callbacks.
        
        Returns:
            Current migration progress
        """
        return self._tracker.get_progress()
    
    def reset(self) -> None:
        """Reset progress tracking."""
        with self._lock:
            self._tracker = ProgressTracker()


def create_console_progress_callback(show_details: bool = True) -> ProgressCallback:
    """Create a progress callback that prints to console.
    
    Args:
        show_details: Whether to show detailed progress information
        
    Returns:
        Progress callback function
    """
    def console_callback(progress: MigrationProgress) -> None:
        """Print progress to console."""
        if show_details:
            print(f"\rProgress: {progress.progress_percentage:.1f}% "
                  f"({progress.objects_completed}/{progress.total_objects} objects, "
                  f"{progress.bytes_percentage:.1f}% bytes) - {progress.current_object}", 
                  end="", flush=True)
        else:
            print(f"\rProgress: {progress.progress_percentage:.1f}%", end="", flush=True)
    
    return console_callback


def create_logging_progress_callback(
    logger_name: str = __name__,
    log_interval: int = 10
) -> ProgressCallback:
    """Create a progress callback that logs progress periodically.
    
    Args:
        logger_name: Name of logger to use
        log_interval: Log every N progress updates
        
    Returns:
        Progress callback function
    """
    import logging
    logger = logging.getLogger(logger_name)
    
    call_count = 0
    
    def logging_callback(progress: MigrationProgress) -> None:
        """Log progress periodically."""
        nonlocal call_count
        call_count += 1
        
        if call_count % log_interval == 0:
            logger.info(
                f"Migration progress: {progress.progress_percentage:.1f}% "
                f"({progress.objects_completed}/{progress.total_objects} objects, "
                f"{progress.bytes_transferred}/{progress.total_bytes} bytes)"
            )
    
    return logging_callback