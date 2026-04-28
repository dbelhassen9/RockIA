'use client'
import { useEffect, useState } from 'react'
import { useRouter, useParams } from 'next/navigation'
import toast from 'react-hot-toast'
import Navbar from '@/components/Navbar'
import { getMatch, analyseMatch, Match, AnalysisResult } from '@/lib/api'
import { useUserStore } from '@/lib/store'
import { ArrowLeft, TrendingUp, Zap, Brain, Activity, Shield, AlertTriangle } from 'lucide-react'

export default function MatchDetailPage() {
  const router   = useRouter()
  const params   = useParams()
  const { loadUser } = useUserStore()
  const [match,     setMatch]     = useState<Match | null>(null)
  const [loading,   setLoading]   = useState(true)
  const [analysis,  setAnalysis]  = useState<AnalysisResult | null>(null)
  const [analysing, setAnalysing] = useState(false)

  useEffect(() => {
    loadUser().then(() => {
      if (!useUserStore.getState().user) router.push('/login')
    })
    if (params.id) {
      getMatch(params.id as string)
        .then(setMatch)
        .catch((e: any) => { toast.error(e.message); router.push('/agenda') })
        .finally(() => setLoading(false))
    }
  }, [params.id])

  const handleAnalyse = async () => {
    if (!params.id) return
    setAnalysing(true)
    try {
      const res = await analyseMatch(params.id as string)
      setAnalysis(res)
      if (!res.from_cache)
        toast.success(`Analyse générée — ${res.credits_remaining} crédit${res.credits_remaining > 1 ? 's' : ''} restant${res.credits_remaining > 1 ? 's' : ''}`)
    } catch (e: any) {
      toast.error(e.message)
    } finally {
      setAnalysing(false)
    }
  }

  if (loading) return (
    <div className="min-h-screen">
      <Navbar />
      <div className="max-w-4xl mx-auto px-6 py-8 space-y-4">
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

  return (
    <div className="min-h-screen">
      <Navbar />
      <div className="max-w-4xl mx-auto px-6 py-8">
        <button onClick={() => router.back()}
          className="flex items-center gap-2 mb-6 font-mono text-[0.72rem] uppercase tracking-wider transition-colors"
          style={{ color: 'var(--text-muted)' }}
          onMouseEnter={e => (e.currentTarget.style.color = 'var(--accent)')}
          onMouseLeave={e => (e.currentTarget.style.color = 'var(--text-muted)')}>
          <ArrowLeft size={14} /> Retour à l&apos;agenda
        </button>

        {/* Header match */}
        <div className="rounded-2xl p-8 mb-6 relative overflow-hidden"
          style={{ background: 'var(--surface)', border: `1px solid ${match.is_strong ? 'var(--border-accent)' : 'var(--border)'}` }}>
          {match.is_strong && (
            <div className="absolute top-0 left-0 right-0 h-px"
              style={{ background: 'linear-gradient(90deg,transparent,var(--accent),transparent)' }} />
          )}
          <div className="font-mono text-[0.62rem] uppercase tracking-widest mb-3" style={{ color: 'var(--text-muted)' }}>
            {match.league}
          </div>
          <div className="flex items-center justify-center gap-8 mb-4">
            <div className="text-center">
              <div className="font-display font-extrabold text-3xl tracking-tight mb-1">{match.team_home}</div>
              <div className="font-mono text-[0.68rem]" style={{ color: 'var(--text-muted)' }}>Domicile</div>
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
            <div className="text-center">
              <div className="font-display font-extrabold text-3xl tracking-tight mb-1">{match.team_away}</div>
              <div className="font-mono text-[0.68rem]" style={{ color: 'var(--text-muted)' }}>Extérieur</div>
            </div>
          </div>
          <div className="text-center font-mono text-[0.7rem]" style={{ color: 'var(--text-muted)' }}>{time}</div>
        </div>

        {/* Value bets */}
        {match.value_bets.length > 0 ? (
          <div className="mb-6">
            <div className="flex items-center gap-3 mb-4">
              <TrendingUp size={16} style={{ color: 'var(--accent)' }} />
              <span className="font-display font-bold text-xl">Value Bets détectés</span>
              <span className="font-mono text-[0.65rem] px-2 py-0.5 rounded"
                style={{ background: 'var(--accent-dim)', color: 'var(--accent)', border: '1px solid var(--border-accent)' }}>
                {match.value_bets.length} signal{match.value_bets.length > 1 ? 's' : ''}
              </span>
            </div>
            <div className="flex flex-col gap-3">
              {match.value_bets.map((vb, i) => (
                <div key={i} className="rounded-xl p-5 relative overflow-hidden"
                  style={{ background: 'var(--surface)', border: `1px solid ${vb.is_strong ? 'var(--border-accent)' : 'var(--border)'}` }}>
                  {vb.is_strong && (
                    <div className="absolute left-0 top-0 bottom-0 w-[3px] rounded-l-xl"
                      style={{ background: 'var(--accent)', boxShadow: '0 0 10px var(--accent-glow)' }} />
                  )}
                  <div className="pl-3 grid grid-cols-2 md:grid-cols-4 gap-4">
                    <div>
                      <div className="font-mono text-[0.58rem] uppercase tracking-wider mb-1" style={{ color: 'var(--text-muted)' }}>Pari</div>
                      <div className="font-display font-semibold">{vb.bet_label}</div>
                      <div className="font-mono text-[0.65rem]" style={{ color: 'var(--text-dim)' }}>{vb.bookmaker}</div>
                    </div>
                    <div>
                      <div className="font-mono text-[0.58rem] uppercase tracking-wider mb-1" style={{ color: 'var(--text-muted)' }}>Cote</div>
                      <div className="font-display font-bold text-2xl">{vb.odds.toFixed(2)}</div>
                      <div className="font-mono text-[0.62rem]" style={{ color: 'var(--text-muted)' }}>
                        Fair: {vb.fair_odds.toFixed(2)}
                      </div>
                    </div>
                    <div>
                      <div className="font-mono text-[0.58rem] uppercase tracking-wider mb-1" style={{ color: 'var(--text-muted)' }}>EV</div>
                      <div className="font-display font-bold text-2xl" style={{ color: 'var(--accent)' }}>+{vb.ev_pct.toFixed(1)}%</div>
                      {vb.is_strong && (
                        <div className="flex items-center gap-1 font-mono text-[0.6rem]" style={{ color: 'var(--accent)' }}>
                          <Zap size={10} /> Signal fort
                        </div>
                      )}
                    </div>
                    <div>
                      <div className="font-mono text-[0.58rem] uppercase tracking-wider mb-1" style={{ color: 'var(--text-muted)' }}>Kelly</div>
                      <div className="font-display font-bold text-xl">{vb.kelly_pct.toFixed(1)}%</div>
                      <div className="font-mono text-[0.62rem]" style={{ color: 'var(--text-muted)' }}>
                        Mise / 100€ : {vb.stake_100.toFixed(2)}€
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        ) : (
          <div className="text-center py-12 font-mono text-[0.8rem] rounded-xl mb-6"
            style={{ background: 'var(--surface)', border: '1px solid var(--border)', color: 'var(--text-muted)' }}>
            Aucun value bet détecté pour ce match
          </div>
        )}

        {/* ── Analyse IA ── */}
        <div className="rounded-2xl overflow-hidden"
          style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}>
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
                Génère une analyse structurée : xG, forme, H2H, recommandation et score de confiance
              </p>
              <button onClick={handleAnalyse}
                className="inline-flex items-center gap-2 px-6 py-3 rounded-xl font-display font-semibold text-[0.85rem] transition-all hover:opacity-90 active:scale-[0.98]"
                style={{ background: 'var(--accent)', color: 'var(--bg)' }}>
                <Brain size={15} /> Analyser ce match — 1 crédit
              </button>
            </div>
          )}

          {analysing && (
            <div className="px-6 py-10 flex flex-col items-center gap-3">
              <div className="w-6 h-6 rounded-full border-2 animate-spin"
                style={{ borderColor: 'var(--border)', borderTopColor: 'var(--accent)' }} />
              <p className="font-mono text-[0.72rem]" style={{ color: 'var(--text-muted)' }}>
                Analyse en cours — xG · forme · H2H · Claude…
              </p>
            </div>
          )}

          {analysis && (
            <div className="p-6 space-y-5">
              {/* Confiance + risque */}
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
                  <div className="h-2 rounded-full overflow-hidden" style={{ background: 'var(--border)' }}>
                    <div className="h-full rounded-full transition-all duration-700"
                      style={{
                        width: `${analysis.confidence}%`,
                        background: `linear-gradient(90deg, var(--accent), ${analysis.confidence >= 80 ? 'var(--accent)' : analysis.confidence >= 60 ? 'var(--gold)' : 'var(--red)'})`,
                        boxShadow: '0 0 8px var(--accent-glow)'
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

              {/* Recommandation */}
              <div className="rounded-xl px-5 py-4" style={{ background: 'var(--accent-dim)', border: '1px solid var(--border-accent)' }}>
                <div className="font-mono text-[0.6rem] uppercase tracking-widest mb-1" style={{ color: 'var(--accent)' }}>
                  Recommandation
                </div>
                <div className="font-display font-bold text-[1rem]">{analysis.recommendation}</div>
              </div>

              {/* Stats xG + forme + H2H */}
              <div className="grid grid-cols-3 gap-3">
                <div className="rounded-xl p-4" style={{ background: 'var(--surface2)', border: '1px solid var(--border)' }}>
                  <div className="font-mono text-[0.58rem] uppercase tracking-wider mb-2 flex items-center gap-1" style={{ color: 'var(--text-muted)' }}>
                    <Activity size={10} /> xG moyen
                  </div>
                  <div className="flex items-baseline gap-1.5">
                    <span className="font-display font-bold text-xl">{analysis.xg_home}</span>
                    <span className="font-mono text-[0.65rem]" style={{ color: 'var(--text-muted)' }}>vs</span>
                    <span className="font-display font-bold text-xl">{analysis.xg_away}</span>
                  </div>
                  <div className="font-mono text-[0.58rem] mt-1" style={{ color: 'var(--text-muted)' }}>
                    {match.team_home.split(' ')[0]} · {match.team_away.split(' ')[0]}
                  </div>
                </div>

                <div className="rounded-xl p-4" style={{ background: 'var(--surface2)', border: '1px solid var(--border)' }}>
                  <div className="font-mono text-[0.58rem] uppercase tracking-wider mb-2" style={{ color: 'var(--text-muted)' }}>
                    Forme récente
                  </div>
                  <div className="space-y-1.5">
                    {[
                      { label: match.team_home.split(' ')[0], form: analysis.form_home },
                      { label: match.team_away.split(' ')[0], form: analysis.form_away },
                    ].map(({ label, form }) => (
                      <div key={label} className="flex items-center gap-1.5">
                        <span className="font-mono text-[0.58rem] w-10 truncate" style={{ color: 'var(--text-muted)' }}>{label}</span>
                        <div className="flex gap-0.5">
                          {form.split('').map((c, i) => (
                            <span key={i} className="w-4 h-4 rounded-sm flex items-center justify-center font-mono text-[0.5rem] font-bold"
                              style={{
                                background: c === 'V' ? 'var(--accent-dim)' : c === 'D' ? 'var(--red-dim)' : 'var(--gold-dim)',
                                color: c === 'V' ? 'var(--accent)' : c === 'D' ? 'var(--red)' : 'var(--gold)',
                              }}>
                              {c}
                            </span>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="rounded-xl p-4" style={{ background: 'var(--surface2)', border: '1px solid var(--border)' }}>
                  <div className="font-mono text-[0.58rem] uppercase tracking-wider mb-2" style={{ color: 'var(--text-muted)' }}>
                    H2H (5 matchs)
                  </div>
                  <div className="flex items-center gap-1 mt-1">
                    {[
                      { count: analysis.h2h_home_wins, label: 'Dom', color: 'var(--accent)' },
                      { count: analysis.h2h_draws,     label: 'Nul', color: 'var(--gold)' },
                      { count: analysis.h2h_away_wins, label: 'Ext', color: 'var(--red)' },
                    ].map(({ count, label, color }) => (
                      <div key={label} className="flex-1 text-center">
                        <div className="font-display font-bold text-xl" style={{ color }}>{count}</div>
                        <div className="font-mono text-[0.55rem] uppercase" style={{ color: 'var(--text-muted)' }}>{label}</div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              {/* Raisonnement */}
              <div className="rounded-xl p-4" style={{ background: 'var(--surface2)', border: '1px solid var(--border)' }}>
                <div className="font-mono text-[0.6rem] uppercase tracking-wider mb-2" style={{ color: 'var(--text-muted)' }}>
                  Analyse
                </div>
                <p className="font-mono text-[0.75rem] leading-relaxed" style={{ color: 'var(--text)' }}>
                  {analysis.reasoning}
                </p>
              </div>

              {/* Facteurs clés */}
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
                  * Stats xG/forme générées en mode démo — configure API_FOOTBALL_KEY pour les données réelles
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
