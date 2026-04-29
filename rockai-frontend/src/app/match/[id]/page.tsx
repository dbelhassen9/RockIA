'use client'
import { useEffect, useState } from 'react'
import { useRouter, useParams } from 'next/navigation'
import toast from 'react-hot-toast'
import Navbar from '@/components/Navbar'
import { getMatch, analyseMatch, Match, AnalysisResult } from '@/lib/api'
import { useUserStore } from '@/lib/store'
import {
  ArrowLeft, Brain, Activity, Shield, AlertTriangle, Zap,
  Target, BarChart3, Calendar, TrendingUp, Sparkles
} from 'lucide-react'

const EMOJI: Record<string, string> = {
  'Arsenal': '🔴', 'Chelsea': '🔵', 'Liverpool': '🔴', 'Man City': '🔵', 'Man United': '🔴',
  'Tottenham': '⚪', 'PSG': '🔵', 'Lyon': '🔴', 'Marseille': '🔵', 'Monaco': '🔴',
  'Bayern': '🔴', 'Dortmund': '🟡', 'Real Madrid': '⚪', 'Barcelona': '🔵', 'Atletico': '🔴',
  'Inter': '⚫', 'Juventus': '⚪', 'Napoli': '🔵', 'Lakers': '🟣', 'Celtics': '🍀',
}
function emoji(name: string) {
  for (const [k, v] of Object.entries(EMOJI)) { if (name.includes(k)) return v }
  return '⚽'
}

function formChip(c: string) {
  const map: Record<string, { bg: string; col: string }> = {
    V: { bg: 'var(--accent-dim)', col: 'var(--accent)' },
    D: { bg: 'var(--red-dim)',    col: 'var(--red)' },
    N: { bg: 'var(--gold-dim)',   col: 'var(--gold)' },
  }
  const s = map[c] || map.N
  return s
}

function SectionTitle({ icon: Icon, title, sub }: { icon: any; title: string; sub?: string }) {
  return (
    <div className="flex items-center gap-3 mb-4">
      <div className="flex items-center justify-center w-8 h-8 rounded-lg"
           style={{ background: 'var(--accent-dim)', border: '1px solid var(--border-accent)' }}>
        <Icon size={14} style={{ color: 'var(--accent)' }} />
      </div>
      <div>
        <div className="font-display font-bold text-lg">{title}</div>
        {sub && <div className="font-mono text-[0.62rem] uppercase tracking-widest" style={{ color: 'var(--text-muted)' }}>{sub}</div>}
      </div>
    </div>
  )
}

function CompareBar({ label, leftVal, rightVal, leftLabel, rightLabel, isPercent = false }: {
  label: string; leftVal: number; rightVal: number; leftLabel: string; rightLabel: string; isPercent?: boolean
}) {
  const total = (leftVal + rightVal) || 1
  const leftPct  = (leftVal  / total) * 100
  const rightPct = (rightVal / total) * 100
  const fmt = (v: number) => isPercent ? `${v.toFixed(1)}%` : v.toFixed(2)

  return (
    <div>
      <div className="flex items-center justify-between mb-1.5">
        <span className="font-display font-bold text-sm" style={{ color: 'var(--accent)' }}>{fmt(leftVal)}</span>
        <span className="font-mono text-[0.62rem] uppercase tracking-wider" style={{ color: 'var(--text-muted)' }}>{label}</span>
        <span className="font-display font-bold text-sm" style={{ color: 'var(--accent)' }}>{fmt(rightVal)}</span>
      </div>
      <div className="bar-track">
        <div className="bar-fill-left"  style={{ width: `${leftPct  / 2}%` }} />
        <div className="bar-fill-right" style={{ width: `${rightPct / 2}%` }} />
      </div>
      <div className="flex items-center justify-between mt-1">
        <span className="font-mono text-[0.55rem] truncate max-w-[40%]" style={{ color: 'var(--text-muted)' }}>{leftLabel}</span>
        <span className="font-mono text-[0.55rem] truncate max-w-[40%] text-right" style={{ color: 'var(--text-muted)' }}>{rightLabel}</span>
      </div>
    </div>
  )
}

