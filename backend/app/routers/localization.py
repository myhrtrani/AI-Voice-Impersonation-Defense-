"""
REST Endpoints for Multi-Language Localization and Language-Specific Acoustic Calibration Profiles.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.logger import get_logger, log_crash
from app.db import save_persisted_config, get_persisted_config

router = APIRouter(prefix="/localization", tags=["Localization"])
logger = get_logger("voice_defense.localization")


LANGUAGES = [
    {
        "code": "en",
        "name": "English",
        "native": "English",
        "flag": "🇺🇸",
        "direction": "ltr",
        "acoustic_profile": "stress_timed",
        "description": "Standard English stress-timed rhythm with balanced high-frequency LFCC detection."
    },
    {
        "code": "es",
        "name": "Spanish",
        "native": "Español",
        "flag": "🇪🇸",
        "direction": "ltr",
        "acoustic_profile": "syllable_timed",
        "description": "Syllable-timed cadence with vowel duration calibration."
    },
    {
        "code": "fr",
        "name": "French",
        "native": "Français",
        "flag": "🇫🇷",
        "direction": "ltr",
        "acoustic_profile": "syllable_timed",
        "description": "Smooth liaison and syllable cadence with adapted nasal resonance filtering."
    },
    {
        "code": "de",
        "name": "German",
        "native": "Deutsch",
        "flag": "🇩🇪",
        "direction": "ltr",
        "acoustic_profile": "stress_timed",
        "description": "Strong consonantal clusters with high-band fricative tolerance."
    },
    {
        "code": "hi",
        "name": "Hindi",
        "native": "हिन्दी",
        "flag": "🇮🇳",
        "direction": "ltr",
        "acoustic_profile": "syllable_timed",
        "description": "Retroflex and aspirated consonant spectrum compensation."
    },
    {
        "code": "te",
        "name": "Telugu",
        "native": "తెలుగు",
        "flag": "🇮🇳",
        "direction": "ltr",
        "acoustic_profile": "syllable_timed",
        "description": "Vowel-ending phonetic cadence with adapted fundamental frequency stability."
    },
    {
        "code": "zh",
        "name": "Chinese",
        "native": "中文 (Mandarin)",
        "flag": "🇨🇳",
        "direction": "ltr",
        "acoustic_profile": "tonal",
        "description": "Four-tone contour compensation preventing pitch inflection false positives."
    },
    {
        "code": "ja",
        "name": "Japanese",
        "native": "日本語",
        "flag": "🇯🇵",
        "direction": "ltr",
        "acoustic_profile": "mora_timed",
        "description": "Mora-timed pitch accent contours and low spectral variance tuning."
    },
    {
        "code": "ar",
        "name": "Arabic",
        "native": "العربية",
        "flag": "🇸🇦",
        "direction": "rtl",
        "acoustic_profile": "stress_timed",
        "description": "Pharyngeal and emphatic consonant high-frequency resonance modeling."
    }
]

ACOUSTIC_PROFILES = {
    "stress_timed": {
        "name": "Stress-Timed Profile",
        "pitch_tolerance": 1.0,
        "lfcc_weight_bias": 0.30,
        "spectral_centroid_baseline_hz": 2200.0,
        "recommended_for": ["English", "German", "Arabic", "Russian"]
    },
    "syllable_timed": {
        "name": "Syllable-Timed Profile",
        "pitch_tolerance": 1.15,
        "lfcc_weight_bias": 0.28,
        "spectral_centroid_baseline_hz": 2400.0,
        "recommended_for": ["Spanish", "French", "Hindi", "Telugu", "Italian"]
    },
    "tonal": {
        "name": "Tonal Inflection Profile",
        "pitch_tolerance": 1.40,  # Expands pitch variance allowance for linguistic tone glides
        "lfcc_weight_bias": 0.32,
        "spectral_centroid_baseline_hz": 2100.0,
        "recommended_for": ["Chinese (Mandarin)", "Vietnamese", "Thai", "Cantonese"]
    },
    "mora_timed": {
        "name": "Mora-Timed Pitch Accent Profile",
        "pitch_tolerance": 1.10,
        "lfcc_weight_bias": 0.30,
        "spectral_centroid_baseline_hz": 2300.0,
        "recommended_for": ["Japanese", "Luganda"]
    }
}


class PreferenceRequest(BaseModel):
    language: str
    acoustic_profile: Optional[str] = None


@router.get("/languages")
async def get_languages():
    """
    Returns available system UI languages and acoustic dialect profiles.
    """
    persisted = get_persisted_config()
    current_lang = persisted.get("preferred_language", "en")
    current_profile = persisted.get("preferred_acoustic_profile", "stress_timed")

    return {
        "status": "success",
        "current_language": current_lang,
        "current_acoustic_profile": current_profile,
        "languages": LANGUAGES,
        "acoustic_profiles": ACOUSTIC_PROFILES
    }


@router.post("/preference")
async def set_localization_preference(req: PreferenceRequest):
    """
    Saves language and acoustic calibration profile preference to database.
    """
    try:
        valid_codes = [l["code"] for l in LANGUAGES]
        if req.language not in valid_codes:
            raise HTTPException(status_code=400, detail=f"Unsupported language code '{req.language}'. Choose from {valid_codes}")

        profile = req.acoustic_profile
        if not profile:
            # Auto-pick recommended profile for this language
            for l in LANGUAGES:
                if l["code"] == req.language:
                    profile = l["acoustic_profile"]
                    break

        to_save = {
            "preferred_language": req.language,
            "preferred_acoustic_profile": profile
        }
        save_persisted_config(to_save)
        logger.info("Localization preference saved: language=%s, acoustic_profile=%s", req.language, profile)

        return {
            "status": "success",
            "message": "Localization preferences saved successfully",
            "saved": to_save
        }
    except HTTPException:
        raise
    except Exception as e:
        log_crash(e, context="Set Localization Preference Endpoint")
        raise HTTPException(status_code=500, detail=f"Failed to save preference: {str(e)}")
