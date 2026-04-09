#!/usr/bin/env python3
from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from gigachat import GigaChat


YEAR_ANALYST_SYSTEM_PROMPT = """
Ты аналитик исторических, общественных, научных, технологических и культурных процессов.

Сначала собери как можно более широкий контекст по указанному году. Нужно учитывать не один-два сюжета, а заметное количество значимых событий, процессов и визуальных признаков эпохи.

Твоя задача:
1. Если год уже прошёл или идёт сейчас, опирайся на реальные события и исторический контекст этого года.
2. Если год находится в будущем, опирайся на текущие тенденции, публичные прогнозы и вероятные сценарии, не выдавая предположения за факты.
3. Охватывай сразу несколько сфер: войны и конфликты, политика, общество, наука, технологии, экономика, транспорт, архитектура, индустрия, культура, медиа, климат, катастрофы, повседневная среда.
4. Для исторических годов обязательно ищи не только глобальные события, но и события, по которым этот год прочно узнаётся в национальной или региональной памяти: войны, ключевые битвы, осады, реформы, революции, экспедиции, открытия, архитектурные и индустриальные рубежи.
5. Если год тесно ассоциируется с конкретным событием, обязательно отражай его в основе сцены. Пример: для 1812 важно учитывать войну с Наполеоном, Бородинское сражение, пожар Москвы и атмосферу военной кампании.
6. Внутренне ориентируйся как минимум на 10-15 заметных событий, процессов или символов года, а затем сожми их в насыщенную сценическую основу.
7. Верни именно аналитическую сценическую основу на русском языке, которую потом можно отдельно превратить в текст для пользователя и отдельно в prompt для изображения.

Требования к ответу:
- Не пиши как готовый рассказ для пользователя.
- Не пиши как prompt для генератора изображений.
- Дай 5-7 плотных предложений.
- Покажи масштаб года через несколько разных событий и признаков эпохи.
- Включай людей, пространства, объекты, одежду, транспорт, архитектуру, промышленность, материалы, свет, атмосферу и ощущение времени.
- Для будущего используй осторожные формулировки: «вероятно», «можно ожидать», «в одном из вероятных сценариев».
""".strip()

TEXT_DESCRIPTION_SYSTEM_PROMPT = """
Ты пишешь краткое человеческое описание ситуации для пользователя.

Получив аналитическую сценическую основу, создай отдельный текст на русском языке.

Требования:
- 1-2 абзаца.
- Естественный, живой русский язык.
- Без списков, без заголовка, без служебных пояснений.
- Передавай обстоятельства и атмосферу понятно для человека.
- Упоминай несколько ключевых событий и признаков года, а не только один мотив.
- Если речь о будущем, сохраняй вероятностный характер и не подавай прогноз как факт.
""".strip()

IMAGE_ENHANCER_SYSTEM_PROMPT = """
Ты создаёшь именно prompt для генерации фотореалистичного изображения.

Получив аналитическую сценическую основу, сделай отдельный подробный prompt на английском языке.
Этот prompt должен отличаться от текста для пользователя: не пересказывай сцену литературно, а преобразуй её в визуальную инструкцию для одного очень красивого и очень реалистичного кадра.

Требования:
- Верни только итоговый image prompt на английском языке.
- Возьми из широкого контекста года 3-5 самых сильных и совместимых визуальных мотивов и собери их в одну цельную сцену.
- Сцена должна читаться как one coherent real photograph, а не как коллаж или набор разрозненных символов.
- Делай изображение как real photo, ultra realistic, highly detailed, physically plausible, visually stunning.
- Укажи композицию, ракурс, масштаб, свет, реальные материалы, фактуры, атмосферу, глубину кадра и характер оптики камеры.
- Подчёркивай красоту кадра через красивый естественный или кинематографичный свет, богатую, но правдоподобную цветопередачу и впечатляющую детализацию.
- Люди, техника, архитектура, оружие, одежда, механизмы и среда должны выглядеть материально и исторически правдоподобно.
- Добавляй реальные несовершенства среды: лёгкий износ, пыль, влажность, микрофактуру материалов, следы эксплуатации, естественную неоднородность поверхностей, правдоподобные погодные эффекты.
- Если в кадре есть люди, они должны выглядеть как настоящие живые люди, а не как стилизованные фигурки: realistic faces, skin texture, natural posture, candid body language.
- Используй лексику photographic realism, editorial photography, documentary realism, high-end real camera capture.
- Для футуристических сцен допустимы стерильная эстетика, гладкие блестящие металлические поверхности, неоновые шлейфы, чистая архитектура будущего, стекло, хром, холодный свет и визуальная эффектность, если это соответствует году и сцене.
- Но даже при футуристической стерильности изображение должно читаться как настоящее фото: realistic reflections, real optical bloom, believable exposure, subtle lens artifacts, camera-captured atmosphere, not a render.
- Избегай рисованности, иллюстративности, мультяшности, плакатности, matte painting, fantasy art, concept art и CGI-look.
- Если сцена про будущее, она должна выглядеть как убедимая реальная фотография из будущего мира, а не как концепт-арт.
- Если сцена относится к эпохе до изобретения фотографии, всё равно подавай её как максимально реалистичную живую реконструкцию, снятую как настоящее фото высокого класса.
""".strip()

