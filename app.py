#!/usr/bin/env python3
from __future__ import annotations

import threading
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from flask import Flask, abort, jsonify, render_template, request, send_from_directory, url_for

from image_generator import (
    DEFAULT_STYLE_KEY,
    STYLE_PRESETS,
    generate_year_image,
    get_style_presets,
    parse_year_input,
)

BASE_DIR = Path(__file__).resolve().parent
GENERATED_IMAGES_DIR = BASE_DIR / "generated_images"

app = Flask(__name__)

_jobs_lock = threading.Lock()
_jobs: dict[str, dict[str, Any]] = {}


def _utc_now() -> str:
    return datetime.utcnow().isoformat(timespec="seconds") + "Z"


def _job_payload(job: dict[str, Any]) -> dict[str, Any]:
    payload = dict(job)
    file_name = payload.get("file_name")
    payload["image_url"] = url_for("generated_image", filename=file_name) if file_name else None
    return payload


def _update_job(job_id: str, **changes: Any) -> None:
    with _jobs_lock:
        job = _jobs[job_id]
        job.update(changes)
        job["updated_at"] = _utc_now()


def _create_job(year: int, style_key: str) -> dict[str, Any]:
    style = STYLE_PRESETS[style_key]
    job_id = uuid4().hex
    job = {
        "id": job_id,
        "year": year,
        "style_key": style_key,
        "style_label": style.label,
        "status": "queued",
        "progress": 0,
        "message": "Задача поставлена в очередь",
        "description_ru": None,
        "file_name": None,
        "error": None,
        "created_at": _utc_now(),
        "updated_at": _utc_now(),
        "finished_at": None,
    }
    with _jobs_lock:
        _jobs[job_id] = job
    return job


def _run_job(job_id: str, year: int, style_key: str) -> None:
    def progress(percent: int, message: str) -> None:
        _update_job(job_id, status="running", progress=percent, message=message)

    try:
        progress(3, "Подготавливаю задачу")
        result = generate_year_image(
            year,
            style_key=style_key,
            out_dir=GENERATED_IMAGES_DIR,
            progress_callback=progress,
        )
        _update_job(
            job_id,
            status="completed",
            progress=100,
            message="Генерация завершена",
            description_ru=result.description_ru,
            file_name=result.image_path.name,
            finished_at=_utc_now(),
        )
    except Exception as exc:
        _update_job(
            job_id,
            status="error",
            progress=100,
            message="Во время генерации произошла ошибка",
            error=str(exc),
            finished_at=_utc_now(),
        )


@app.get("/")
def index() -> str:
    return render_template(
        "index.html",
        styles=get_style_presets(),
        default_style=DEFAULT_STYLE_KEY,
    )


@app.post("/api/jobs")
def create_job() -> Any:
    payload = request.get_json(silent=True) or request.form
    year_raw = str(payload.get("year", "")).strip()
    style_key = str(payload.get("style", DEFAULT_STYLE_KEY)).strip() or DEFAULT_STYLE_KEY

    year = parse_year_input(year_raw)
    if year is None:
        return jsonify(
            {
                "error": "Введите целый год, например -44, 476, 1812 или 2035. Год 0 не используется."
            }
        ), 400
    if style_key not in STYLE_PRESETS:
        return jsonify({"error": "Неизвестный стиль изображения."}), 400

    job = _create_job(year, style_key)
    worker = threading.Thread(
        target=_run_job,
        args=(job["id"], year, style_key),
        daemon=True,
    )
    worker.start()

    return jsonify({"job": _job_payload(job)})


@app.get("/api/jobs/<job_id>")
def api_job_status(job_id: str) -> Any:
    with _jobs_lock:
        job = _jobs.get(job_id)
    if job is None:
        abort(404)
    return jsonify(_job_payload(job))


@app.get("/generated/<path:filename>")
def generated_image(filename: str) -> Any:
    return send_from_directory(GENERATED_IMAGES_DIR, filename)


if __name__ == "__main__":
    GENERATED_IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    app.run(host="127.0.0.1", port=5000, debug=True, use_reloader=False)
