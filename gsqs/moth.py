"""Minimal client for the Moth Atlas API (https://api.mothquantum.com, OpenAPI at /openapi.json).

Only what this session needs: upload an asset, submit an engine job, wait, fetch outputs.
The key is read from $MOTH_API_KEY or a key file and never printed.
"""
from __future__ import annotations

import os
import time
from pathlib import Path

import requests

API = "https://api.mothquantum.com"
# Cloudflare rejects anonymous client User-Agents with a 403 that looks like an auth error.
UA = "ghost-signals-quantum-session/0.1 (+https://github.com/kannaka-labs)"


class _Retryable(Exception):
    pass


class Moth:
    def __init__(self, key: str | None = None, key_file: str | os.PathLike | None = None):
        key = key or os.environ.get("MOTH_API_KEY")
        if not key and key_file:
            key = Path(key_file).read_text(encoding="utf-8").strip()
        if not key:
            raise RuntimeError("set MOTH_API_KEY or pass key_file")
        self._h = {"Authorization": f"Bearer {key}", "User-Agent": UA, "accept": "application/json"}

    def _check(self, r: requests.Response):
        if not r.ok:
            raise RuntimeError(f"HTTP {r.status_code} {r.request.method} {r.url}: {r.text[:600]}")
        return r.json() if r.content else {}

    def get(self, path: str, attempts: int = 5):
        """GET with retries on dropped connections (seen mid-poll under hackathon load)."""
        for i in range(attempts):
            try:
                return self._check(requests.get(API + path, headers=self._h, timeout=60))
            except (requests.ConnectionError, requests.Timeout):
                if i == attempts - 1:
                    raise
                time.sleep(3 * (i + 1))

    def upload(self, path: str | os.PathLike, content_type: str) -> str:
        """Stage a file as an asset (create -> PUT presigned -> complete). Returns the asset id."""
        p = Path(path)
        a = self._check(requests.post(f"{API}/api/v1/assets", headers=self._h, timeout=60, json={
            "filename": p.name, "content_type": content_type, "size_bytes": p.stat().st_size}))
        up = a["upload"]
        r = requests.put(up["url"], data=p.read_bytes(), headers=up.get("headers") or {}, timeout=300)
        if not r.ok:
            raise RuntimeError(f"upload PUT failed: HTTP {r.status_code} {r.text[:300]}")
        aid = a.get("asset_id") or a.get("id") or a["asset"]["asset_id"]
        self._check(requests.post(f"{API}/api/v1/assets/{aid}/complete", headers=self._h, timeout=60))
        return aid

    def run(self, engine: str, params: dict, input_files: dict | None = None, timeout_s: int = 1800,
            retries: int = 3) -> dict:
        """Submit a job, wait until it is terminal, return {job_id, status, result}.

        Failures the API marks `retryable` (e.g. `engine_timeout` when a worker is cold or busy) are
        resubmitted up to `retries` times with a growing pause; anything else raises at once."""
        for attempt in range(retries + 1):
            try:
                return self._run_once(engine, params, input_files, timeout_s)
            except _Retryable as e:
                if attempt == retries:
                    raise RuntimeError(str(e)) from None
                time.sleep(20 * (attempt + 1))
        raise AssertionError("unreachable")

    def _run_once(self, engine: str, params: dict, input_files: dict | None, timeout_s: int) -> dict:
        body = {"params": params}
        if input_files:
            body["input_files"] = input_files
        sub = self._check(requests.post(f"{API}/api/v1/engines/{engine}/process", headers=self._h,
                                        json=body, timeout=120))
        jid = sub["job_id"]
        t0 = time.time()
        while True:
            st = self.get(f"/api/v1/jobs/{jid}/status")
            if st.get("status") in ("completed", "failed", "cancelled", "error"):
                break
            if time.time() - t0 > timeout_s:
                raise TimeoutError(f"{engine} job {jid} still {st.get('status')} after {timeout_s}s")
            time.sleep(5)
        if st["status"] != "completed":
            msg = f"{engine} job {jid} {st['status']}: {str(st.get('error') or st)[:800]}"
            if (st.get("error") or {}).get("retryable"):
                raise _Retryable(msg)
            raise RuntimeError(msg)
        return {"job_id": jid, "engine": engine, "status": st, "result": self.get(f"/api/v1/jobs/{jid}/result")}

    @staticmethod
    def outputs(job: dict) -> dict:
        """Map output slot -> output record (with a presigned url and, when present, an asset id)."""
        res = job["result"]
        outs = res.get("outputs") or res.get("result", {}).get("outputs") or []
        return {o.get("slot") or o.get("name"): o for o in outs}

    def download(self, job: dict, slot: str, dest: str | os.PathLike) -> Path:
        o = self.outputs(job)[slot]
        url = o.get("url") or o.get("download_url")
        if not url:
            aid = o.get("asset_id") or o.get("id")
            url = self.get(f"/api/v1/assets/{aid}/download")["url"]
        r = requests.get(url, headers={"User-Agent": UA}, timeout=300)
        r.raise_for_status()
        dest = Path(dest)
        dest.write_bytes(r.content)
        return dest
