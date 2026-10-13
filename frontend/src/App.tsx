import { useState } from 'react'
import SpeechToText from './SpeechToText'
import TextToSpeech from './TextToSpeech'

type Tab = 'tts' | 'stt'

export default function App() {
  const [tab, setTab] = useState<Tab>('tts')

  return (
    <main className="app">
      <header>
        <h1>VoiceBox</h1>
        <p className="hint">Sintesi e trascrizione vocale, tutto in locale.</p>
      </header>

      <nav className="tabs" role="tablist">
        <button role="tab" aria-selected={tab === 'tts'} onClick={() => setTab('tts')}>Testo → Voce</button>
        <button role="tab" aria-selected={tab === 'stt'} onClick={() => setTab('stt')}>Voce → Testo</button>
      </nav>

      {/* Both stay mounted so switching tabs keeps text, audio and results. */}
      <div hidden={tab !== 'tts'}><TextToSpeech /></div>
      <div hidden={tab !== 'stt'}><SpeechToText /></div>
    </main>
  )
}
