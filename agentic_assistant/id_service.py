# id_service.py
"""Thread-safe service for generating unique IDs across agents and tools."""

import threading
import uuid
import time

class IdService:
    """Thread-safe service for generating unique IDs and tracking relationships."""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(IdService, cls).__new__(cls)
                cls._instance._counter = 0
                cls._instance._parent_child_map = {}
                cls._instance._call_records = {}
        return cls._instance
    
    def generate_id(self, prefix="call"):
        """Generate a unique ID with optional prefix."""
        with self._lock:
            self._counter += 1
            # Combine timestamp, counter and random bits for uniqueness
            return f"{prefix}_{int(time.time() * 1000)}_{self._counter}_{uuid.uuid4().hex[:6]}"
    
    def record_call_start(self, call_id, tool_name, args=None, parent_id=None, depth=0):
        """Record the start of a tool call."""
        with self._lock:
            # Record call metadata
            self._call_records[call_id] = {
                "id": call_id,
                "tool_name": tool_name,
                "args": args or {},
                "parent_id": parent_id,
                "depth": depth,
                "start_time": time.time(),
                "status": "running"
            }
            
            # Record parent-child relationship
            if parent_id:
                if parent_id not in self._parent_child_map:
                    self._parent_child_map[parent_id] = []
                self._parent_child_map[parent_id].append(call_id)
    
    def record_call_end(self, call_id, result=None, status="success", summary=None):
        """Record the successful completion of a call."""
        with self._lock:
            if call_id in self._call_records:
                self._call_records[call_id]["end_time"] = time.time()
                self._call_records[call_id]["duration"] = (
                    self._call_records[call_id]["end_time"] - 
                    self._call_records[call_id]["start_time"]
                )
                self._call_records[call_id]["status"] = status
                self._call_records[call_id]["result_summary"] = summary or "Completed"
    
    def record_call_error(self, call_id, error="Unknown error"):
        """Record an error in a call."""
        with self._lock:
            if call_id in self._call_records:
                self._call_records[call_id]["end_time"] = time.time()
                self._call_records[call_id]["duration"] = (
                    self._call_records[call_id]["end_time"] - 
                    self._call_records[call_id]["start_time"]
                )
                self._call_records[call_id]["status"] = "error"
                self._call_records[call_id]["result_summary"] = str(error)
    
    def get_all_records(self):
        """Get all call records."""
        with self._lock:
            return list(self._call_records.values())
    
    def get_parent_child_map(self):
        """Get the parent-child relationship map."""
        with self._lock:
            return self._parent_child_map.copy()
    
    def clear_history(self):
        """Clear history but keep the counter."""
        with self._lock:
            self._parent_child_map = {}
            self._call_records = {}

# Global instance
id_service = IdService()
