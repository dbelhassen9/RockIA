const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export const getToken = () =>
  typeof window !== 'undefined' ? localStorage.getItem('rockai_token') : null
export const setToken = (t: string) => localStorage.setItem('rockai_token', t)
export const clearToken = () => {
  localStorage.removeItem('rockai_token')
  localStorage.removeItem('rockai_user')
}

async function apiFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getToken()
  const res = await fetch(API_BASE + path, {
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    ...options,
  })
  const data = await res.json()
  if (!res.ok) throw new Error(data.detail || `Erreur ${res.status}`)
  return data as T
}

export interface AuthResponse { access_token: string; token_type: string }
export interface User {
  id: number; email: string; full_name: string
  plan: 'free' | 'pro' | 'elite'; credits: number; bankroll: number
}
export interface ValueBet {
  match_id: string; sport_key: string; league: string
  team_home: string; team_away: string; commence_time: string
  bet_on: 'home' | 'draw' | 'away'; bet_label: string
  bookmaker: string; bookmaker_key: string
  odds: number; fair_odds: number; pinnacle_odds: number | null
  ev: number; ev_pct: number; kelly_pct: number; is_strong: boolean
  stake_100: number; stake_500: number; stake_1000: number
}
export interface Match {
  match_id: string; sport_key: string; league: string
  team_home: string; team_away: string; commence_time: string
  odds_home: number | null; odds_draw: number | null; odds_away: number | null
  has_value: boolean; value_count: number
  best_ev: number | null; best_ev_pct: number | null
  best_bet_label: string | null; best_bookmaker: string | null
  best_odds: number | null; best_kelly: number | null
  is_strong: boolean; value_bets: ValueBet[]
}
export interface MatchesResponse {
  count: number; value_count: number; strong_count: number
  mode: 'live' | 'demo'; updated_at: string; matches: Match[]
}
export interface Bet {
  id: number; match_id: string; sport: string
  team_home: string; team_away: string; bet_on: string; bet_label: string
  bookmaker: string; odds: number; fair_odds: number; ev: number
  kelly_pct: number; stake: number; status: string
  result: 'won' | 'lost' | null; profit: number; placed_at: string; match_date: string
}
export interface Stats {
  total_bets: number; won: number; lost: number; pending: number
  win_rate: number; roi: number; total_profit: number; total_staked: number
  avg_ev_pct: number; bankroll: number; projection_500_bets: number
  monthly: { month: string; bets: number; wins: number; profit: number }[]
  by_sport: { sport: string; bets: number; wins: number; profit: number }[]
}

export interface PoissonProbabilities {
  home_win: number
  draw: number
  away_win: number
  over_15: number
  over_25: number
  over_35: number
  btts_yes: number
  btts_no: number
  top_scores: { score: string; prob: number }[]
}

export interface TeamHistoryStats {
  played: number
  wins: number
  draws: number
  losses: number
  win_rate: number
  avg_goals_for: number
  avg_goals_against: number
  over_25_rate: number
  btts_rate: number
  clean_sheet_rate: number
  form_str: string
  home: { played: number; wins: number; avg_gf: number; avg_ga: number }
  away: { played: number; wins: number; avg_gf: number; avg_ga: number }
  h2h: {
    played: number; wins: number; draws: number; losses: number
    recent?: { date: string; home: number; gf: number; ga: number; result: string }[]
  }
  recent_matches: {
    result: string; goals_for: number; goals_against: number
    opponent_name: string; match_date: string; is_home: number
  }[]
  data_source: string
}

export interface AnalysisResult {
  recommendation: string
  confidence: number
  risk_level: 'faible' | 'modéré' | 'élevé'
  reasoning: string
  factors: string[]
  xg_home: number
  xg_away: number
  form_home: string
  form_away: string
  h2h_home_wins: number
  h2h_away_wins: number
  h2h_draws: number
  h2h_recent?: { date: string; home: number; gf: number; ga: number; result: string }[]
  probabilities?: PoissonProbabilities
  stats_home?: TeamHistoryStats
  stats_away?: TeamHistoryStats
  data_source: string
  best_bet_label: string | null
  best_odds: number | null
  best_bookmaker: string | null
  best_ev_pct: number | null
  best_kelly_pct: number | null
  credits_remaining: number
  from_cache: boolean
}

export const authLogin = (email: string, password: string) =>
  apiFetch<AuthResponse>('/auth/login', { method: 'POST', body: JSON.stringify({ email, password }) })
export const authRegister = (email: string, password: string, full_name: string) =>
  apiFetch<AuthResponse>('/auth/register', { method: 'POST', body: JSON.stringify({ email, password, full_name }) })
export const getMe = () => apiFetch<User>('/user/me')
export const getMatches = (params?: string) =>
  apiFetch<MatchesResponse>(`/matches${params ? '?' + params : ''}`)
export const getMatch = (id: string) => apiFetch<Match>(`/matches/${id}`)
export const getBets = () => apiFetch<{ bets: Bet[] }>('/bets')
export const getStats = () => apiFetch<Stats>('/stats')
export const analyseMatch = (id: string) =>
  apiFetch<AnalysisResult>(`/matches/${id}/analyse`, { method: 'POST' })