function ProbTile({ label, value, big = false, color = 'var(--accent)' }:
  { label: string; value: number; big?: boolean; color?: string }) {
  return (
    <div className="card-vs p-4 flex flex-col items-center justify-center text-center">
      <div className="font-mono text-[0.55rem] uppercase tracking-widest mb-1" style={{ color: 'var(--text-muted)' }}>{label}</div>
      <div className={`font-display font-extrabold ${big ? 'text-3xl' : 'text-xl'}`} style={{ color }}>
        {value.toFixed(1)}<span className="text-sm">%</span>
      </div>
      <div className="bar-track mt-2 w-full" style={{ height: 4 }}>
        <div className="bar-fill-progress" style={{ width: `${Math.min(value, 100)}%` }} />
      </div>
    </div>
  )
}

export default function MatchDetailPage() {
  const router = useRouter()
  const params = useParams()
  const { loadUser } = useUserStore()
  const [match, setMatch] = useState<Match | null>(null)
  const [loading, setLoading] = useState(true)
  const [analysis, setAnalysis] = useState<AnalysisResult | null>(null)
  const [analysing, setAnalysing] = useState(false)
  const [showFullHistoryHome, setShowFullHistoryHome] = useState(false)
  const [showFullHistoryAway, setShowFullHistoryAway] = useState(false)

  useEffect(() => {
    loadUser().then(() => {
      if (!useUserStore.getState().user) router.push('/login')
    })
    if (params.id) {
      const cached = typeof window !== 'undefined'
        ? localStorage.getItem(`rockai_analysis_${params.id}`) : null
      if (cached) {
        try {
          const parsed = JSON.parse(cached) as AnalysisResult
          // eslint-disable-next-line react-hooks/set-state-in-effect
          setAnalysis(parsed)
        } catch { /* ignore */ }
      }
      getMatch(params.id as string)
        .then(setMatch)
        .catch((e: Error) => { toast.error(e.message); router.push('/agenda') })
        .finally(() => setLoading(false))
    }
  }, [params.id])

  const handleAnalyse = async () => {
    if (!params.id) return
    setAnalysing(true)
    try {
      const res = await analyseMatch(params.id as string)
      setAnalysis(res)
      try {
        localStorage.setItem(`rockai_analysis_${params.id}`, JSON.stringify(res))
      } catch { /* quota */ }
      if (!res.from_cache)
        toast.success(`Analyse générée — ${res.credits_remaining} crédit${res.credits_remaining > 1 ? 's' : ''} restant${res.credits_remaining > 1 ? 's' : ''}`)
    } catch (e) {
      const err = e as Error
      toast.error(err.message)
    } finally {
      setAnalysing(false)
    }
  }

  if (loading) return (
    <div className="min-h-screen">
      <Navbar />
      <div className="max-w-5xl mx-auto px-6 py-8 space-y-4">
        {[...Array(4)].map((_, i) => (
          <div key={i} className="h-24 rounded-xl animate-pulse" style={{ background: 'var(--surface)' }} />
        ))}
      </div>
    </div>
  )

  if (!match) return null

  const time = new Date(match.commence_time).toLocaleString('fr-FR', {
    weekday: 'long', day: 'numeric', month: 'long', hour: '2-digit', minute: '2-digit',
  })

  const riskColor = (level: string) =>
    level === 'faible' ? 'var(--accent)' : level === 'élevé' ? 'var(--red)' : 'var(--gold)'
  const riskBg = (level: string) =>
    level === 'faible' ? 'var(--accent-dim)' : level === 'élevé' ? 'var(--red-dim)' : 'var(--gold-dim)'

  const probs   = analysis?.probabilities
  const sH      = analysis?.stats_home
  const sA      = analysis?.stats_away
  const h2hRec  = analysis?.h2h_recent || []
  const recentH = sH?.recent_matches || []
  const recentA = sA?.recent_matches || []

  return (
    <div className="min-h-screen">
      <Navbar />
      <div className="max-w-5xl mx-auto px-6 py-8">
        <button onClick={() => router.back()}
          className="flex items-center gap-2 mb-6 font-mono text-[0.72rem] uppercase tracking-wider transition-colors"
          style={{ color: 'var(--text-muted)' }}
          onMouseEnter={e => (e.currentTarget.style.color = 'var(--accent)')}
          onMouseLeave={e => (e.currentTarget.style.color = 'var(--text-muted)')}>
          <ArrowLeft size={14} /> Retour au calendrier
        </button>

        {/* SECTION 1 — Header du match */}
        <div className="card-vs p-8 mb-6 relative overflow-hidden"
             style={{ borderColor: match.is_strong ? 'var(--border-accent)' : 'var(--border)' }}>
          {match.is_strong && (
            <div className="absolute top-0 left-0 right-0 h-px"
                 style={{ background: 'linear-gradient(90deg,transparent,var(--accent),transparent)' }} />
          )}
          <div className="flex items-center justify-between mb-4 flex-wrap gap-2">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="font-mono text-[0.62rem] uppercase tracking-widest px-2 py-1 rounded"
                    style={{ background: 'var(--surface2)', border: '1px solid var(--border)', color: 'var(--text-dim)' }}>
                {match.league}
              </span>
              <span className="font-mono text-[0.62rem] uppercase tracking-widest px-2 py-1 rounded flex items-center gap-1"
                    style={{ background: 'var(--surface2)', border: '1px solid var(--border)', color: 'var(--text-dim)' }}>
                <Calendar size={10} /> {time}
              </span>
            </div>
            {match.is_strong && (
              <span className="font-mono text-[0.62rem] uppercase tracking-wider px-3 py-1 rounded flex items-center gap-1"
                    style={{ background: 'var(--accent-dim)', color: 'var(--accent)', border: '1px solid var(--border-accent)' }}>
                <Zap size={10} /> Value Bet
              </span>
            )}
          </div>

          <div className="flex items-center justify-center gap-6 md:gap-12 my-4">
            <div className="flex flex-col items-center gap-2 flex-1 max-w-[200px]">
              <div className="text-5xl">{emoji(match.team_home)}</div>
              <div className="font-display font-extrabold text-xl md:text-2xl tracking-tight text-center">{match.team_home}</div>
              <div className="font-mono text-[0.6rem] uppercase tracking-widest" style={{ color: 'var(--text-muted)' }}>Domicile</div>
            </div>
            <div className="flex flex-col items-center gap-2">
              <div className="font-mono text-[0.6rem] uppercase tracking-widest" style={{ color: 'var(--text-muted)' }}>vs</div>
              <div className="flex gap-2">
                {[match.odds_home, match.odds_draw, match.odds_away].map((o, i) => o ? (
                  <div key={i} className="flex flex-col items-center px-3 py-1.5 rounded-lg"
                       style={{ background: 'var(--surface2)', border: '1px solid var(--border)' }}>
                    <span className="font-mono text-[0.58rem] uppercase" style={{ color: 'var(--text-muted)' }}>
                      {i === 0 ? '1' : i === 1 ? 'N' : '2'}
                    </span>
                    <span className="font-display font-bold text-lg">{o.toFixed(2)}</span>
                  </div>
                ) : null)}
              </div>
            </div>
            <div className="flex flex-col items-center gap-2 flex-1 max-w-[200px]">
              <div className="text-5xl">{emoji(match.team_away)}</div>
              <div className="font-display font-extrabold text-xl md:text-2xl tracking-tight text-center">{match.team_away}</div>
              <div className="font-mono text-[0.6rem] uppercase tracking-widest" style={{ color: 'var(--text-muted)' }}>Extérieur</div>
            </div>
          </div>
        </div>

        {/* SECTION 2 — Forme récente */}
        <div className="card-vs p-6 mb-6">
          <SectionTitle icon={Activity} title="Forme récente" sub="5 derniers matchs (2 ans dispos)" />
          <div className="grid md:grid-cols-2 gap-5">
            {[
              { team: match.team_home, recent: recentH, fallback: analysis?.form_home, expanded: showFullHistoryHome, setExpanded: setShowFullHistoryHome },
              { team: match.team_away, recent: recentA, fallback: analysis?.form_away, expanded: showFullHistoryAway, setExpanded: setShowFullHistoryAway },
            ].map(({ team, recent, fallback, expanded, setExpanded }) => (
              <div key={team}>
                <div className="flex items-center gap-2 mb-3">
                  <span className="text-2xl">{emoji(team)}</span>
                  <span className="font-display font-semibold text-sm">{team}</span>
                </div>
                {recent.length > 0 ? (
                  <>
                    <div className="space-y-1">
                      {(expanded ? recent : recent.slice(0, 5)).map((r, i) => {
                        const result = r.result === 'W' ? 'V' : r.result === 'D' ? 'N' : 'D'
                        const chip = formChip(result)
                        return (
                          <div key={i} className="flex items-center gap-2 px-2 py-1.5 rounded text-[0.68rem]"
                               style={{ background: i % 2 ? 'transparent' : 'var(--surface2)' }}>
                            <span className="font-mono w-4 h-4 flex items-center justify-center rounded font-bold text-[0.55rem]"
                                  style={{ background: chip.bg, color: chip.col }}>
                              {result}
                            </span>
                            <span className="font-mono flex-1 truncate" style={{ color: 'var(--text-dim)' }}>
                              {r.is_home ? 'vs' : '@'} {r.opponent_name}
                            </span>
                            <span className="font-display font-bold">
                              {r.goals_for}-{r.goals_against}
                            </span>
                            <span className="font-mono text-[0.55rem]" style={{ color: 'var(--text-muted)' }}>
                              {r.match_date.slice(5)}
                            </span>
                          </div>
                        )
                      })}
                    </div>
                    {recent.length > 5 && (
                      <button onClick={() => setExpanded(!expanded)}
                        className="mt-2 font-mono text-[0.62rem] uppercase tracking-wider"
                        style={{ color: 'var(--accent)' }}>
                        {expanded ? '— Voir moins' : `+ Voir plus (${recent.length - 5})`}
                      </button>
                    )}
                  </>
                ) : (
                  <div className="flex gap-1">
                    {(fallback || 'NNNNN').split('').map((c, i) => {
                      const chip = formChip(c)
                      return (
                        <span key={i} className="w-7 h-7 rounded-md flex items-center justify-center font-mono text-[0.7rem] font-bold"
                              style={{ background: chip.bg, color: chip.col }}>
                          {c}
                        </span>
                      )
                    })}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* SECTION 3 — Comparaison statistique */}
        {(sH && sA) && (
          <div className="card-vs p-6 mb-6">
            <SectionTitle icon={BarChart3} title="Comparaison statistique" sub="historique 2 ans" />
            <div className="grid md:grid-cols-2 gap-x-8 gap-y-5">
              <CompareBar label="Buts marqués/match" leftVal={sH.avg_goals_for} rightVal={sA.avg_goals_for}
                leftLabel={match.team_home} rightLabel={match.team_away} />
              <CompareBar label="Buts encaissés/match" leftVal={sH.avg_goals_against} rightVal={sA.avg_goals_against}
                leftLabel={match.team_home} rightLabel={match.team_away} />
              <CompareBar label="% Victoires" leftVal={sH.win_rate} rightVal={sA.win_rate} isPercent
                leftLabel={match.team_home} rightLabel={match.team_away} />
              <CompareBar label="Over 2.5 rate" leftVal={sH.over_25_rate} rightVal={sA.over_25_rate} isPercent
                leftLabel={match.team_home} rightLabel={match.team_away} />
              <CompareBar label="BTTS rate" leftVal={sH.btts_rate} rightVal={sA.btts_rate} isPercent
                leftLabel={match.team_home} rightLabel={match.team_away} />
              <CompareBar label="Clean sheets" leftVal={sH.clean_sheet_rate} rightVal={sA.clean_sheet_rate} isPercent
                leftLabel={match.team_home} rightLabel={match.team_away} />
            </div>
            <div className="mt-5 pt-5 border-t flex items-center justify-around" style={{ borderColor: 'var(--border)' }}>
              {[
                { label: `${match.team_home.split(' ')[0]} (dom)`, val: `${sH.home.wins}V / ${sH.home.played}m`, col: 'var(--accent)' },
                { label: 'H2H 2 ans', val: `${analysis?.h2h_home_wins || 0}-${analysis?.h2h_draws || 0}-${analysis?.h2h_away_wins || 0}`, col: 'var(--gold)' },
                { label: `${match.team_away.split(' ')[0]} (ext)`, val: `${sA.away.wins}V / ${sA.away.played}m`, col: 'var(--accent)' },
              ].map(x => (
                <div key={x.label} className="text-center">
                  <div className="font-mono text-[0.58rem] uppercase tracking-wider" style={{ color: 'var(--text-muted)' }}>{x.label}</div>
                  <div className="font-display font-bold text-lg" style={{ color: x.col }}>{x.val}</div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* SECTION 4 — Probabilités Poisson */}
        {probs ? (
          <div className="card-vs p-6 mb-6">
            <SectionTitle icon={Target} title="Probabilités du match" sub="Méthode Poisson · 2 ans d'historique" />
            <div className="grid grid-cols-3 gap-3 mb-4">
              <ProbTile label={`Victoire ${match.team_home.split(' ')[0]}`} value={probs.home_win} big />
              <ProbTile label="Match nul" value={probs.draw} big color="var(--gold)" />
              <ProbTile label={`Victoire ${match.team_away.split(' ')[0]}`} value={probs.away_win} big />
            </div>
            <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
              <ProbTile label="Over 1.5" value={probs.over_15} />
              <ProbTile label="Over 2.5" value={probs.over_25} />
              <ProbTile label="Over 3.5" value={probs.over_35} />
              <ProbTile label="BTTS Oui" value={probs.btts_yes} />
              <ProbTile label="BTTS Non" value={probs.btts_no} />
            </div>
            {probs.top_scores?.length > 0 && (
              <div className="mt-5 pt-5 border-t" style={{ borderColor: 'var(--border)' }}>
                <div className="font-mono text-[0.6rem] uppercase tracking-widest mb-3" style={{ color: 'var(--text-muted)' }}>
                  Scores les plus probables
                </div>
                <div className="flex gap-2 flex-wrap">
                  {probs.top_scores.slice(0, 5).map((s, i) => (
                    <div key={i} className="px-3 py-2 rounded-lg flex items-center gap-2"
                         style={{ background: 'var(--surface2)', border: '1px solid var(--border)' }}>
                      <span className="font-display font-bold text-lg">{s.score}</span>
                      <span className="font-mono text-[0.62rem]" style={{ color: 'var(--accent)' }}>{s.prob}%</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        ) : (
          <div className="card-vs p-6 mb-6 text-center">
            <SectionTitle icon={Target} title="Probabilités du match" sub="Disponible après analyse IA" />
            <p className="font-mono text-[0.72rem]" style={{ color: 'var(--text-muted)' }}>
              Lance une analyse IA pour calculer les probabilités Poisson basées sur 2 ans d&apos;historique.
            </p>
          </div>
        )}

        {/* SECTION 5 — Historique H2H */}
        {h2hRec.length > 0 && (
          <div className="card-vs p-6 mb-6">
            <SectionTitle icon={TrendingUp} title="Historique des confrontations" sub={`${h2hRec.length} dernières rencontres`} />
            <div className="grid grid-cols-3 gap-3 mb-4">
              {[
                { count: analysis?.h2h_home_wins || 0, label: `Victoires ${match.team_home.split(' ')[0]}`, color: 'var(--accent)' },
                { count: analysis?.h2h_draws || 0,     label: 'Nuls',                                       color: 'var(--gold)' },
                { count: analysis?.h2h_away_wins || 0, label: `Victoires ${match.team_away.split(' ')[0]}`, color: 'var(--red)' },
              ].map(x => (
                <div key={x.label} className="card-vs p-4 text-center">
                  <div className="font-display font-extrabold text-3xl" style={{ color: x.color }}>{x.count}</div>
                  <div className="font-mono text-[0.55rem] uppercase tracking-wider mt-1" style={{ color: 'var(--text-muted)' }}>{x.label}</div>
                </div>
              ))}
            </div>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr style={{ borderBottom: '1px solid var(--border)' }}>
                    {['Date', 'Domicile', 'Score', 'Extérieur'].map(h => (
                      <th key={h} className="px-3 py-2 text-left font-mono text-[0.58rem] uppercase tracking-wider"
                          style={{ color: 'var(--text-muted)' }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {h2hRec.map((r, i) => {
                    const home = r.home ? match.team_home : match.team_away
                    const away = r.home ? match.team_away : match.team_home
                    const homeGoals = r.home ? r.gf : r.ga
                    const awayGoals = r.home ? r.ga : r.gf
                    return (
                      <tr key={i} style={{ borderBottom: '1px solid var(--border)' }}>
                        <td className="px-3 py-2 font-mono text-[0.65rem]" style={{ color: 'var(--text-dim)' }}>{r.date}</td>
                        <td className="px-3 py-2 font-display font-semibold text-[0.78rem]">{home}</td>
                        <td className="px-3 py-2 font-display font-bold text-[0.85rem]">
                          {homeGoals} <span style={{ color: 'var(--text-muted)' }}>-</span> {awayGoals}
                        </td>
                        <td className="px-3 py-2 font-display font-semibold text-[0.78rem]">{away}</td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* SECTION 6 — Analyse IA */}
        <div className="card-vs overflow-hidden mb-6">
          <div className="px-6 py-4 flex items-center justify-between border-b" style={{ borderColor: 'var(--border)' }}>
            <div className="flex items-center gap-2">
              <Brain size={16} style={{ color: 'var(--accent)' }} />
              <span className="font-display font-bold">Analyse IA</span>
              <span className="font-mono text-[0.6rem] uppercase tracking-widest ml-1" style={{ color: 'var(--text-muted)' }}>
                · Claude Sonnet
              </span>
            </div>
            {!analysis && (
              <span className="font-mono text-[0.6rem]" style={{ color: 'var(--text-muted)' }}>1 crédit</span>
            )}
          </div>

          {!analysis && !analysing && (
            <div className="px-6 py-8 text-center">
              <p className="font-mono text-[0.75rem] mb-5" style={{ color: 'var(--text-muted)' }}>
                Génère une analyse structurée — probabilités Poisson, forme, H2H, recommandation et score de confiance
              </p>
              <button onClick={handleAnalyse}
                className="inline-flex items-center gap-2 px-6 py-3 rounded-xl font-display font-semibold text-[0.85rem] transition-all hover:opacity-90 active:scale-[0.98]"
                style={{ background: 'var(--accent)', color: 'var(--bg)' }}>
                <Sparkles size={15} /> Analyser ce match — 1 crédit
              </button>
            </div>
          )}

          {analysing && (
            <div className="px-6 py-10 flex flex-col items-center gap-3">
              <div className="w-6 h-6 rounded-full border-2 animate-spin"
                   style={{ borderColor: 'var(--border)', borderTopColor: 'var(--accent)' }} />
              <p className="font-mono text-[0.72rem]" style={{ color: 'var(--text-muted)' }}>
                Analyse en cours — Poisson · forme · H2H · Claude…
              </p>
            </div>
          )}

          {analysis && (
            <div className="p-6 space-y-5">
              <div className="rounded-xl px-5 py-5" style={{ background: 'var(--accent-dim)', border: '1px solid var(--border-accent)' }}>
                <div className="font-mono text-[0.6rem] uppercase tracking-widest mb-2" style={{ color: 'var(--accent)' }}>
                  Verdict
                </div>
                <div className="font-display font-extrabold text-xl md:text-2xl">{analysis.recommendation}</div>
              </div>

              <div className="flex items-center justify-between gap-4">
                <div className="flex-1">
                  <div className="flex items-center justify-between mb-1.5">
                    <span className="font-mono text-[0.62rem] uppercase tracking-wider" style={{ color: 'var(--text-muted)' }}>
                      Score de confiance
                    </span>
                    <span className="font-display font-extrabold text-lg" style={{ color: 'var(--accent)' }}>
                      {analysis.confidence}%
                    </span>
                  </div>
                  <div className="bar-track" style={{ height: 8 }}>
                    <div className="bar-fill-progress"
                         style={{
                           width: `${analysis.confidence}%`,
                           background: `linear-gradient(90deg, var(--accent), ${analysis.confidence >= 80 ? 'var(--accent)' : analysis.confidence >= 60 ? 'var(--gold)' : 'var(--red)'})`,
                         }} />
                  </div>
                </div>
                <div className="flex-shrink-0">
                  <span className="font-mono text-[0.65rem] uppercase tracking-wider px-3 py-1.5 rounded-lg flex items-center gap-1.5"
                        style={{ background: riskBg(analysis.risk_level), color: riskColor(analysis.risk_level), border: `1px solid ${riskColor(analysis.risk_level)}30` }}>
                    {analysis.risk_level === 'faible' ? <Shield size={11} /> : <AlertTriangle size={11} />}
                    Risque {analysis.risk_level}
                  </span>
                </div>
              </div>

              {analysis.best_bet_label && analysis.best_odds && (
                <div className="rounded-xl p-4" style={{ background: 'var(--surface2)', border: '1px solid var(--border)' }}>
                  <div className="font-mono text-[0.6rem] uppercase tracking-widest mb-2" style={{ color: 'var(--text-muted)' }}>
                    Meilleur pari
                  </div>
                  <div className="flex items-center justify-between gap-3 flex-wrap">
                    <div>
                      <div className="font-display font-bold text-base">{analysis.best_bet_label}</div>
                      <div className="font-mono text-[0.65rem]" style={{ color: 'var(--text-dim)' }}>
                        @ {analysis.best_odds.toFixed(2)} chez {analysis.best_bookmaker}
                      </div>
                    </div>
                    {analysis.best_ev_pct != null && (
                      <div className="font-display font-bold text-2xl" style={{ color: 'var(--accent)' }}>
                        +{analysis.best_ev_pct}%
                        <span className="font-mono text-[0.6rem] ml-1" style={{ color: 'var(--text-muted)' }}>EV</span>
                      </div>
                    )}
                  </div>
                </div>
              )}

              <div className="rounded-xl p-4" style={{ background: 'var(--surface2)', border: '1px solid var(--border)' }}>
                <div className="font-mono text-[0.6rem] uppercase tracking-wider mb-2" style={{ color: 'var(--text-muted)' }}>
                  Note IA
                </div>
                <p className="font-mono text-[0.75rem] leading-relaxed" style={{ color: 'var(--text)' }}>
                  {analysis.reasoning}
                </p>
              </div>

              <div>
                <div className="font-mono text-[0.6rem] uppercase tracking-wider mb-2" style={{ color: 'var(--text-muted)' }}>
                  Facteurs clés
                </div>
                <div className="space-y-1.5">
                  {analysis.factors.map((f, i) => (
                    <div key={i} className="flex items-start gap-2 font-mono text-[0.72rem]">
                      <span style={{ color: 'var(--accent)' }}>→</span>
                      <span style={{ color: 'var(--text)' }}>{f}</span>
                    </div>
                  ))}
                </div>
              </div>

              {analysis.data_source === 'demo' && (
                <div className="font-mono text-[0.58rem] text-center pt-1" style={{ color: 'var(--text-muted)' }}>
                  * Stats générées en mode démo — configure API_FOOTBALL_KEY pour les données réelles sur 2 ans
                </div>
              )}
            </div>
          )}
        </div>

        {/* SECTION 7 — Value Bets */}
        {match.value_bets.length > 0 && (
          <div className="mb-6">
            <SectionTitle icon={Zap} title="Value Bets disponibles" sub={`${match.value_bets.length} signal${match.value_bets.length > 1 ? 's' : ''} via Pinnacle`} />
            <div className="card-vs overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr style={{ borderBottom: '1px solid var(--border)' }}>
                    {['Pari', 'Bookmaker', 'Cote', 'Fair', 'EV', 'Kelly', 'Mise/1000€'].map(h => (
                      <th key={h} className="px-4 py-3 text-left font-mono text-[0.58rem] uppercase tracking-wider"
                          style={{ color: 'var(--text-muted)' }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {match.value_bets.map((vb, i) => (
                    <tr key={i} style={{ borderBottom: '1px solid var(--border)', position: 'relative' }}>
                      <td className="px-4 py-3">
                        <div className="font-display font-semibold text-[0.82rem] flex items-center gap-1.5">
                          {vb.is_strong && <Zap size={11} style={{ color: 'var(--accent)' }} />}
                          {vb.bet_label}
                        </div>
                      </td>
                      <td className="px-4 py-3 font-mono text-[0.72rem]">{vb.bookmaker}</td>
                      <td className="px-4 py-3 font-display font-bold text-[0.85rem]">{vb.odds.toFixed(2)}</td>
                      <td className="px-4 py-3 font-mono text-[0.7rem]" style={{ color: 'var(--text-muted)' }}>{vb.fair_odds.toFixed(2)}</td>
                      <td className="px-4 py-3 font-display font-bold" style={{ color: 'var(--accent)' }}>+{vb.ev_pct.toFixed(1)}%</td>
                      <td className="px-4 py-3 font-mono text-[0.72rem]">{vb.kelly_pct.toFixed(1)}%</td>
                      <td className="px-4 py-3 font-display font-bold text-[0.82rem]">{vb.stake_1000.toFixed(2)}€</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
