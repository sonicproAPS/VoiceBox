import { useEffect, useState } from 'react'
import { downloadVoice, listVoices, synthesize, type Voice } from './api'
import { languageName } from './languages'

const MAX_CHARS = 5000

export default function TextToSpeech() {
  const [voices, setVoices] = useState<Voice[]>([])
  const [voiceId, setVoiceId] = useState('')
  const [text, setText] = useState('Ciao! Questa è una prova di sintesi vocale.')
  const [speed, setSpeed] = useState(1)
  const [busy, setBusy] = useState<'download' | 'generate' | null>(null)
  const [error, setError] = useState('')
  const [audioUrl, setAudioUrl] = useState('')

  useEffect(() => {
    listVoices()
      .then((list) => {
        setVoices(list)
        const italian = (v: Voice) => v.language.startsWith('it')
        const preferred =
          list.find((v) => v.installed && italian(v)) ?? list.find((v) => v.installed) ?? list.find(italian) ?? list[0]
        if (preferred) setVoiceId(preferred.id)
      })
      .catch((e) => setError(`Impossibile caricare le voci: ${e.message}`))
  }, [])

  useEffect(() => () => { if (audioUrl) URL.revokeObjectURL(audioUrl) }, [audioUrl])

  const voice = voices.find((v) => v.id === voiceId)

  async function onDownload() {
    if (!voice) return
    setBusy('download')
    setError('')
    try {
      const updated = await downloadVoice(voice.id)
      setVoices((list) => list.map((v) => (v.id === updated.id ? updated : v)))
    } catch (e) {
      setError(`Download non riuscito: ${(e as Error).message}`)
    } finally {
      setBusy(null)
    }
  }

  async function onGenerate() {
    if (!voice) return
    setBusy('generate')
    setError('')
    try {
      const blob = await synthesize(text, voice.id, speed)
      setAudioUrl(URL.createObjectURL(blob))
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setBusy(null)
    }
  }

  return (
    <section className="panel">
      <label className="field">
        <span>Testo</span>
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          maxLength={MAX_CHARS}
          rows={8}
          placeholder="Scrivi il testo da leggere…"
        />
        <small className="hint">{text.length} / {MAX_CHARS}</small>
      </label>

      <div className="row">
        <label className="field grow">
          <span>Voce</span>
          <select value={voiceId} onChange={(e) => setVoiceId(e.target.value)}>
            {voices.map((v) => (
              <option key={v.id} value={v.id}>
                {languageName(v.language)} — {v.name} ({v.quality}){v.installed ? '' : ' ⬇'}
              </option>
            ))}
          </select>
        </label>

        <label className="field">
          <span>Velocità {speed.toFixed(2)}×</span>
          <input type="range" min={0.5} max={2} step={0.05} value={speed} onChange={(e) => setSpeed(Number(e.target.value))} />
        </label>
      </div>

      <div className="actions">
        {voice && !voice.installed ? (
          <button onClick={onDownload} disabled={busy !== null}>
            {busy === 'download' ? 'Download in corso…' : 'Scarica voce'}
          </button>
        ) : (
          <button className="primary" onClick={onGenerate} disabled={busy !== null || !voice || !text.trim()}>
            {busy === 'generate' ? 'Generazione…' : 'Genera audio'}
          </button>
        )}
      </div>

      {error && <p className="error">{error}</p>}

      {audioUrl && (
        <div className="result">
          <audio src={audioUrl} controls autoPlay />
          <a className="button" href={audioUrl} download={`voicebox-${voiceId}.wav`}>Scarica WAV</a>
        </div>
      )}
    </section>
  )
}
