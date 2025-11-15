"""
Local request queue implementation for Apify SDK.
Provides file-based storage that mimics platform request queue operations.
"""

import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Union


class LocalRequestQueue:
    """
    Local request queue implementation that stores requests to files.
    Mimics Apify request queue API for local development and testing.
    """

    def __init__(self, queue_id: str = "default", storage_dir: Optional[str] = None):
        """
        Initialize local request queue.

        Args:
            queue_id: Queue identifier (used as directory name)
            storage_dir: Base storage directory (defaults to ./storage/request_queues)
        """
        if storage_dir is None:
            # Default to storage/request_queues relative to current working directory
            storage_dir = os.path.join(os.getcwd(), "storage", "request_queues")

        self.queue_id = queue_id
        self.storage_dir = Path(storage_dir) / queue_id
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        # Queue state files
        self.pending_file = self.storage_dir / "pending.json"
        self.handled_file = self.storage_dir / "handled.json"

        # In-memory queues
        self.pending: List[Dict[str, Any]] = []
        self.handled: List[Dict[str, Any]] = []
        self._load_state()

    def _load_state(self) -> None:
        """Load queue state from files."""
        # Load pending requests
        if self.pending_file.exists():
            try:
                with open(self.pending_file, 'r', encoding='utf-8') as f:
                    self.pending = json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                self.pending = []

        # Load handled requests
        if self.handled_file.exists():
            try:
                with open(self.handled_file, 'r', encoding='utf-8') as f:
                    self.handled = json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                self.handled = []

    def _save_state(self) -> None:
        """Save queue state to files."""
        with open(self.pending_file, 'w', encoding='utf-8') as f:
            json.dump(self.pending, f, indent=2, ensure_ascii=False)

        with open(self.handled_file, 'w', encoding='utf-8') as f:
            json.dump(self.handled, f, indent=2, ensure_ascii=False)

    def add_request(self, request: Dict[str, Any], forefront: bool = False) -> str:
        """
        Add a request to the queue.

        Args:
            request: Request data (must include 'url')
            forefront: Whether to add to front of queue

        Returns:
            Request ID
        """
        if not isinstance(request, dict):
            raise ValueError("Request must be a dict")

        if 'url' not in request:
            raise ValueError("Request must include 'url' field")

        # Generate request ID
        request_id = f"req_{int(time.time() * 1000000)}"

        queue_item = {
            'id': request_id,
            'url': request['url'],
            'method': request.get('method', 'GET'),
            'headers': request.get('headers', {}),
            'payload': request.get('payload'),
            'userData': request.get('userData', {}),
            'uniqueKey': request.get('uniqueKey', request['url']),
            'addedAt': time.time()
        }

        if forefront:
            self.pending.insert(0, queue_item)
        else:
            self.pending.append(queue_item)

        self._save_state()
        return request_id

    def fetch_next_request(self) -> Optional[Dict[str, Any]]:
        """
        Fetch the next request from the queue.

        Returns:
            Next request or None if queue is empty
        """
        if not self.pending:
            return None

        request = self.pending.pop(0)
        self._save_state()
        return request

    def mark_request_as_handled(self, request: Dict[str, Any]) -> None:
        """
        Mark a request as handled.

        Args:
            request: Request that was handled
        """
        request['handledAt'] = time.time()
        self.handled.append(request)
        self._save_state()

    def reclaim_request(self, request: Dict[str, Any], forefront: bool = False) -> None:
        """
        Reclaim a request (put it back in the queue).

        Args:
            request: Request to reclaim
            forefront: Whether to add to front of queue
        """
        if forefront:
            self.pending.insert(0, request)
        else:
            self.pending.append(request)
        self._save_state()

    def get_info(self) -> Dict[str, Any]:
        """
        Get queue information.

        Returns:
            Queue metadata
        """
        return {
            "id": self.queue_id,
            "name": self.queue_id,
            "pendingRequestCount": len(self.pending),
            "handledRequestCount": len(self.handled),
            "totalRequestCount": len(self.pending) + len(self.handled),
            "storageDir": str(self.storage_dir)
        }

    def is_empty(self) -> bool:
        """
        Check if the queue is empty.

        Returns:
            True if no pending requests
        """
        return len(self.pending) == 0

    def is_finished(self) -> bool:
        """
        Check if the queue is finished (no pending requests).

        Returns:
            True if no pending requests
        """
        return self.is_empty()

    def drop(self) -> None:
        """Delete all data in the request queue."""
        import shutil
        if self.storage_dir.exists():
            shutil.rmtree(self.storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.pending = []
        self.handled = []

    def __len__(self) -> int:
        """Return the number of pending requests."""
        return len(self.pending)