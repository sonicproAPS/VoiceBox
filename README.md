# VoiceBox

App web per **sintesi vocale (text-to-speech)** e **trascrizione (speech-to-text)** che gira interamente in locale, con modelli open source. Niente API a pagamento e nessun audio inviato a servizi esterni.

| Funzione | Motore | Note |
|---|---|---|
| Testo → Voce | [Piper](https://github.com/OHF-Voice/piper1-gpl) | Voci ONNX leggere (20–100 MB), tempo reale su CPU, incluso l'italiano |
| Voce → Testo | [faster-whisper](https://github.com/SYSTRAN/faster-whisper) | Whisper su CTranslate2, ~100 lingue, CPU o GPU NVIDIA |

## Architettura

```
frontend/  React + Vite + TypeScript (UI in italiano)
backend/   FastAPI
  voicebox/tts/   interfaccia TTSEngine + PiperEngine
  voicebox/stt/   interfaccia STTEngine + WhisperEngine
data/      voci e modelli scaricati (creata al primo uso, ignorata da git)
```

I motori sono dietro un'interfaccia comune (`TTSEngine`, `STTEngine`), quindi se ne possono aggiungere altri (es. Kokoro, XTTS, Qwen3-TTS per la clonazione vocale) senza toccare API e frontend.

## Requisiti

- Python 3.10+
- Node.js 18+ (solo per compilare il frontend)
- Internet al primo avvio, per scaricare voci e modelli da Hugging Face

## Avvio

```bash
# Backend
cd backend
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Frontend (compilato una volta, poi servito dal backend)
cd ../frontend
npm install
npm run build

# Avvio
cd ../backend
uvicorn voicebox.main:app --port 8000
```

Apri http://localhost:8000.

1. **Testo → Voce**: scegli una voce, premi *Scarica voce* la prima volta, poi *Genera audio*.
2. **Voce → Testo**: carica un file audio/video o registra dal microfono, poi *Trascrivi*. Il primo utilizzo di un modello Whisper lo scarica (`small` ≈ 480 MB).

### Sviluppo

Con hot-reload su entrambi i lati:

```bash
cd backend && uvicorn voicebox.main:app --reload --port 8000
cd frontend && npm run dev     # http://localhost:5173, /api inoltrato al backend
```

Test del backend:

```bash
cd backend && pip install -r requirements-dev.txt && pytest
```

## Configurazione

Variabili d'ambiente:

| Variabile | Default | Descrizione |
|---|---|---|
| `VOICEBOX_DATA_DIR` | `./data` | Dove salvare voci e modelli |
| `VOICEBOX_WHISPER_MODEL` | `small` | Modello predefinito: `tiny`, `base`, `small`, `medium`, `large-v3`, `large-v3-turbo` |
| `VOICEBOX_DEVICE` | `auto` | `cpu`, `cuda` o `auto` |
| `VOICEBOX_MAX_TTS_CHARS` | `5000` | Lunghezza massima del testo da sintetizzare |

Altre voci Piper: l'elenco completo è su https://huggingface.co/rhasspy/piper-voices. Si installano con `POST /api/tts/voices/<id>/download` (es. `it_IT-riccardo-x_low`) oppure copiando `<id>.onnx` e `<id>.onnx.json` in `data/voices/`.

## API

| Metodo | Percorso | Descrizione |
|---|---|---|
| `GET` | `/api/tts/voices` | Elenco voci (installate e scaricabili) |
| `POST` | `/api/tts/voices/{id}/download` | Scarica una voce |
| `POST` | `/api/tts` | JSON `{text, voice, speed}` → `audio/wav` |
| `GET` | `/api/stt/models` | Modelli Whisper disponibili |
| `POST` | `/api/stt` | multipart `file`, `language?`, `model?`, `translate?` → testo + segmenti con timestamp |

Documentazione interattiva: http://localhost:8000/docs.

## Prossimi passi possibili

- Clonazione vocale da un campione audio (XTTS-v2, F5-TTS, Qwen3-TTS)
- Cronologia di generazioni e trascrizioni
- Streaming dell'audio frase per frase e trascrizione in tempo reale
- Pacchetto desktop con Tauri
