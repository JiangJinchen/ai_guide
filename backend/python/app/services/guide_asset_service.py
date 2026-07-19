import base64
import hashlib
import json
import re
from pathlib import Path
from typing import Iterable

from sqlalchemy.orm import Session

from app.models import Spot, SpotGuideAsset


GUIDE_AUDIO_DIR = Path(__file__).resolve().parents[2] / "storage" / "guide-assets"
GUIDE_AUDIO_URL_PREFIX = "/api/visitor/guide-assets/audio"

GUIDE_STYLES = {
    "standard": {
        "label": "标准讲解",
        "max_chars": 320,
        "instruction": "适合普通游客，口语自然，有导游感，控制在约1分钟。",
    },
    "short": {
        "label": "精简讲解",
        "max_chars": 180,
        "instruction": "适合快速了解，突出最重要信息，控制在30秒左右。",
    },
    "deep": {
        "label": "深度讲解",
        "max_chars": 520,
        "instruction": "适合深度游览，补充文化内涵和观看提示，控制在2分钟以内。",
    },
}

VALID_VOICES = {"female", "male"}


def normalize_style(style: str | None) -> str:
    return style if style in GUIDE_STYLES else "standard"


def normalize_voice(voice: str | None) -> str:
    return voice if voice in VALID_VOICES else "female"


def spot_source_payload(spot: Spot) -> dict:
    return {
        "id": spot.id,
        "scenic_area_name": spot.scenic_area_name or "",
        "spot_name": spot.spot_name or "",
        "description": spot.description or "",
        "culture_connotation": spot.culture_connotation or "",
        "highlights": spot.highlights or "",
        "open_info": spot.open_info or "",
        "remark": spot.remark or "",
    }


def build_source_hash(spot: Spot, style: str, voice: str) -> str:
    payload = {
        "spot": spot_source_payload(spot),
        "style": normalize_style(style),
        "voice": normalize_voice(voice),
    }
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def sanitize_script_text(text: str, max_chars: int = 320) -> str:
    cleaned = str(text or "")
    cleaned = re.sub(r"<[^>]+>", "", cleaned)
    cleaned = re.sub(r"[\U00010000-\U0010ffff]", "", cleaned)
    cleaned = re.sub(r"\*\*(.*?)\*\*", r"\1", cleaned)
    cleaned = re.sub(r"`([^`]*)`", r"\1", cleaned)
    cleaned = re.sub(r"^[\s>*#-]+", "", cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r"\s+", " ", cleaned)
    cleaned = cleaned.replace("。 ", "。").strip(" \n\t")

    if len(cleaned) > max_chars:
        end = max(cleaned.rfind("。", 0, max_chars), cleaned.rfind("；", 0, max_chars), cleaned.rfind("，", 0, max_chars))
        if end < 80:
            end = max_chars
        cleaned = cleaned[:end].rstrip("，；、。 ") + "。"
    return cleaned


def build_template_script(spot: Spot, style: str = "standard") -> str:
    config = GUIDE_STYLES[normalize_style(style)]
    highlights = spot.highlights or "建筑细节、文化内涵和适合拍照的视角"
    parts = [
        f"欢迎来到{spot.spot_name}。",
        spot.description or f"这里是{spot.scenic_area_name}的重要景点。",
    ]
    if spot.culture_connotation:
        parts.append(f"它的文化内涵是：{spot.culture_connotation}")
    if highlights:
        parts.append(f"游览时可以重点关注：{highlights}")
    if spot.open_info:
        parts.append(f"开放信息请以景区当日公告为准，当前资料显示：{spot.open_info}")
    parts.append("建议您放慢脚步，结合现场景观细细感受。")
    return sanitize_script_text("".join(parts), config["max_chars"])


