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


def _as_text(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", "replace")
    return value


def dump_dom(url: str, *, virtual_time_ms: int = 12000, timeout_seconds: int = 35) -> str:
    browser = find_browser()
    if not browser:
        raise RuntimeError("headless_browser_unavailable")
    command = [
        browser,
        "--headless=new",
        "--no-sandbox",
        "--disable-gpu",
        "--disable-dev-shm-usage",
        "--disable-background-networking",
        "--disable-component-update",
        "--disable-sync",
        f"--virtual-time-budget={virtual_time_ms}",
        "--dump-dom",
        url,
    ]
    try:
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
        markup = _as_text(completed.stdout).strip()
        if completed.returncode != 0 and not markup:
            raise RuntimeError(f"headless_browser_failed:{completed.returncode}")
    except subprocess.TimeoutExpired as exc:
        # Dynamic procurement portals can keep analytics/network connections open
        # indefinitely. Chrome may nevertheless have emitted a useful DOM before
        # the process-level timeout. Preserve that source-backed output instead of
        # discarding it merely because the browser did not exit cleanly.
        markup = _as_text(exc.stdout).strip()
        if not markup:
            raise RuntimeError("headless_browser_timeout_without_dom") from exc
    if not markup:
        raise RuntimeError("headless_browser_empty_dom")
    return markup
