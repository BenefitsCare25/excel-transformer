"""
Automatic file cleanup service for Excel Transformer
Removes files older than 15 minutes from uploads and processed folders
"""
import os
import time
import logging
import threading
import glob

logger = logging.getLogger(__name__)

class CleanupService:
    def __init__(self, upload_folder, processed_folder, ttl_minutes=15):
        self.upload_folder = upload_folder
        self.processed_folder = processed_folder
        self.ttl_seconds = ttl_minutes * 60
        self.cleanup_interval = 600  # Run every 10 minutes
        self.cleanup_thread = None

    def cleanup_job_files(self, job_id):
        """Delete all files associated with a specific job_id"""
        try:
            deleted_count = 0
            deleted_size = 0

            # Clean uploaded files
            upload_pattern = os.path.join(self.upload_folder, f"{job_id}_*")
            for filepath in glob.glob(upload_pattern):
                try:
                    size = os.path.getsize(filepath)
                    os.remove(filepath)
                    deleted_count += 1
                    deleted_size += size
                    logger.info(f"Deleted upload: {os.path.basename(filepath)}")
                except Exception as e:
                    logger.warning(f"Failed to delete {filepath}: {e}")

            # Clean processed files
            processed_pattern = os.path.join(self.processed_folder, f"{job_id}_*")
            for filepath in glob.glob(processed_pattern):
                try:
                    size = os.path.getsize(filepath)
                    os.remove(filepath)
                    deleted_count += 1
                    deleted_size += size
                    logger.info(f"Deleted processed: {os.path.basename(filepath)}")
                except Exception as e:
                    logger.warning(f"Failed to delete {filepath}: {e}")

            if deleted_count > 0:
                logger.info(f"Job {job_id}: cleaned {deleted_count} files ({deleted_size/1024:.1f}KB)")

            return deleted_count, deleted_size

        except Exception as e:
            logger.error(f"Error cleaning job {job_id} files: {e}")
            return 0, 0

    def cleanup_old_files(self):
        """Remove files older than TTL from uploads and processed folders"""
        try:
            current_time = time.time()
            folders_to_clean = [self.upload_folder, self.processed_folder]
            total_cleaned = 0
            total_size_freed = 0

            for folder in folders_to_clean:
                if not os.path.exists(folder):
                    continue

                files_cleaned = 0
                size_freed = 0

                for filename in os.listdir(folder):
                    filepath = os.path.join(folder, filename)

                    # Skip directories
                    if os.path.isdir(filepath):
                        continue

                    try:
                        # Get file age
                        file_age = current_time - os.path.getmtime(filepath)

                        # Remove if older than TTL
                        if file_age > self.ttl_seconds:
                            file_size = os.path.getsize(filepath)
                            os.remove(filepath)
                            files_cleaned += 1
                            size_freed += file_size
                            logger.info(f"TTL cleanup: {filename} (age: {file_age/60:.1f}min, size: {file_size/1024:.1f}KB)")

                    except Exception as e:
                        logger.warning(f"Failed to clean up {filename}: {e}")

                if files_cleaned > 0:
                    total_cleaned += files_cleaned
                    total_size_freed += size_freed
                    logger.info(f"Cleaned {files_cleaned} files from {folder}/ (freed {size_freed/1024:.1f}KB)")

            if total_cleaned > 0:
                logger.info(f"Total cleanup: {total_cleaned} files removed, {total_size_freed/1024/1024:.2f}MB freed")

            return total_cleaned, total_size_freed

        except Exception as e:
            logger.error(f"Error during file cleanup: {e}")
            return 0, 0

    def _cleanup_loop(self):
        """Background thread loop for periodic cleanup"""
        while True:
            try:
                time.sleep(self.cleanup_interval)
                logger.info("Running scheduled file cleanup...")
                self.cleanup_old_files()
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")

    def start_periodic_cleanup(self):
        """Start background cleanup thread"""
        if self.cleanup_thread is not None and self.cleanup_thread.is_alive():
            logger.warning("Cleanup thread already running")
            return

        self.cleanup_thread = threading.Thread(
            target=self._cleanup_loop,
            daemon=True,
            name="FileCleanupThread"
        )
        self.cleanup_thread.start()
        logger.info(f"Automatic cleanup started: running every {self.cleanup_interval/60} minutes ({self.ttl_seconds/60}min TTL)")

    def startup_cleanup(self):
        """Run cleanup on startup to remove orphaned files"""
        logger.info("Running startup cleanup for orphaned files...")
        count, size = self.cleanup_old_files()
        return count, size
