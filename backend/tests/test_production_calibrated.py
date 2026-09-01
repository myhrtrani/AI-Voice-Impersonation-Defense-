import os
import sys
import numpy as np

# ensure workspace package imports resolve during tests
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.models.aasist import pad_to_aasist_length
from app.scoring.calibrated import agg_mean
from app.routers.stream import process_audio_chunk
from app.config import settings


def test_pad_to_aasist_length_zero_pad():
    x = np.zeros(100, dtype=np.float32)
    padded = pad_to_aasist_length(x, max_len=64600)
    assert len(padded) == 64600
    assert np.allclose(padded[:100], x)
    assert np.allclose(padded[100:], 0.0)


def test_agg_mean_basic():
    probs = [0.0, 0.5, 1.0]
    assert abs(agg_mean(probs) - (sum(probs) / len(probs))) < 1e-6


def test_process_audio_chunk_short_audio_returns_zero_model_score():
    # Tiny audio shorter than 200ms should trigger early return model_score 0.0
    tiny = np.zeros(int(0.1 * settings.AUDIO.SAMPLE_RATE), dtype=np.float32)  # 100ms
    res = process_audio_chunk(
        audio_data=tiny,
        sr=settings.AUDIO.SAMPLE_RATE,
        session_id="test-session",
        chunk_index=1,
        previous_rolling_score=None,
        previous_severity="NORMAL",
        transaction_context="general",
        elapsed_seconds=0.0,
        context_audio=None,
        actual_chunk_duration_sec=0.1,
        actual_chunk_samples=len(tiny),
        total_audio_duration_sec=0.1,
        is_padded=False
    )
    # model_score should be present and 0.0
    assert 'features' in res
    assert res['features']['model_score'] == 0.0


if __name__ == '__main__':
    import pytest
    pytest.main([__file__])