def build_ai_prompt(spot: Spot, style: str) -> str:
    config = GUIDE_STYLES[normalize_style(style)]
    return f"""
请基于以下景点资料，生成一段适合数字人语音播报的中文讲解稿。
要求：
1. 口语化、自然、有导游感。
2. 不使用 Markdown、表格、项目符号或 emoji。
3. 不编造资料中没有的事实。
4. 开头欢迎游客，结尾给出游览提示。
5. {config["instruction"]}
6. 字数不超过 {config["max_chars"]} 字。

景区名称：{spot.scenic_area_name or ""}
景点名称：{spot.spot_name or ""}
简介：{spot.description or ""}
文化内涵：{spot.culture_connotation or ""}
亮点：{spot.highlights or ""}
开放信息：{spot.open_info or ""}
备注：{spot.remark or ""}
""".strip()


async def request_ai_script(spot: Spot, style: str) -> str | None:
    try:
        from app.api.ai import AI_API_KEY, QWEN_API_URL, QWEN_MODEL, ai_client

        if not AI_API_KEY:
            return None

        headers = {
            "Authorization": f"Bearer {AI_API_KEY}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": QWEN_MODEL,
            "messages": [
                {"role": "system", "content": "你是景区金牌讲解员，只输出适合语音播报的纯文本。"},
                {"role": "user", "content": build_ai_prompt(spot, style)},
            ],
            "temperature": 0.45,
        }
        response = await ai_client.post(QWEN_API_URL, headers=headers, json=payload)
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        return sanitize_script_text(content, GUIDE_STYLES[normalize_style(style)]["max_chars"])
    except Exception as exc:
        print(f"[GUIDE_ASSET] AI讲解稿生成失败，使用模板降级: {exc}")
        return None


def parse_audio_data(audio_data: str | None) -> tuple[bytes | None, str]:
    if not audio_data or "," not in audio_data:
        return None, "mp3"

    header, payload = audio_data.split(",", 1)
    match = re.search(r"audio/([^;]+)", header)
    audio_type = (match.group(1) if match else "mp3").lower()
    ext = "mp3" if audio_type in {"mpeg", "mp3", "lame"} else audio_type

    try:
        return base64.b64decode(payload), ext
    except Exception:
        return None, ext


def safe_token(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_-]+", "_", value or "").strip("_") or "default"


def save_audio_file(spot_id: int, style: str, voice: str, source_hash: str, audio_data: str | None) -> tuple[str | None, str | None]:
    audio_bytes, ext = parse_audio_data(audio_data)
    if not audio_bytes:
        return None, None

    audio_dir = GUIDE_AUDIO_DIR / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)
    filename = f"spot_{spot_id}_{safe_token(style)}_{safe_token(voice)}_{source_hash[:10]}.{ext}"
    file_path = audio_dir / filename
    file_path.write_bytes(audio_bytes)
    return f"{GUIDE_AUDIO_URL_PREFIX}/{filename}", str(file_path)


def estimate_duration_seconds(script_text: str, tts_duration: float | int | None = None) -> int:
    if tts_duration:
        return max(1, int(round(float(tts_duration))))
    return max(8, int(round(len(script_text or "") / 4.2)))


def serialize_asset(asset: SpotGuideAsset | None, spot: Spot | None = None, style: str = "standard", voice: str = "female") -> dict:
    if not asset:
        return {
            "status": "missing",
            "style": normalize_style(style),
            "voice": normalize_voice(voice),
            "script_text": build_template_script(spot, style) if spot else "",
            "audio_url": "",
            "duration_seconds": 0,
            "is_stale": False,
        }

    normalized_style = normalize_style(asset.style)
    normalized_voice = normalize_voice(asset.voice)
    current_hash = build_source_hash(spot, normalized_style, normalized_voice) if spot else asset.source_hash
    return {
        "id": asset.id,
        "spot_id": asset.spot_id,
        "status": asset.status,
        "style": normalized_style,
        "voice": normalized_voice,
        "script_text": asset.script_text or "",
        "audio_url": asset.audio_url or "",
        "duration_seconds": asset.duration_seconds or 0,
        "source_hash": asset.source_hash,
        "is_stale": asset.source_hash != current_hash,
        "error_message": asset.error_message or "",
        "updated_at": asset.updated_at.isoformat() if asset.updated_at else "",
    }


