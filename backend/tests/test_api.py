import io
import wave
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from voicebox.config import Settings
from voicebox.main import create_app
from voicebox.stt import Segment, Transcription
from voicebox.tts import VoiceInfo
from voicebox.tts.piper_engine import PiperEngine, VoiceNotFound, parse_voice_id


def make_wav(seconds: float = 0.1, rate: int = 16000) -> bytes:
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(b"\x00\x00" * int(seconds * rate))
    return buffer.getvalue()


class FakeTTS:
    def __init__(self):
        self.calls = []

    def list_voices(self):
        return [VoiceInfo("it_IT-paola-medium", "Paola", "it_IT", "medium", True)]

    def download_voice(self, voice_id):
        parse_voice_id(voice_id)
        return VoiceInfo(voice_id, "X", "it_IT", "medium", True)

    def synthesize(self, text, voice_id, speed=1.0):
        if voice_id != "it_IT-paola-medium":
            raise VoiceNotFound(voice_id)
        self.calls.append((text, voice_id, speed))
        return make_wav()


class FakeSTT:
    def __init__(self):
        self.calls = []

    def list_models(self):
        return ["tiny", "small"]

    def transcribe(self, audio_path, language=None, model=None, translate=False):
        self.calls.append((Path(audio_path).read_bytes(), language, model, translate))
        return Transcription(
            text="ciao mondo",
            language=language or "it",
            language_probability=0.99,
            duration=1.0,
            segments=[Segment(0.0, 1.0, "ciao mondo")],
        )


@pytest.fixture
def client(tmp_path):
    settings = Settings(data_dir=tmp_path, frontend_dist=tmp_path / "nodist")
    tts, stt = FakeTTS(), FakeSTT()
    c = TestClient(create_app(settings, tts=tts, stt=stt))
    c.tts, c.stt = tts, stt
    return c


def test_health(client):
    assert client.get("/api/health").json() == {"status": "ok"}


def test_list_voices(client):
    voices = client.get("/api/tts/voices").json()
    assert voices[0]["id"] == "it_IT-paola-medium"
    assert voices[0]["installed"] is True


def test_synthesize_returns_wav(client):
    r = client.post("/api/tts", json={"text": " Ciao! ", "voice": "it_IT-paola-medium", "speed": 1.5})
    assert r.status_code == 200
    assert r.headers["content-type"] == "audio/wav"
    assert r.content[:4] == b"RIFF"
    assert client.tts.calls == [("Ciao!", "it_IT-paola-medium", 1.5)]


@pytest.mark.parametrize(
    "body, status",
    [
        ({"text": "   ", "voice": "it_IT-paola-medium"}, 400),
        ({"text": "", "voice": "it_IT-paola-medium"}, 422),
        ({"text": "x", "voice": "it_IT-paola-medium", "speed": 5}, 422),
        ({"text": "x" * 5001, "voice": "it_IT-paola-medium"}, 400),
        ({"text": "ciao", "voice": "en_US-missing-medium"}, 404),
    ],
)
def test_synthesize_errors(client, body, status):
    assert client.post("/api/tts", json=body).status_code == status


def test_download_rejects_bad_voice_id(client):
    assert client.post("/api/tts/voices/..%2Fetc-x-y/download").status_code in (400, 404)
    assert client.post("/api/tts/voices/not-a-voice/download").status_code == 400


def test_transcribe(client):
    audio = make_wav()
    r = client.post(
        "/api/stt",
        files={"file": ("rec.webm", audio, "audio/webm")},
        data={"language": "it", "model": "tiny"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["text"] == "ciao mondo"
    assert body["segments"] == [{"start": 0.0, "end": 1.0, "text": "ciao mondo"}]
    assert client.stt.calls == [(audio, "it", "tiny", False)]


def test_transcribe_auto_language(client):
    client.post("/api/stt", files={"file": ("a.wav", make_wav())}, data={"language": ""})
    assert client.stt.calls[0][1] is None


def test_unknown_api_route_is_404(client):
    assert client.get("/api/nope").status_code == 404


def test_piper_engine_lists_catalog_and_local_voices(tmp_path):
    (tmp_path / "it_IT-custom-high.onnx").write_bytes(b"")
    (tmp_path / "it_IT-custom-high.onnx.json").write_text("{}")
    engine = PiperEngine(tmp_path)
    voices = {v.id: v for v in engine.list_voices()}
    assert voices["it_IT-custom-high"].installed
    assert not voices["it_IT-paola-medium"].installed
    with pytest.raises(VoiceNotFound):
        engine.synthesize("ciao", "it_IT-paola-medium")
