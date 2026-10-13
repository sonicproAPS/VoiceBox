import { useEffect, useRef, useState } from 'react'
import { listModels, transcribe, type Segment, type Transcription } from './api'
import { STT_LANGUAGES, languageName } from './languages'

interface AudioInput {
  blob: Blob
  name: string
  url: string
}

function formatTime(seconds: number, sep = '.'): string {
  const ms = Math.round(seconds * 1000)
  const h = Math.floor(ms / 3_600_000)
  const m = Math.floor((ms % 3_600_000) / 60_000)
  const s = Math.floor((ms % 60_000) / 1000)
  const pad = (n: number, w = 2) => String(n).padStart(w, '0')
  return `${pad(h)}:${pad(m)}:${pad(s)}${sep}${pad(ms % 1000, 3)}`
}

function toSrt(segments: Segment[]): string {
  return segments
    .map((s, i) => `${i + 1}\n${formatTime(s.start, ',')} --> ${formatTime(s.end, ',')}\n${s.text}\n`)
    .join('\n')
}

function saveText(content: string, filename: string) {
  const url = URL.createObjectURL(new Blob([content], { type: 'text/plain;charset=utf-8' }))
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}

export default function SpeechToText() {
  const [models, setModels] = useState<string[]>([])
  const [model, setModel] = useState('')
  const [language, setLanguage] = useState('')
  const [translate, setTranslate] = useState(false)
  const [input, setInput] = useState<AudioInput | null>(null)
  const [recording, setRecording] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [result, setResult] = useState<Transcription | null>(null)
  const recorder = useRef<MediaRecorder | null>(null)

  useEffect(() => {
    listModels()
      .then(({ models, default: def }) => {
        setModels(models)
        setModel(def)
      })
      .catch((e) => setError(`Impossibile caricare i modelli: ${e.message}`))
  }, [])

  useEffect(() => () => { if (input) URL.revokeObjectURL(input.url) }, [input])

  function selectAudio(blob: Blob, name: string) {
    setInput({ blob, name, url: URL.createObjectURL(blob) })
    setResult(null)
  }

  async function startRecording() {
    setError('')
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const rec = new MediaRecorder(stream)
      const chunks: Blob[] = []
      rec.ondataavailable = (e) => chunks.push(e.data)
      rec.onstop = () => {
        stream.getTracks().forEach((t) => t.stop())
        const type = rec.mimeType || 'audio/webm'
        const ext = type.includes('mp4') ? 'm4a' : type.includes('ogg') ? 'ogg' : 'webm'
        selectAudio(new Blob(chunks, { type }), `registrazione.${ext}`)
        setRecording(false)
      }
      rec.start()
      recorder.current = rec
      setRecording(true)
    } catch (e) {
      setError(`Microfono non disponibile: ${(e as Error).message}`)
    }
  }

  function stopRecording() {
    recorder.current?.stop()
    recorder.current = null
  }

  async function onTranscribe() {
    if (!input) return
    setBusy(true)
    setError('')
    try {
      setResult(await transcribe(input.blob, input.name, { language, model, translate }))
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setBusy(false)
    }
  }

  const baseName = input?.name.replace(/\.[^.]+$/, '') || 'trascrizione'

  return (
    <section className="panel">
      <div className="row">
        <label className="button file">
          Carica file audio
          <input
            type="file"
            accept="audio/*,video/*"
            onChange={(e) => {
              const file = e.target.files?.[0]
              if (file) selectAudio(file, file.name)
              e.target.value = ''
            }}
          />
        </label>
        {recording ? (
          <button className="danger" onClick={stopRecording}>■ Ferma registrazione</button>
        ) : (
          <button onClick={startRecording}>● Registra dal microfono</button>
        )}
      </div>

      {input && (
        <div className="result">
          <span className="hint">{input.name}</span>
          <audio src={input.url} controls />
        </div>
      )}

      <div className="row">
        <label className="field grow">
          <span>Lingua</span>
          <select value={language} onChange={(e) => setLanguage(e.target.value)}>
            <option value="">Rilevamento automatico</option>
            {STT_LANGUAGES.map((l) => <option key={l} value={l}>{languageName(l)}</option>)}
          </select>
        </label>
        <label className="field grow">
          <span>Modello</span>
          <select value={model} onChange={(e) => setModel(e.target.value)}>
            {models.map((m) => <option key={m} value={m}>{m}</option>)}
          </select>
        </label>
        <label className="check">
          <input type="checkbox" checked={translate} onChange={(e) => setTranslate(e.target.checked)} />
          Traduci in inglese
        </label>
      </div>

      <div className="actions">
        <button className="primary" onClick={onTranscribe} disabled={!input || busy || recording}>
          {busy ? 'Trascrizione… (il primo avvio scarica il modello)' : 'Trascrivi'}
        </button>
      </div>

      {error && <p className="error">{error}</p>}

      {result && (
        <div className="transcript">
          <p className="hint">
            Lingua: {languageName(result.language)} ({Math.round(result.language_probability * 100)}%) · Durata: {formatTime(result.duration)}
          </p>
          <textarea readOnly value={result.text} rows={6} />
          <div className="actions">
            <button onClick={() => navigator.clipboard.writeText(result.text)}>Copia</button>
            <button onClick={() => saveText(result.text, `${baseName}.txt`)}>Scarica TXT</button>
            <button onClick={() => saveText(toSrt(result.segments), `${baseName}.srt`)}>Scarica SRT</button>
          </div>
          <ol className="segments">
            {result.segments.map((s, i) => (
              <li key={i}>
                <time>{formatTime(s.start)}</time>
                <span>{s.text}</span>
              </li>
            ))}
          </ol>
        </div>
      )}
    </section>
  )
}
