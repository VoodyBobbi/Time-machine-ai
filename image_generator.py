#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import os
import re
import sys
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

from gigachat_prompt_enricher import (
    describe_scene_in_russian,
    enhance_prompt_for_image,
    enrich_year_prompt,
)

ProgressCallback = Callable[[int, str], None]
YEAR_INPUT_RE = re.compile(r"^-?\d+$")


@dataclass(frozen=True)
class StylePreset:
    key: str
    label: str
    description: str
    prompt_suffix: str


STYLE_PRESETS: dict[str, StylePreset] = {
    "documentary_photo": StylePreset(
        key="documentary_photo",
        label="Документальное фото",
        description="Реальный репортажный кадр с атмосферой подлинного события.",
        prompt_suffix=(
            "documentary photography, authentic reportage, truthful atmosphere, real-world environment, "
            "natural motion, grounded physical detail, candid realism, editorial photojournalism, "
            "lived-in detail, believable imperfections"
        ),
    ),
    "cinematic_photo": StylePreset(
        key="cinematic_photo",
        label="Кинофото",
        description="Красивое фотореалистичное изображение с сильным светом и глубиной.",
        prompt_suffix=(
            "cinematic photography, visually stunning but realistic, elegant composition, dramatic natural light, "
            "large-scale photographic scene, premium film still realism, realistic atmosphere, "
            "high-end full-frame camera capture, glossy but plausible futuristic materials, real optical bloom"
        ),
    ),
    "engineering_shot": StylePreset(
        key="engineering_shot",
        label="Инженерная съёмка",
        description="Максимум конструктивной правдоподобности, механики и материалов.",
        prompt_suffix=(
            "engineering photography, mechanically plausible design, realistic metal and glass, "
            "precise construction detail, industrial realism, credible technical surfaces, micro-texture detail, "
            "real manufacturing marks, non-sterile surfaces"
        ),
    ),
    "night_realism": StylePreset(
        key="night_realism",
        label="Ночной реализм",
        description="Глубокая ночная съёмка с настоящим светом, бликами и отражениями.",
        prompt_suffix=(
            "night photography, realistic reflections, wet surfaces, atmospheric darkness, believable neon and tungsten light, "
            "true photographic contrast, beautiful nocturnal realism, cinematic haze, realistic moisture in the air, "
            "neon light trails captured by a real camera"
        ),
    ),
    "industry_architecture": StylePreset(
        key="industry_architecture",
        label="Индустрия и архитектура",
        description="Индустриальные объекты, масштабные конструкции, городская среда и архитектура.",
        prompt_suffix=(
            "industrial and architectural photography, large structures, built environment realism, "
            "credible urban and industrial design, construction detail, majestic but realistic scale, "
            "weathered surfaces, true architectural materials, not utopian concept art"
        ),
    ),
}

DEFAULT_STYLE_KEY = "cinematic_photo"
REALISM_LOCK = (
    "Realism lock: actual photograph, ultra photorealistic, fine-grained material detail, "
    "real skin pores when faces are visible, natural asymmetry, physically plausible geometry, "
    "subtle weathering or pristine engineered finish where appropriate, realistic scale relationships, "
    "true atmospheric perspective, realistic reflections, believable exposure, subtle lens artifacts, "
    "not glossy CGI, not concept art, not synthetic illustration."
)


@dataclass(frozen=True)
class GenerateArgs:
    prompt: str
    out_dir: Path
    model: str
    size: str
    quality: str
    style: str


@dataclass(frozen=True)
class PreparedPrompt:
    scene_brief: str
    description_ru: str
    image_prompt: str


@dataclass(frozen=True)
class GenerationResult:
    description_ru: str
    image_path: Path
    style_key: str
    style_label: str


def parse_year_input(value: str) -> int | None:
    text = value.strip()
    if not text or not YEAR_INPUT_RE.fullmatch(text):
        return None

    year = int(text)
    if year == 0:
        return None
    return year


