export interface Voice {
  id: string
  name: string
  language: string
  quality: string
  installed: boolean
}

export interface Segment {
  start: number
  end: number
  text: string
}

export interface Transcription {
  text: string
  language: string
  language_probability: number
  duration: number
  segments: Segment[]
}

async function check(res: Response): Promise<Response> {
  if (!res.ok) {
    let detail = `${res.status} ${res.statusText}`
    try {
      const body = await res.json()
      if (typeof body.detail === 'string') detail = body.detail
      else if (Array.isArray(body.detail)) detail = body.detail.map((d: { msg: string }) => d.msg).join('; ')
    } catch {
      // response was not JSON
    }
    throw new Error(detail)
  }
  return res
}

export async function listVoices(): Promise<Voice[]> {
  return (await check(await fetch('/api/tts/voices'))).json()
}

export async function downloadVoice(id: string): Promise<Voice> {
  const res = await fetch(`/api/tts/voices/${encodeURIComponent(id)}/download`, { method: 'POST' })
  return (await check(res)).json()
}

export async function synthesize(text: string, voice: string, speed: number): Promise<Blob> {
  const res = await fetch('/api/tts', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text, voice, speed }),
  })
  return (await check(res)).blob()
}

export async function listModels(): Promise<{ models: string[]; default: string }> {
  return (await check(await fetch('/api/stt/models'))).json()
}

export async function transcribe(
  audio: Blob,
  filename: string,
  options: { language?: string; model?: string; translate?: boolean },
): Promise<Transcription> {
  const form = new FormData()
  form.append('file', audio, filename)
  if (options.language) form.append('language', options.language)
  if (options.model) form.append('model', options.model)
  if (options.translate) form.append('translate', 'true')
  const res = await fetch('/api/stt', { method: 'POST', body: form })
  return (await check(res)).json()
}