def get_asset(db: Session, spot_id: int, style: str = "standard", voice: str = "female") -> SpotGuideAsset | None:
    return (
        db.query(SpotGuideAsset)
        .filter(SpotGuideAsset.spot_id == spot_id)
        .filter(SpotGuideAsset.style == normalize_style(style))
        .filter(SpotGuideAsset.voice == normalize_voice(voice))
        .first()
    )


async def generate_guide_asset(
    db: Session,
    spot: Spot,
    style: str = "standard",
    voice: str = "female",
    force: bool = False,
) -> tuple[SpotGuideAsset, bool]:
    style = normalize_style(style)
    voice = normalize_voice(voice)
    source_hash = build_source_hash(spot, style, voice)
    asset = get_asset(db, spot.id, style, voice)

    if asset and not force and asset.source_hash == source_hash and asset.status == "ready" and asset.audio_url:
        return asset, False

    script_text = await request_ai_script(spot, style)
    if not script_text:
        script_text = build_template_script(spot, style)
    script_text = sanitize_script_text(script_text, GUIDE_STYLES[style]["max_chars"])

    status = "ready"
    error_message = ""
    audio_url = None
    audio_path = None
    duration_seconds = estimate_duration_seconds(script_text)

    try:
        from app.api.ai import TTSRequest, text_to_speech

        tts_result = await text_to_speech(TTSRequest(
            text=script_text,
            voice=voice,
            reply_id=f"spot-{spot.id}-{style}-{voice}",
        ))
        audio_url = tts_result.get("audio_url") or ""
        audio_path = tts_result.get("audio_path") or None
        if not audio_url:
            audio_url, audio_path = save_audio_file(spot.id, style, voice, source_hash, tts_result.get("audio_data"))
        duration_seconds = estimate_duration_seconds(script_text, tts_result.get("duration"))
        if not audio_url:
            status = "text_only"
            error_message = tts_result.get("note") or "TTS未返回可保存的音频"
    except Exception as exc:
        status = "text_only"
        error_message = f"TTS生成失败: {exc}"

    if not asset:
        asset = SpotGuideAsset(
            spot_id=spot.id,
            style=style,
            voice=voice,
            script_text=script_text,
            source_hash=source_hash,
        )
        db.add(asset)

    asset.script_text = script_text
    asset.audio_url = audio_url
    asset.audio_path = audio_path
    asset.source_hash = source_hash
    asset.status = status
    asset.error_message = error_message
    asset.duration_seconds = duration_seconds

    db.commit()
    db.refresh(asset)
    return asset, True


def get_spot_guide_detail(db: Session, spot_id: int, style: str = "standard", voice: str = "female") -> dict | None:
    style = normalize_style(style)
    voice = normalize_voice(voice)
    spot = db.query(Spot).filter(Spot.id == spot_id).first()
    if not spot:
        return None

    asset = get_asset(db, spot_id, style, voice)
    asset_payload = serialize_asset(asset, spot, style, voice)
    return {
        "spot_id": spot_id,
        "scenic_area": spot.scenic_area_name,
        "name": spot.spot_name,
        "content": spot.description,
        "culture": spot.culture_connotation,
        "highlights": spot.highlights,
        "open_info": spot.open_info,
        "guide_asset": asset_payload,
        "speech_text": asset_payload.get("script_text") or "",
        "audio_url": asset_payload.get("audio_url") or "",
        "guide_asset_status": asset_payload.get("status") or "missing",
        "guide_asset_stale": bool(asset_payload.get("is_stale")),
    }


async def generate_assets_for_spots(
    db: Session,
    spots: Iterable[Spot],
    style: str = "standard",
    voice: str = "female",
    force: bool = False,
) -> list[dict]:
    results = []
    for spot in spots:
        try:
            asset, generated = await generate_guide_asset(db, spot, style, voice, force)
            results.append({
                **serialize_asset(asset, spot, style, voice),
                "generated": generated,
                "spot_name": spot.spot_name,
            })
        except Exception as exc:
            db.rollback()
            results.append({
                "spot_id": spot.id,
                "spot_name": spot.spot_name,
                "status": "failed",
                "generated": False,
                "error_message": str(exc),
            })
    return results
