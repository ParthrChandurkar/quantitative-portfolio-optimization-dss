import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import { OptiVestApiError } from '../../lib/api/client'
import { PageError } from '../PageState'

function show(status:number){render(<MemoryRouter initialEntries={['/protected']}><Routes><Route path="/protected" element={<PageError error={new OptiVestApiError(status,'TEST','request failed')}/>}/><Route path="/auth" element={<p>Authentication page</p>}/></Routes></MemoryRouter>)}

describe('shared API error state',()=>{
  it('redirects a 401 to authentication',()=>{show(401);expect(screen.getByText('Authentication page')).toBeInTheDocument()})
  it('labels a 403 without leaking data',()=>{show(403);expect(screen.getByRole('alert')).toHaveTextContent('Access denied')})
  it('labels a 500 as a service error',()=>{show(500);expect(screen.getByRole('alert')).toHaveTextContent('OptiVest service error')})
})
