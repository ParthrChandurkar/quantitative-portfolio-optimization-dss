export type Holding = {
  symbol: string; name: string; sector: string; weight: number; value: number;
  expectedReturn: number; volatility: number; score: number; color: string; rationale: string;
}

export const holdings: Holding[] = [
  { symbol: 'HDFCBANK', name: 'HDFC Bank', sector: 'Financials', weight: 18.4, value: 460000, expectedReturn: 15.8, volatility: 18.2, score: 92, color: '#60a5fa', rationale: 'High risk-adjusted return and resilient asset quality anchor the allocation.' },
  { symbol: 'RELIANCE', name: 'Reliance Industries', sector: 'Energy', weight: 15.2, value: 380000, expectedReturn: 16.9, volatility: 22.4, score: 89, color: '#34d399', rationale: 'Strong expected return with diversified earnings across energy and consumer businesses.' },
  { symbol: 'INFY', name: 'Infosys', sector: 'Technology', weight: 13.6, value: 340000, expectedReturn: 17.4, volatility: 21.8, score: 88, color: '#a78bfa', rationale: 'Efficient return contribution improves portfolio Sharpe without binding the sector cap.' },
  { symbol: 'ICICIBANK', name: 'ICICI Bank', sector: 'Financials', weight: 11.8, value: 295000, expectedReturn: 16.3, volatility: 20.1, score: 86, color: '#fbbf24', rationale: 'Positive marginal Sharpe contribution; weight limited by financial-sector exposure.' },
  { symbol: 'LT', name: 'Larsen & Toubro', sector: 'Industrials', weight: 10.4, value: 260000, expectedReturn: 18.1, volatility: 24.3, score: 84, color: '#fb7185', rationale: 'Captures domestic capex momentum and reduces correlation with technology holdings.' },
  { symbol: 'SUNPHARMA', name: 'Sun Pharma', sector: 'Healthcare', weight: 9.2, value: 230000, expectedReturn: 14.6, volatility: 17.1, score: 82, color: '#22d3ee', rationale: 'Defensive return profile provides downside protection during broad market stress.' },
  { symbol: 'ITC', name: 'ITC', sector: 'Consumer', weight: 8.4, value: 210000, expectedReturn: 13.2, volatility: 15.4, score: 79, color: '#c084fc', rationale: 'Low volatility and dividend yield stabilize the portfolio risk budget.' },
  { symbol: 'BHARTIARTL', name: 'Bharti Airtel', sector: 'Telecom', weight: 7.2, value: 180000, expectedReturn: 16.1, volatility: 20.9, score: 78, color: '#f97316', rationale: 'Pricing power and cash-flow growth add uncorrelated upside participation.' },
  { symbol: 'TATAMOTORS', name: 'Tata Motors', sector: 'Automobile', weight: 6.0, value: 150000, expectedReturn: 19.4, volatility: 29.8, score: 75, color: '#94a3b8', rationale: 'Highest return candidate, capped at 6% to contain its volatility contribution.' },
]

export const curve = [100,101,100.5,102,103.5,102.8,104.2,105,104.4,106.3,107.5,108.2,107.6,109.4,110.8,111.6,113.1,112.4,114.5,116.8,117.6,116.9,119.2,120.5,122.4,124.1,123.5,125.9,127.8,129.4]
export const benchmark = [100,100.4,99.8,101,101.8,101.4,102.6,103.2,102.8,104,105,105.3,104.7,106,106.6,107.1,108,107.5,108.8,110.1,110.7,110.2,111.8,112.7,113.8,114.5,114,115.2,116.2,117]
