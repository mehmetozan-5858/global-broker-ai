from __future__ import annotations

import shutil
import subprocess
from typing import Iterable


BROWSER_CANDIDATES: tuple[str, ...] = (
    "google-chrome",
    "google-chrome-stable",
    "chromium",
    "chromium-browser",
)


def find_browser(candidates: Iterable[str] = BROWSER_CANDIDATES) -> str | None:
    for name in candidates:
        path = shutil.which(name)
        if path:
            return path
    return None


def dump_dom(url: str, *, virtual_time_ms: int = 12000, timeout_seconds: int = 35) -> str:
    browser = find_browser()
    if not browser:
        raise RuntimeError("headless_browser_unavailable")
    completed = subprocess.run(
        [
            browser,
            "--headless=new",
            "--no-sandbox",
            "--disable-gpu",
            "--disable-dev-shm-usage",
            f"--virtual-time-budget={virtual_time_ms}",
            "--dump-dom",
            url,
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
    )
    if completed.returncode != 0:
        raise RuntimeError(f"headless_browser_failed:{completed.returncode}")
    markup = completed.stdout.strip()
    if not markup:
        raise RuntimeError("headless_browser_empty_dom")
    return markup