IMAGE_STYLE_BOOST = (
    "photorealistic real-world scene, ultra realistic photography, atmospheric editorial photo, "
    "breathtaking but believable beauty, exquisite natural and cinematic light, authentic textures, "
    "physically plausible materials, premium full-frame camera look, subtle lens compression, "
    "rich but realistic colors, extremely sharp micro-details, realistic skin texture, realistic wear and tear, "
    "natural imperfections, grounded environmental detail, elegant composition, single coherent scene, "
    "sleek futuristic surfaces, polished metal, neon light trails and clean architecture are allowed when justified, "
    "but the frame must still read as real photography, "
    "not concept art, not matte painting, not illustration, not painting, not cartoon, not fantasy art, not CGI render look"
)


@dataclass(frozen=True)
class GigaChatConfig:
    credentials: str
    scope: str
    model: str | None
    base_url: str | None
    verify_ssl_certs: bool


def _as_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if hasattr(value, "dict"):
        return value.dict()
    if hasattr(value, "model_dump"):
        return value.model_dump()
    return {}


def _extract_text_from_response(response: Any) -> str:
    payload = _as_dict(response)
    choices = payload.get("choices") or []
    if not choices:
        raise RuntimeError("GigaChat returned no choices.")
    message = _as_dict(choices[0].get("message"))
    text = (message.get("content") or "").strip()
    if not text:
        raise RuntimeError("GigaChat returned empty text.")
    return text


def _build_year_user_prompt(year: int, current_year: int) -> str:
    if year > current_year:
        return (
            f"Год: {year}\n"
            f"Текущий год для сравнения: {current_year}\n\n"
            "Собери максимально широкий контекст о мировой политике, конфликтах, технологиях, науке, экономике, обществе, "
            "климате, архитектуре, городской среде, индустрии и культуре. "
            "На этой основе создай правдоподобную сценическую основу для указанного будущего года. "
            "Внутренне учитывай большое число заметных процессов и событий, но в ответе собери их в одну цельную основу сцены."
        )

    if year < 0:
        return (
            f"Год: {year}\n"
            "Это год до нашей эры.\n\n"
            "Собери широкий исторический контекст: государства и империи, войны и битвы, правителей, религию, торговлю, "
            "архитектуру, оружие, одежду, транспорт, ремёсла, городскую среду и повседневную атмосферу времени. "
            "Сформируй насыщенную сценическую основу, в которой чувствуется масштаб эпохи и историческая конкретика."
        )

    if year < 1000:
        return (
            f"Год: {year}\n\n"
            "Собери широкий исторический контекст для этого года: важные войны, битвы, походы, реформы, религиозные события, "
            "династии, государства, архитектуру, ремёсла, транспорт, оружие, одежду, городскую и сельскую среду. "
            "Сформируй насыщенную сценическую основу, где ощущаются конкретные признаки эпохи."
        )

    return (
        f"Год: {year}\n\n"
        "Собери как можно более широкую информацию о ключевых мировых событиях, конфликтах, научных прорывах, технологиях, "
        "экономике, климатических событиях, культуре, архитектуре, городской среде, индустрии и общественном настроении этого года. "
        "Если год ассоциируется с конкретным известным событием или битвой, обязательно учитывай это. "
        "На этой основе создай насыщенную сценическую основу, в которой чувствуется масштаб и узнаваемость года."
    )


