import { afterEach, describe, expect, it, vi } from 'vitest'
import { ApiClient } from './client'

describe('ApiClient native fetch integration', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('binds native fetch to the browser global receiver', async () => {
    const nativeLikeFetch = vi.fn(function (this: unknown) {
      if (this !== globalThis) throw new TypeError('Illegal invocation')
      return Promise.resolve(new Response(JSON.stringify({ data: [], error: null }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }))
    })
    vi.stubGlobal('fetch', nativeLikeFetch)

    const client = new ApiClient('http://localhost/api/v1')
    await expect(client.portfolios()).resolves.toEqual([])
    expect(nativeLikeFetch).toHaveBeenCalledOnce()
  })

  it('posts assistant questions to the portfolio-scoped endpoint', async () => {
    const response = { answer: 'Grounded answer.', intent: 'ALLOCATION_RATIONALE', confidence: 0.91, grounding: [], is_fallback: false }
    const fetcher = vi.fn().mockResolvedValue(new Response(JSON.stringify({ data: response, error: null }), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    }))
    const client = new ApiClient('http://localhost/api/v1', undefined, fetcher)
    await expect(client.askAssistant('portfolio-1', 'Why these weights?')).resolves.toEqual(response)
    expect(fetcher).toHaveBeenCalledWith('http://localhost/api/v1/portfolios/portfolio-1/assistant/ask', expect.objectContaining({ method: 'POST', body: JSON.stringify({ question: 'Why these weights?' }) }))
  })
})
