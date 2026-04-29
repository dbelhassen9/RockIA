'use client'
import{useEffect,useState}from 'react'
import{useRouter}from 'next/navigation'
import toast from 'react-hot-toast'
import Navbar from '@/components/Navbar'
import{getStats,getBets,Stats,Bet,AnalysisResult}from '@/lib/api'
import{useUserStore}from '@/lib/store'
import{Brain}from 'lucide-react'

interface StoredAnalysis { id: string; analysis: AnalysisResult }

export default function StatsPage(){
  const router=useRouter()
  const{loadUser}=useUserStore()
  const[stats,setStats]=useState<Stats|null>(null)
  const[bets,setBets]=useState<Bet[]>([])
  const[loading,setLoading]=useState(true)
  const[analyses,setAnalyses]=useState<StoredAnalysis[]>([])

  useEffect(()=>{
    loadUser().then(()=>{if(!useUserStore.getState().user)router.push('/login')})
    Promise.all([getStats(),getBets()]).then(([s,b])=>{setStats(s);setBets(b.bets)})
      .catch(e=>toast.error(e.message)).finally(()=>setLoading(false))

    if(typeof window!=='undefined'){
      const out:StoredAnalysis[]=[]
      for(let i=0;i<localStorage.length;i++){
        const k=localStorage.key(i)
        if(k?.startsWith('rockai_analysis_')){
          try{
            const v=JSON.parse(localStorage.getItem(k)!)as AnalysisResult
            out.push({id:k.replace('rockai_analysis_',''),analysis:v})
          }catch{/* skip */}
        }
      }
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setAnalyses(out)
    }
  },[])

  const kpis=[
    {label:'ROI Global',val:stats?`${stats.roi>=0?'+':''}${stats.roi}%`:'—',color:'var(--accent)'},
    {label:'Taux de réussite',val:stats?`${stats.win_rate}%`:'—',color:'#00b8ff'},
    {label:'Profit net',val:stats?`${stats.total_profit>=0?'+':''}${stats.total_profit}€`:'—',color:'var(--gold)'},
    {label:'Analyses IA',val:String(analyses.length),color:'var(--accent)'},
  ]

  return(
    <div className="min-h-screen">
      <Navbar/>
      <div className="max-w-5xl mx-auto px-6 py-8">
        <div className="mb-8">
          <h1 className="font-display font-extrabold text-3xl tracking-tight mb-1">Historique</h1>
          <p className="font-mono text-[0.72rem]" style={{color:'var(--text-muted)'}}>{'// Performances · paris · analyses IA passées'}</p>
        </div>
        <div className="grid grid-cols-4 gap-4 mb-8">
          {kpis.map(({label,val,color})=>(
            <div key={label} className="rounded-xl p-5" style={{background:'var(--surface)',border:'1px solid var(--border)'}}>
              <div className="font-mono text-[0.62rem] uppercase tracking-wider mb-2" style={{color:'var(--text-muted)'}}>{label}</div>
              <div className="font-display font-extrabold text-3xl tracking-tight" style={{color}}>{val}</div>
            </div>
          ))}
        </div>
        {analyses.length>0&&(
          <div className="rounded-2xl overflow-hidden mb-8" style={{background:'var(--surface)',border:'1px solid var(--border)'}}>
            <div className="px-6 py-4 border-b flex items-center gap-2" style={{borderColor:'var(--border)'}}>
              <Brain size={14} style={{color:'var(--accent)'}}/>
              <span className="font-display font-bold">Analyses IA passées</span>
              <span className="font-mono text-[0.6rem] uppercase tracking-widest ml-1" style={{color:'var(--text-muted)'}}>· {analyses.length}</span>
            </div>
            <div className="divide-y" style={{borderColor:'var(--border)'}}>
              {analyses.map(({id,analysis})=>(
                <div key={id} onClick={()=>router.push(`/match/${id}`)}
                     className="px-6 py-4 cursor-pointer transition-colors hover:bg-white/5">
                  <div className="flex items-start justify-between gap-3 flex-wrap">
                    <div className="flex-1 min-w-0">
                      <div className="font-display font-semibold text-[0.85rem] truncate">{analysis.recommendation}</div>
                      <div className="font-mono text-[0.62rem] mt-1" style={{color:'var(--text-muted)'}}>
                        Confiance {analysis.confidence}% · Risque {analysis.risk_level} · Source {analysis.data_source}
                      </div>
                    </div>
                    {analysis.best_ev_pct!=null&&(
                      <span className="font-display font-bold text-base" style={{color:'var(--accent)'}}>
                        +{analysis.best_ev_pct}%
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        <div className="rounded-2xl overflow-hidden" style={{background:'var(--surface)',border:'1px solid var(--border)'}}>
          <div className="px-6 py-4 border-b" style={{borderColor:'var(--border)'}}>
            <span className="font-display font-bold">Historique des paris</span>
          </div>
          {loading?(
            <div className="p-6 space-y-3">{[...Array(5)].map((_,i)=><div key={i} className="h-12 rounded-lg animate-pulse" style={{background:'var(--surface2)'}}/>)}</div>
          ):bets.length===0?(
            <div className="px-6 py-12 text-center font-mono text-[0.8rem]" style={{color:'var(--text-muted)'}}>Aucun pari enregistré</div>
          ):(
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead><tr style={{borderBottom:'1px solid var(--border)'}}>
                  {['Match','Pari','Cote','EV','Mise','Résultat','P&L'].map(h=>(
                    <th key={h} className="px-4 py-3 text-left font-mono text-[0.6rem] uppercase tracking-wider" style={{color:'var(--text-muted)'}}>{h}</th>
                  ))}
                </tr></thead>
                <tbody>
                  {bets.map(b=>(
                    <tr key={b.id} style={{borderBottom:'1px solid var(--border)'}}
                        onMouseEnter={e=>(e.currentTarget.style.background='var(--surface2)')}
                        onMouseLeave={e=>(e.currentTarget.style.background='')}>
                      <td className="px-4 py-3">
                        <div className="font-display font-semibold text-[0.82rem]">{b.team_home} vs {b.team_away}</div>
                        <div className="font-mono text-[0.6rem]" style={{color:'var(--text-muted)'}}>{b.sport} · {new Date(b.placed_at).toLocaleDateString('fr-FR')}</div>
                      </td>
                      <td className="px-4 py-3 font-mono text-[0.75rem]">{b.bet_label}</td>
                      <td className="px-4 py-3 font-mono text-[0.78rem]">{b.odds}</td>
                      <td className="px-4 py-3 font-mono text-[0.75rem]" style={{color:'var(--accent)'}}>{b.ev>0?'+':''}{(b.ev*100).toFixed(1)}%</td>
                      <td className="px-4 py-3 font-mono text-[0.75rem]">{b.stake}€</td>
                      <td className="px-4 py-3">
                        <span className="font-mono text-[0.65rem] px-2 py-0.5 rounded"
                              style={{background:b.result==='won'?'var(--accent-dim)':b.result==='lost'?'var(--red-dim)':'var(--gold-dim)',
                                color:b.result==='won'?'var(--accent)':b.result==='lost'?'var(--red)':'var(--gold)'}}>
                          {b.result==='won'?'Gagné':b.result==='lost'?'Perdu':'En cours'}
                        </span>
                      </td>
                      <td className="px-4 py-3 font-display font-bold text-[0.85rem]"
                          style={{color:b.profit>=0?'var(--accent)':'var(--red)'}}>{b.profit>=0?'+':''}{b.profit}€</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
