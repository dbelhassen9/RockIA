'use client'
import{useEffect,useState}from 'react'
import{useRouter}from 'next/navigation'
import toast from 'react-hot-toast'
import Navbar from '@/components/Navbar'
import MatchCard from '@/components/MatchCard'
import{getMatches,Match,MatchesResponse}from '@/lib/api'
import{useUserStore}from '@/lib/store'
import{RefreshCw}from 'lucide-react'

const FILTERS=[
  {label:'Tous',params:''},
  {label:'🔥 Value Bets',params:'value_only=true'},
  {label:'Signaux forts',params:'strong_only=true'},
]

export default function AgendaPage(){
  const router=useRouter()
  const{loadUser}=useUserStore()
  const[data,setData]=useState<MatchesResponse|null>(null)
  const[loading,setLoading]=useState(true)
  const[activeFilter,setActiveFilter]=useState(0)
  const[refreshing,setRefreshing]=useState(false)

  useEffect(()=>{loadUser().then(()=>{if(!useUserStore.getState().user)router.push('/login')})},[])
  useEffect(()=>{load()},[activeFilter])

  const load=async(silent=false)=>{
    if(!silent)setLoading(true);else setRefreshing(true)
    try{const res=await getMatches(FILTERS[activeFilter].params);setData(res)}
    catch(e:any){toast.error(e.message)}
    finally{setLoading(false);setRefreshing(false)}
  }

  const grouped:Record<string,Match[]>={}
  data?.matches.forEach(m=>{
    const d=new Date(m.commence_time),now=new Date()
    const isToday=d.toDateString()===now.toDateString()
    const isTom=d.toDateString()===new Date(Date.now()+86400000).toDateString()
    const key=isToday?`Aujourd'hui — ${d.toLocaleDateString('fr-FR',{weekday:'long',day:'numeric',month:'long'})}`
      :isTom?`Demain — ${d.toLocaleDateString('fr-FR',{weekday:'long',day:'numeric',month:'long'})}`
      :d.toLocaleDateString('fr-FR',{weekday:'long',day:'numeric',month:'long'})
    if(!grouped[key])grouped[key]=[]
    grouped[key].push(m)
  })

  return(
    <div className="min-h-screen">
      <Navbar/>
      <div className="max-w-5xl mx-auto px-6 py-8">
        <div className="flex items-baseline justify-between mb-6">
          <div>
            <h1 className="font-display font-extrabold text-3xl tracking-tight mb-1">Agenda des matchs</h1>
            <p className="font-mono text-[0.72rem]" style={{color:'var(--text-muted)'}}>
              {data?`// ${data.count} matchs · ${data.value_count} value bets · ${data.strong_count} signaux forts · mode ${data.mode}`:'// Chargement...'}
            </p>
          </div>
          <button onClick={()=>load(true)} disabled={refreshing}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg font-mono text-[0.7rem] transition-all disabled:opacity-50"
            style={{background:'var(--surface)',border:'1px solid var(--border)',color:'var(--text-dim)'}}>
            <RefreshCw size={12} className={refreshing?'animate-spin':''}/>Actualiser
          </button>
        </div>

        <div className="flex gap-2 mb-6 flex-wrap">
          {FILTERS.map(({label},i)=>(
            <button key={i} onClick={()=>setActiveFilter(i)}
              className="font-mono text-[0.68rem] uppercase tracking-wider px-4 py-1.5 rounded-full transition-all"
              style={{background:activeFilter===i?'var(--accent-dim)':'transparent',
                border:activeFilter===i?'1px solid var(--border-accent)':'1px solid var(--border)',
                color:activeFilter===i?'var(--accent)':'var(--text-dim)'}}>
              {label}
            </button>
          ))}
        </div>

        {loading?(
          <div className="flex flex-col gap-3">
            {[...Array(5)].map((_,i)=>(
              <div key={i} className="h-20 rounded-xl animate-pulse" style={{background:'var(--surface)'}}/>
            ))}
          </div>
        ):Object.keys(grouped).length===0?(
          <div className="text-center py-20 font-mono text-[0.8rem]" style={{color:'var(--text-muted)'}}>
            Aucun match trouvé pour ce filtre
          </div>
        ):(
          Object.entries(grouped).map(([date,matches])=>(
            <div key={date} className="mb-8">
              <div className="flex items-center gap-3 mb-3">
                <span className="font-mono text-[0.65rem] uppercase tracking-widest" style={{color:'var(--text-muted)'}}>
                  {date.charAt(0).toUpperCase()+date.slice(1)}
                </span>
                <div className="flex-1 h-px" style={{background:'var(--border)'}}/>
              </div>
              <div className="flex flex-col gap-2">
                {matches.map(m=>(
                  <MatchCard key={m.match_id} match={m} onClick={()=>router.push(`/match/${m.match_id}`)}/>
                ))}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  )
}
