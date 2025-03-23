import json
import os
from pathlib import Path
from typing import List, Dict, Any
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class LogReader:
    """Utility class for reading and parsing log files"""
    
    def __init__(self, log_dir: str = "logs"):
        """Initialize the log reader
        
        Args:
            log_dir: Directory containing log files
        """
        self.log_dir = Path(log_dir)
    
    def get_log_files(self) -> List[Path]:
        """Get all Teldor request log files
        
        Returns:
            List of log file paths
        """
        try:
            if not self.log_dir.exists():
                logger.warning(f"Log directory {self.log_dir} does not exist")
                return []
                
            # Get all JSON files in the log directory
            log_files = list(self.log_dir.glob("teldor_request_*.json"))
            
            # Sort by modification time (newest first)
            log_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            
            return log_files
        except Exception as e:
            logger.error(f"Error getting log files: {str(e)}")
            return []
    
    def read_log_file(self, file_path: Path) -> Dict[str, Any]:
        """Read and parse a log file
        
        Args:
            file_path: Path to the log file
            
        Returns:
            Parsed log data
        """
        try:
            with open(file_path, 'r') as f:
                log_data = json.load(f)
            
            # Add filename and formatted timestamp
            log_data['filename'] = file_path.name
            
            # Format the timestamp for display
            if 'timestamp' in log_data:
                try:
                    timestamp = datetime.fromisoformat(log_data['timestamp'])
                    log_data['formatted_timestamp'] = timestamp.strftime("%Y-%m-%d %H:%M:%S")
                except:
                    log_data['formatted_timestamp'] = log_data['timestamp']
            
            return log_data
        except Exception as e:
            logger.error(f"Error reading log file {file_path}: {str(e)}")
            return {
                'error': f"Failed to read log file: {str(e)}",
                'filename': file_path.name
            }
    
    def get_all_logs(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get all logs, parsed and sorted by timestamp
        
        Args:
            limit: Maximum number of logs to return
            
        Returns:
            List of parsed log data
        """
        try:
            log_files = self.get_log_files()
            logs = []
            
            for file_path in log_files[:limit]:
                log_data = self.read_log_file(file_path)
                logs.append(log_data)
            
            return logs
        except Exception as e:
            logger.error(f"Error getting all logs: {str(e)}")
            return []