def format_year_label(year: int) -> str:
    if year < 0:
        return f"{abs(year)} до н. э."
    return str(year)


def get_style_presets() -> list[StylePreset]:
    return list(STYLE_PRESETS.values())


def get_style_preset(style_key: str) -> StylePreset:
    return STYLE_PRESETS.get(style_key, STYLE_PRESETS[DEFAULT_STYLE_KEY])


def _report_progress(callback: ProgressCallback | None, percent: int, message: str) -> None:
    if callback is not None:
        callback(percent, message)


def _get_api_key() -> str:
    base_dir = Path(__file__).resolve().parent
    load_dotenv(base_dir / ".env")
    load_dotenv()

    key = os.getenv("OPENAI_KEY") or os.getenv("OPENAI_API_KEY")
    if not key:
        print(
            "Error: OpenAI API key not found.\n"
            "Set OPENAI_KEY (or OPENAI_API_KEY) in environment or .env.\n"
            "PowerShell: $env:OPENAI_KEY=\"your-key\"\n"
            "CMD: set OPENAI_KEY=your-key\n"
            "Linux/Mac: export OPENAI_KEY=your-key",
            file=sys.stderr,
        )
        raise SystemExit(2)
    return key


def _slugify(text: str, max_len: int = 40) -> str:
    text = text.strip().lower()
    text = re.sub(r"\s+", "_", text)
    text = re.sub(r"[^a-z0-9а-яё_\-]+", "", text, flags=re.IGNORECASE)
    text = re.sub(r"_+", "_", text).strip("_")
    return (text[:max_len] or "prompt").strip("_")


def prepare_prompt(
    prompt: str,
    progress_callback: ProgressCallback | None = None,
) -> PreparedPrompt:
    scene_brief = prompt
    year = parse_year_input(prompt)

    _report_progress(progress_callback, 5, "Проверяю входные данные")

    if year is not None:
        _report_progress(
            progress_callback,
            18,
            f"GigaChat собирает исторический и событийный контекст по году {format_year_label(year)}",
        )
        scene_brief = enrich_year_prompt(year)
    else:
        _report_progress(progress_callback, 18, "Использую введённый текст как основу сцены")

    _report_progress(progress_callback, 42, "GigaChat пишет отдельное описание для пользователя")
    description_ru = describe_scene_in_russian(scene_brief)

    _report_progress(progress_callback, 64, "GigaChat создаёт отдельный prompt для изображения")
    image_prompt = enhance_prompt_for_image(scene_brief)

    return PreparedPrompt(
        scene_brief=scene_brief,
        description_ru=description_ru,
        image_prompt=image_prompt,
    )


def build_styled_image_prompt(image_prompt: str, style_key: str) -> tuple[str, StylePreset]:
    style_preset = get_style_preset(style_key)
    styled_prompt = (
        f"{image_prompt}\n\n"
        f"Style direction: {style_preset.prompt_suffix}, breathtaking but believable beauty, "
        "gorgeous realistic light, exquisite micro-details, dense environmental detail, rich but natural colors, "
        "beautiful composition, full-frame real photography, premium lens rendering, realistic lens behavior, "
        "subtle atmospheric depth, natural imperfections, tactile material realism, not stylized, no illustration.\n\n"
        f"{REALISM_LOCK}"
    )
    return styled_prompt, style_preset


