import json
import logging
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class RequestLogger:
    """Utility class for logging API requests to files"""
    
    def __init__(self, log_dir: str = "logs"):
        """Initialize the request logger
        
        Args:
            log_dir: Directory to store log files
        """
        self.log_dir = Path(log_dir)
        self._ensure_log_dir()
        self.request_logs = {}  # Track request IDs to filenames
    
    def _ensure_log_dir(self):
        """Ensure the log directory exists"""
        os.makedirs(self.log_dir, exist_ok=True)
        
    def log_teldor_request(self, request_data: Dict[str, Any], response_data: Optional[Dict[str, Any]] = None) -> str:
        """Log a Teldor request to a file
        
        Args:
            request_data: The Teldor request data
            response_data: Optional response data
            
        Returns:
            The request ID
        """
        try:
            # Generate a unique request ID based on timestamp and request data
            request_id = str(request_data.get('ICL_POST_ID', '')) + '_' + str(datetime.now().timestamp())
            
            # Check if we've already logged this request
            if request_id in self.request_logs:
                # Update existing log file with response data
                return self._update_log(request_id, response_data)
            
            # Create a timestamp for the filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            
            # Create a log entry
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "request": request_data
            }
            
            if response_data:
                log_entry["response"] = response_data
                
            # Create the log filename
            filename = f"teldor_request_{timestamp}.json"
            file_path = self.log_dir / filename
            
            # Write the log to file
            with open(file_path, 'w') as f:
                json.dump(log_entry, f, indent=2, default=str)
            
            # Store the mapping of request ID to filename
            self.request_logs[request_id] = file_path
                
            logger.info(f"Teldor request logged to {file_path}")
            return request_id
            
        except Exception as e:
            logger.error(f"Error logging Teldor request: {str(e)}")
            return str(uuid.uuid4())  # Return a random ID in case of error
    
    def _update_log(self, request_id: str, response_data: Dict[str, Any]) -> str:
        """Update an existing log file with response data
        
        Args:
            request_id: The request ID
            response_data: The response data to add
            
        Returns:
            The request ID
        """
        try:
            if request_id not in self.request_logs:
                logger.warning(f"No log file found for request ID {request_id}")
                return request_id
                
            file_path = self.request_logs[request_id]
            
            # Read the existing log
            with open(file_path, 'r') as f:
                log_entry = json.load(f)
            
            # Update with response data
            log_entry["response"] = response_data
            log_entry["updated_at"] = datetime.now().isoformat()
            
            # Write the updated log
            with open(file_path, 'w') as f:
                json.dump(log_entry, f, indent=2, default=str)
                
            logger.info(f"Updated log for request ID {request_id} at {file_path}")
            return request_id
            
        except Exception as e:
            logger.error(f"Error updating log for request ID {request_id}: {str(e)}")
            return request_id
