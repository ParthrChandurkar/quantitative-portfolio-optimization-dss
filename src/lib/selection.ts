export type PortfolioSelection = { portfolioId: string; snapshotId: string }

const key = 'optivest.selection'
export function saveSelection(value: PortfolioSelection) { globalThis.localStorage?.setItem(key, JSON.stringify(value)) }
export function loadSelection(): PortfolioSelection | null {
  const value = globalThis.localStorage?.getItem(key)
  return value ? JSON.parse(value) as PortfolioSelection : null
}
