import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { ApiProvider } from '../../lib/api/context'
import type { AssistantAnswer, OptiVestApi } from '../../lib/api/client'
import { AssistantPanel } from '../AssistantPanel'

const grounded: AssistantAnswer = {
  answer: 'The diversification score is 82.0.',
  intent: 'DIVERSIFICATION_QUESTION',
  confidence: 0.94,
  grounding: [{ source: 'explainability.diversification', fields: ['overall_score'], values: { overall_score: 82.0 } }],
  is_fallback: false,
}

function show(askAssistant: OptiVestApi['askAssistant']) {
  const client = { askAssistant } as OptiVestApi
  const query = new QueryClient({ defaultOptions: { mutations: { retry: false } } })
  return render(<QueryClientProvider client={query}><ApiProvider client={client}><AssistantPanel portfolioId="portfolio-1"/></ApiProvider></QueryClientProvider>)
}

describe('AssistantPanel', () => {
  it('submits a question through the typed client and renders grounded evidence', async () => {
    const ask = vi.fn().mockResolvedValue(grounded)
    show(ask)
    await userEvent.click(screen.getByRole('button', { name: 'Is this portfolio diversified?' }))
    expect(await screen.findByText(grounded.answer)).toBeInTheDocument()
    expect(screen.getByText(/explainability\.diversification \(overall_score\)/)).toBeInTheDocument()
    expect(ask).toHaveBeenCalledWith('portfolio-1', 'Is this portfolio diversified?')
  })

  it('shows a pending state while portfolio sources are checked', async () => {
    show(vi.fn(() => new Promise<AssistantAnswer>(() => undefined)))
    await userEvent.click(screen.getByRole('button', { name: 'How risky is this portfolio?' }))
    expect(screen.getByRole('status')).toHaveTextContent('checking live portfolio sources')
  })

  it('renders a low-confidence fallback distinctly', async () => {
    show(vi.fn().mockResolvedValue({ answer: 'Please ask about the portfolio.', intent: 'UNKNOWN', confidence: 0.2, grounding: [], is_fallback: true }))
    await userEvent.type(screen.getByLabelText('Question'), 'Tell me a joke')
    await userEvent.click(screen.getByRole('button', { name: 'Ask' }))
    const response = await screen.findByText('Please ask about the portfolio.')
    expect(response.closest('.chat-fallback')).toBeInTheDocument()
    expect(screen.getByText(/clarification requested/)).toBeInTheDocument()
  })

  it('shows backend failures without inventing an answer', async () => {
    show(vi.fn().mockRejectedValue(new Error('assistant unavailable')))
    await userEvent.type(screen.getByLabelText('Question'), 'Why this allocation?')
    await userEvent.click(screen.getByRole('button', { name: 'Ask' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('assistant unavailable')
    expect(screen.queryByText(/Grounded in/)).not.toBeInTheDocument()
  })
})
