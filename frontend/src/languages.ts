const display = (() => {
  try {
    return new Intl.DisplayNames(['it'], { type: 'language' })
  } catch {
    return null
  }
})()

/** "it_IT" → "Italiano (Italia)", "en" → "Inglese". */
export function languageName(code: string): string {
  const tag = code.replace('_', '-')
  const name = display?.of(tag) ?? code
  return name.charAt(0).toUpperCase() + name.slice(1)
}

/** Languages offered for transcription; Whisper supports ~100, these are the common ones. */
export const STT_LANGUAGES = ['it', 'en', 'es', 'fr', 'de', 'pt', 'nl', 'ro', 'pl', 'ru', 'uk', 'ar', 'zh', 'ja', 'ko']
