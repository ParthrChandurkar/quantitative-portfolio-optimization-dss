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
})
