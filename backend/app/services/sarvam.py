"""
Sarvam AI voice service — STT (Saaras), Translate (Mayura), TTS (Bulbul).

Pipeline:
  1. Student sends audio in any Indian language
  2. Saaras STT → text + detected language
  3. Mayura Translate → English (if not already English)
  4. LLM generates answer in English
  5. Mayura Translate → back to student's language
  6. Bulbul TTS → audio response
"""
import base64
import logging
from typing import Optional

import httpx

from app.config import SARVAM_API_KEY

logger = logging.getLogger(__name__)

SARVAM_BASE = "https://api.sarvam.ai"

SUPPORTED_LANGUAGES = {
    "hi-IN": "Hindi",
    "bn-IN": "Bengali",
    "ta-IN": "Tamil",
    "te-IN": "Telugu",
    "mr-IN": "Marathi",
    "gu-IN": "Gujarati",
    "kn-IN": "Kannada",
    "ml-IN": "Malayalam",
    "pa-IN": "Punjabi",
    "od-IN": "Odia",
    "en-IN": "English",
}


def _headers():
    return {
        "api-subscription-key": SARVAM_API_KEY,
        "Content-Type": "application/json",
    }


def is_configured() -> bool:
    return bool(SARVAM_API_KEY)


async def speech_to_text(audio_b64: str, language_code: str = "unknown") -> dict:
    async with httpx.AsyncClient(timeout=30) as client:
        payload = {
            "input": audio_b64,
            "config": {"language": {"sourceLanguage": language_code}},
        }
        resp = await client.post(
            f"{SARVAM_BASE}/speech-to-text",
            headers=_headers(),
            json=payload,
        )
        resp.raise_for_status()
        data = resp.json()
        return {
            "transcript": data.get("transcript", ""),
            "language": data.get("languageCode", language_code),
        }


async def translate_text(text: str, source_lang: str, target_lang: str) -> str:
    if source_lang == target_lang:
        return text
    async with httpx.AsyncClient(timeout=20) as client:
        payload = {
            "input": text,
            "source_language_code": source_lang,
            "target_language_code": target_lang,
            "mode": "formal",
            "model": "mayura:v1",
            "enable_preprocessing": True,
        }
        resp = await client.post(
            f"{SARVAM_BASE}/translate",
            headers=_headers(),
            json=payload,
        )
        resp.raise_for_status()
        return resp.json().get("translated_text", text)


async def text_to_speech(text: str, language_code: str = "hi-IN", speaker: str = "meera") -> str:
    async with httpx.AsyncClient(timeout=30) as client:
        payload = {
            "inputs": [text[:500]],
            "target_language_code": language_code,
            "speaker": speaker,
            "model": "bulbul:v1",
        }
        resp = await client.post(
            f"{SARVAM_BASE}/text-to-speech",
            headers=_headers(),
            json=payload,
        )
        resp.raise_for_status()
        data = resp.json()
        audios = data.get("audios", [])
        return audios[0] if audios else ""


async def voice_tutor_pipeline(
    audio_b64: str,
    classroom_id: str,
    user_id: str,
    language_code: str = "hi-IN",
) -> dict:
    from app.classroom import chat_with_tutor

    stt_result = await speech_to_text(audio_b64, language_code)
    student_text = stt_result["transcript"]
    detected_lang = stt_result.get("language", language_code)

    if not student_text.strip():
        return {"error": "Could not understand the audio. Please try again."}

    if detected_lang != "en-IN":
        english_text = await translate_text(student_text, detected_lang, "en-IN")
    else:
        english_text = student_text

    tutor_msg = chat_with_tutor(classroom_id, user_id, english_text)
    english_reply = tutor_msg.content

    if detected_lang != "en-IN":
        reply_in_lang = await translate_text(english_reply, "en-IN", detected_lang)
    else:
        reply_in_lang = english_reply

    audio_b64_response = await text_to_speech(reply_in_lang, detected_lang)

    return {
        "student_text": student_text,
        "student_text_english": english_text,
        "tutor_reply_english": english_reply,
        "tutor_reply": reply_in_lang,
        "audio_b64": audio_b64_response,
        "language": detected_lang,
    }
