import { Bot, Database, LoaderCircle, Send, UserRound } from 'lucide-react'
import { useMutation } from '@tanstack/react-query'
import { useState } from 'react'
import { useApi } from '../lib/api/context'
import type { AssistantAnswer } from '../lib/api/client'

type ChatMessage =
  | { role: 'user'; text: string }
  | { role: 'assistant'; response: AssistantAnswer }

const examples = [
  'Why was RELIANCE included?',
  'How risky is this portfolio?',
  'Is this portfolio diversified?',
  'What happens in a 20% market crash?',
]

export function AssistantPanel({ portfolioId }: { portfolioId: string }) {
  const api = useApi()
  const [question, setQuestion] = useState('')
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const ask = useMutation({
    mutationFn: (value: string) => api.askAssistant(portfolioId, value),
    onSuccess: response => setMessages(current => [...current, { role: 'assistant', response }]),
  })

  function submit(value = question) {
    const clean = value.trim()
    if (!clean || ask.isPending) return
    setMessages(current => [...current, { role: 'user', text: clean }])
    setQuestion('')
    ask.mutate(clean)
  }

  return <section className="card assistant-panel" aria-label="Grounded portfolio assistant">
    <div className="card-head">
      <div><span>OFFLINE NLP ASSISTANT</span><h3>Ask about this portfolio</h3></div>
      <Bot/>
    </div>
    <p className="assistant-intro">Answers are generated from stored optimization, explanation, analytics, and scenario results. No external AI service is used.</p>
    <div className="assistant-examples" aria-label="Example questions">
      {examples.map(example => <button key={example} type="button" onClick={() => submit(example)}>{example}</button>)}
    </div>
    <div className="assistant-thread" aria-live="polite">
      {messages.length === 0 && <p className="assistant-empty">Choose an example or ask your own question.</p>}
      {messages.map((message, index) => message.role === 'user'
        ? <div className="chat-message chat-user" key={`${message.text}-${index}`}><UserRound/><p>{message.text}</p></div>
        : <div className={`chat-message chat-assistant${message.response.is_fallback ? ' chat-fallback' : ''}`} key={`${message.response.intent}-${index}`}>
          <Bot/><div><p>{message.response.answer}</p><div className="grounding-caption"><Database/>Grounded in {message.response.grounding.length ? message.response.grounding.map(item => `${item.source} (${item.fields.join(', ')})`).join('; ') : 'no portfolio source — clarification requested'} · intent {message.response.intent} · confidence {message.response.confidence.toFixed(2)}</div></div>
        </div>)}
      {ask.isPending && <div className="chat-message chat-assistant" role="status"><LoaderCircle className="spin"/><p>Classifying the question and checking live portfolio sources…</p></div>}
      {ask.error && <div className="assistant-error" role="alert">{ask.error instanceof Error ? ask.error.message : 'The assistant request failed.'}</div>}
    </div>
    <form className="assistant-form" onSubmit={event => { event.preventDefault(); submit() }}>
      <label htmlFor="assistant-question">Question</label>
      <div><input id="assistant-question" value={question} onChange={event => setQuestion(event.target.value)} placeholder="Ask why a stock was selected…"/><button className="primary" type="submit" disabled={!question.trim() || ask.isPending}><Send/>Ask</button></div>
    </form>
  </section>
}