def load_gigachat_config() -> GigaChatConfig:
    base_dir = Path(__file__).resolve().parent
    load_dotenv(base_dir / ".env")
    load_dotenv()

    credentials = os.getenv("GIGACHAT_CREDENTIALS", "").strip()
    if not credentials:
        raise RuntimeError(
            "GigaChat credentials not found. Set GIGACHAT_CREDENTIALS in .env or env vars."
        )

    scope = os.getenv("GIGACHAT_SCOPE", "GIGACHAT_API_PERS").strip() or "GIGACHAT_API_PERS"
    model = os.getenv("GIGACHAT_MODEL", "").strip() or None
    base_url = os.getenv("GIGACHAT_BASE_URL", "").strip() or None
    verify_ssl = os.getenv("GIGACHAT_VERIFY_SSL_CERTS", "false").strip().lower() == "true"
    return GigaChatConfig(
        credentials=credentials,
        scope=scope,
        model=model,
        base_url=base_url,
        verify_ssl_certs=verify_ssl,
    )


def _pick_working_model(giga: GigaChat, requested_model: str | None) -> str | None:
    try:
        models_payload = _as_dict(giga.get_models())
        items = models_payload.get("data") or []
        model_ids: list[str] = []
        for item in items:
            info = _as_dict(item)
            model_id = str(info.get("id_", "") or info.get("id", "")).strip()
            if model_id:
                model_ids.append(model_id)

        if requested_model and requested_model in model_ids:
            return requested_model

        for model_id in model_ids:
            if "lite" in model_id.lower():
                return model_id
        if model_ids:
            return model_ids[0]
    except Exception:
        return requested_model

    if requested_model:
        return None
    return None


def _chat_with_model_fallback(giga: GigaChat, payload: dict[str, Any], model_id: str | None) -> Any:
    try:
        return giga.chat({**({"model": model_id} if model_id else {}), **payload})
    except Exception as exc:
        if "No such model" in str(exc) and model_id:
            return giga.chat(payload)
        raise


def _chat_text(messages: list[dict[str, str]], temperature: float = 0.7) -> str:
    config = load_gigachat_config()
    with GigaChat(
        credentials=config.credentials,
        scope=config.scope,
        base_url=config.base_url,
        verify_ssl_certs=config.verify_ssl_certs,
    ) as giga:
        model_id = _pick_working_model(giga, config.model)
        response = _chat_with_model_fallback(
            giga,
            {"messages": messages, "temperature": temperature},
            model_id,
        )
    return _extract_text_from_response(response)


def enrich_year_prompt(year: int) -> str:
    current_year = datetime.now().year
    return _chat_text(
        [
            {"role": "system", "content": YEAR_ANALYST_SYSTEM_PROMPT},
            {"role": "user", "content": _build_year_user_prompt(year, current_year)},
        ],
        temperature=0.75,
    )


def describe_scene_in_russian(scene_brief: str) -> str:
    return _chat_text(
        [
            {"role": "system", "content": TEXT_DESCRIPTION_SYSTEM_PROMPT},
            {"role": "user", "content": scene_brief},
        ],
        temperature=0.6,
    )


def enhance_prompt_for_image(scene_brief: str) -> str:
    prompt = _chat_text(
        [
            {"role": "system", "content": IMAGE_ENHANCER_SYSTEM_PROMPT},
            {"role": "user", "content": scene_brief},
        ],
        temperature=0.85,
    )
    return f"{prompt}\n\n{IMAGE_STYLE_BOOST}"
