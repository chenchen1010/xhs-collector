"""
Douyin signature helper for a_bogus.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

try:
    import execjs  # type: ignore
except Exception as exc:  # pragma: no cover - runtime dependency
    execjs = None
    _EXECJS_IMPORT_ERROR = exc
else:
    _EXECJS_IMPORT_ERROR = None


_SIGN_CONTEXT = None


def _load_sign_context(js_path: Path):
    global _SIGN_CONTEXT
    if _SIGN_CONTEXT is not None:
        return _SIGN_CONTEXT

    if execjs is None:
        raise RuntimeError(
            "Missing execjs runtime. Install PyExecJS and ensure Node.js is available."
        ) from _EXECJS_IMPORT_ERROR

    js_code = js_path.read_text(encoding="utf-8")
    _SIGN_CONTEXT = execjs.compile(js_code)
    return _SIGN_CONTEXT


class DouyinSigner:
    """Compute a_bogus for Douyin web endpoints."""

    def __init__(self, js_path: Optional[Path] = None) -> None:
        if js_path is None:
            js_path = Path(__file__).resolve().parent / "douyin_js" / "douyin.js"
        self._js_path = js_path

    def sign(self, query_string: str, user_agent: str) -> str:
        if not query_string:
            raise ValueError("query_string is required for a_bogus signature")
        ctx = _load_sign_context(self._js_path)
        return ctx.call("sign_datail", query_string, user_agent)
