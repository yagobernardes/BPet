from __future__ import annotations

from pathlib import Path
from typing import Dict, Any
import numpy as np

def export_csv(path: str | Path, t: np.ndarray, y: np.ndarray, headers: list[str]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    data = np.column_stack([t.reshape(-1, 1), y.T])
    cols = ["t_s"] + headers
    header_line = ",".join(cols)

    np.savetxt(path, data, delimiter=",", header=header_line, comments="")