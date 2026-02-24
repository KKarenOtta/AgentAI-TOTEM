import queue
from collections import defaultdict
from typing import Dict, Any

_company_queues: Dict[str, "queue.Queue[Dict[str, Any]]"] = defaultdict(queue.Queue)

def publish(company_id: str, event: Dict[str, Any]) -> None:
    _company_queues[company_id].put(event)

def get_queue(company_id: str) -> "queue.Queue[Dict[str, Any]]":
    return _company_queues[company_id]