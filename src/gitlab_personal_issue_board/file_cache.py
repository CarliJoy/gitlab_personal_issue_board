from pathlib import Path
from typing import TypeVar

type Mtime = int
type Ctime = int
type FileSize = int
type FileCacheInfo = tuple[Mtime, Ctime, FileSize]

T_ID = TypeVar("T_ID", bound=int)


def get_file_cache_info(file: Path) -> FileCacheInfo:
    stat = file.stat()
    return stat.st_mtime_ns, stat.st_ctime_ns, stat.st_size