def generate_from_prompt(
    prompt: str,
    *,
    style_key: str = DEFAULT_STYLE_KEY,
    out_dir: Path = Path("generated_images"),
    model: str = "gpt-image-1",
    size: str = "1024x1024",
    quality: str = "high",
    progress_callback: ProgressCallback | None = None,
) -> GenerationResult:
    out_dir.mkdir(parents=True, exist_ok=True)

    prepared = prepare_prompt(prompt, progress_callback=progress_callback)
    styled_image_prompt, style_preset = build_styled_image_prompt(prepared.image_prompt, style_key)

    _report_progress(progress_callback, 78, f"Применяю стиль «{style_preset.label}»")
    client = OpenAI(api_key=_get_api_key())

    _report_progress(progress_callback, 88, "OpenAI создаёт очень детализированное фотореалистичное изображение")
    response = client.images.generate(
        model=model,
        prompt=styled_image_prompt,
        size=size,
        quality=quality,
        n=1,
    )

    item = response.data[0]
    image_bytes: bytes | None = None

    if getattr(item, "b64_json", None):
        image_bytes = base64.b64decode(item.b64_json)
    elif getattr(item, "url", None):
        with urllib.request.urlopen(item.url) as stream:  # nosec - URL comes from provider response
            image_bytes = stream.read()

    if not image_bytes:
        print("Error: provider returned no image bytes.", file=sys.stderr)
        raise SystemExit(1)

    _report_progress(progress_callback, 96, "Сохраняю итоговую картинку")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_name = f"{timestamp}_{_slugify(prompt)}_{style_preset.key}.png"
    image_path = out_dir / file_name
    image_path.write_bytes(image_bytes)

    _report_progress(progress_callback, 100, "Готово")
    return GenerationResult(
        description_ru=prepared.description_ru,
        image_path=image_path,
        style_key=style_preset.key,
        style_label=style_preset.label,
    )


def generate_year_image(
    year: int,
    *,
    style_key: str = DEFAULT_STYLE_KEY,
    out_dir: Path = Path("generated_images"),
    model: str = "gpt-image-1",
    size: str = "1024x1024",
    quality: str = "high",
    progress_callback: ProgressCallback | None = None,
) -> GenerationResult:
    return generate_from_prompt(
        str(year),
        style_key=style_key,
        out_dir=out_dir,
        model=model,
        size=size,
        quality=quality,
        progress_callback=progress_callback,
    )


def _parse_args(argv: list[str]) -> GenerateArgs:
    parser = argparse.ArgumentParser(
        prog="image_generator",
        description="CLI image generator via OpenAI. Key: env OPENAI_KEY.",
    )
    parser.add_argument("prompt", nargs="?", help="Prompt or year.")
    parser.add_argument(
        "--out",
        default="generated_images",
        help="Output directory (default: generated_images).",
    )
    parser.add_argument("--model", default="gpt-image-1", help="Image model.")
    parser.add_argument("--size", default="1024x1024", help="Size (e.g. 1024x1024).")
    parser.add_argument(
        "--quality",
        default="high",
        choices=["low", "medium", "high", "auto"],
        help="Quality (low, medium, high, auto).",
    )
    parser.add_argument(
        "--style",
        default=DEFAULT_STYLE_KEY,
        choices=sorted(STYLE_PRESETS.keys()),
        help="Preset style for the final image.",
    )
    options = parser.parse_args(argv)

    prompt = (options.prompt or "").strip()
    if not prompt:
        prompt = input("Введите год или текстовый промт: ").strip()
    if not prompt:
        print("Error: prompt must not be empty.", file=sys.stderr)
        raise SystemExit(2)

    return GenerateArgs(
        prompt=prompt,
        out_dir=Path(options.out),
        model=options.model,
        size=options.size,
        quality=options.quality,
        style=options.style,
    )


def _cli_progress(percent: int, message: str) -> None:
    print(f"[{percent:>3}%] {message}")


def main(argv: list[str] | None = None) -> int:
    try:
        args = _parse_args(list(sys.argv[1:] if argv is None else argv))
        result = generate_from_prompt(
            args.prompt,
            style_key=args.style,
            out_dir=args.out_dir,
            model=args.model,
            size=args.size,
            quality=args.quality,
            progress_callback=_cli_progress,
        )
        print("\nОписание ситуации:\n")
        print(result.description_ru)
        print()
        print(f"Стиль: {result.style_label}")
        print(f"Готово: {result.image_path.resolve()}")
        return 0
    except KeyboardInterrupt:
        print("\nОперация отменена пользователем.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
