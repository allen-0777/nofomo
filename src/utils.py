import json
import threading
from pathlib import Path
from typing import Any, Dict, List, Union

# ---------------------------------------------------------------------------
# 線程安全的 JSON 檔案操作
# ---------------------------------------------------------------------------
_file_locks: Dict[str, threading.Lock] = {}
_file_locks_lock = threading.Lock()

def get_file_lock(filepath: Union[str, Path]) -> threading.Lock:
    """取得或建立對應檔案的鎖（thread-safe）"""
    filepath = str(filepath)
    with _file_locks_lock:
        if filepath not in _file_locks:
            _file_locks[filepath] = threading.Lock()
        return _file_locks[filepath]

def safe_json_write(filepath: Union[str, Path], data: Any):
    """Thread-safe JSON 寫入"""
    lock = get_file_lock(filepath)
    with lock:
        # 確保目錄存在
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as fp:
            json.dump(data, fp, ensure_ascii=False, indent=2)

def safe_json_read(filepath: Union[str, Path], default: Any = None) -> Any:
    """Thread-safe JSON 讀取"""
    path_obj = Path(filepath)
    if not path_obj.exists():
        return default if default is not None else {}
        
    lock = get_file_lock(filepath)
    with lock:
        try:
            with open(filepath, 'r', encoding='utf-8') as fp:
                return json.load(fp)
        except json.JSONDecodeError:
            return default if default is not None else {}
