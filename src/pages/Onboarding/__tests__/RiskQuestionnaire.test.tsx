import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import type { OptiVestApi, RiskProfile } from '../../../lib/api/client'
import { ApiProvider } from '../../../lib/api/context'
import { RiskQuestionnaire } from '../RiskQuestionnaire'

const profile:RiskProfile={id:'risk-1',predicted_category:'moderate',category_confidence:.96,probabilities:{conservative:.01,moderate:.96,aggressive:.03},recommended_constraints:{risk_tolerance:.22,max_single_weight:.15,default_sector_cap:.30},questionnaire_answers:{age_bracket:'30_44',investment_horizon:'6_10_years',income_stability:'stable',loss_reaction:'hold',experience_level:'intermediate',financial_dependents:'one_or_two'},model_name:'logistic_regression',created_at:'2026-08-22T00:00:00Z'}

function show(submitRiskProfile:OptiVestApi['submitRiskProfile']){const client={isAuthenticated:()=>true,submitRiskProfile} as unknown as OptiVestApi;const query=new QueryClient({defaultOptions:{mutations:{retry:false}}});return render(<MemoryRouter><QueryClientProvider client={query}><ApiProvider client={client}><RiskQuestionnaire/></ApiProvider></QueryClientProvider></MemoryRouter>)}

describe('RiskQuestionnaire',()=>{
  it('shows a visible loading state while classification is running',async()=>{show(vi.fn(()=>new Promise<RiskProfile>(()=>undefined)));await userEvent.click(screen.getByRole('button',{name:'Get transparent recommendation'}));expect(await screen.findByRole('button',{name:/Assessing profile/})).toBeDisabled()})
  it('shows the reason, confidence, and editable defaults before storing them',async()=>{const submit=vi.fn().mockResolvedValue(profile);show(submit);await userEvent.click(screen.getByRole('button',{name:'Get transparent recommendation'}));expect(await screen.findByText(/suggest a/)).toHaveTextContent('moderate');expect(screen.getByText(/96.0%/)).toBeInTheDocument();const weight=screen.getByLabelText('Recommended maximum stock weight');await userEvent.clear(weight);await userEvent.type(weight,'0.18');await userEvent.click(screen.getByRole('button',{name:'Use these editable defaults'}));expect(JSON.parse(localStorage.getItem('optivest.personalized-defaults')!)).toEqual({risk_tolerance:.22,max_single_weight:.18,default_sector_cap:.3,category:'moderate',confidence:.96});expect(submit).toHaveBeenCalledWith(profile.questionnaire_answers)})
  it('renders the shared error state for a failed API request',async()=>{show(vi.fn().mockRejectedValue(new Error('classification unavailable')));await userEvent.click(screen.getByRole('button',{name:'Get transparent recommendation'}));expect(await screen.findByRole('alert')).toHaveTextContent('classification unavailable')})
})
