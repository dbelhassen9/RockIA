# RockAI Frontend — Script d'installation automatique
# Lance depuis : C:\Users\danbe\RockIA\rockai-frontend\
# Commande : .\setup.ps1

$base = "src"

# ══════════════════════════════════════════════════════════════════
# lib/api.ts
# ══════════════════════════════════════════════════════════════════
Set-Content "$base\lib\api.ts" @'
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
'@

# ══════════════════════════════════════════════════════════════════
# lib/store.ts
# ══════════════════════════════════════════════════════════════════
Set-Content "$base\lib\store.ts" @'
import { create } from 'zustand'
import { User, getMe, setToken, clearToken } from './api'

interface UserStore {
  user: User | null
  loading: boolean
  setUser: (u: User | null) => void
  loadUser: () => Promise<void>
  logout: () => void
}

export const useUserStore = create<UserStore>((set) => ({
  user: null,
  loading: true,
  setUser: (user) => set({ user }),
  loadUser: async () => {
    try {
      const user = await getMe()
      set({ user, loading: false })
    } catch {
      set({ user: null, loading: false })
    }
  },
  logout: () => { clearToken(); set({ user: null }) },
}))
'@

# ══════════════════════════════════════════════════════════════════
# app/globals.css
# ══════════════════════════════════════════════════════════════════
Set-Content "$base\app\globals.css" @'
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;500;600;700;800&family=DM+Mono:wght@300;400;500&family=DM+Sans:wght@300;400;500&display=swap');

@tailwind base;
@tailwind components;
@tailwind utilities;

:root {
  --bg:            #080c10;
  --surface:       #0d1318;
  --surface2:      #111820;
  --border:        rgba(255,255,255,0.06);
  --border-accent: rgba(0,210,220,0.28);
  --accent:        #00d4dc;
  --accent-dim:    rgba(0,210,220,0.12);
  --accent-glow:   rgba(0,210,220,0.38);
  --red:           #ff4757;
  --red-dim:       rgba(255,71,87,0.12);
  --gold:          #ffd700;
  --gold-dim:      rgba(255,215,0,0.12);
  --text:          #e8edf2;
  --text-muted:    #4a5568;
  --text-dim:      #8892a4;
}

* { box-sizing: border-box; margin: 0; padding: 0; }
body { background: var(--bg); color: var(--text); font-family: 'DM Sans', sans-serif;
  min-height: 100vh; -webkit-font-smoothing: antialiased; }
body::before { content: ''; position: fixed; inset: 0;
  background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)' opacity='0.03'/%3E%3C/svg%3E");
  pointer-events: none; z-index: 9998; opacity: 0.4; }
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: var(--bg); }
::-webkit-scrollbar-thumb { background: var(--surface2); border-radius: 3px; }
.font-display { font-family: 'Syne', sans-serif; }
.font-mono    { font-family: 'DM Mono', monospace; }
@keyframes pulse-dot { 0%,100% { opacity:1 } 50% { opacity:0.3 } }
.pulse { animation: pulse-dot 2s infinite; }
@keyframes fadeUp { from { opacity:0; transform:translateY(10px) } to { opacity:1; transform:translateY(0) } }
.fade-up { animation: fadeUp 0.4s ease both; }
.text-accent-glow { color: var(--accent); text-shadow: 0 0 40px var(--accent-glow); }
.grid-bg {
  background-image: linear-gradient(rgba(255,255,255,0.02) 1px,transparent 1px),
    linear-gradient(90deg,rgba(255,255,255,0.02) 1px,transparent 1px);
  background-size: 60px 60px;
  mask-image: radial-gradient(ellipse 80% 80% at 50% 50%,black,transparent);
}
'@

# ══════════════════════════════════════════════════════════════════
# app/layout.tsx
# ══════════════════════════════════════════════════════════════════
Set-Content "$base\app\layout.tsx" @'
import type { Metadata } from 'next'
import { Toaster } from 'react-hot-toast'
import './globals.css'

export const metadata: Metadata = {
  title: 'RockAI — Sports Betting Intelligence',
  description: 'Détection de value bets par méthode Pinnacle.',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="fr">
      <body>
        {children}
        <Toaster position="bottom-right" toastOptions={{
          style: { background:'#0d1318', color:'#e8edf2',
            border:'1px solid rgba(0,210,220,0.25)',
            fontFamily:"'DM Mono', monospace", fontSize:'0.8rem', borderRadius:'10px' },
          success: { iconTheme: { primary:'#00d4dc', secondary:'#080c10' } },
          error:   { iconTheme: { primary:'#ff4757', secondary:'#080c10' } },
        }}/>
      </body>
    </html>
  )
}
'@

# ══════════════════════════════════════════════════════════════════
# app/page.tsx
# ══════════════════════════════════════════════════════════════════
Set-Content "$base\app\page.tsx" @'
'use client'
import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { getToken } from '@/lib/api'

export default function Home() {
  const router = useRouter()
  useEffect(() => { router.replace(getToken() ? '/agenda' : '/login') }, [router])
  return null
}
'@

# ══════════════════════════════════════════════════════════════════
# components/Navbar.tsx
# ══════════════════════════════════════════════════════════════════
Set-Content "$base\components\Navbar.tsx" @'
'use client'
import Link from 'next/link'
import { usePathname, useRouter } from 'next/navigation'
import { useUserStore } from '@/lib/store'
import { Gem, LogOut } from 'lucide-react'

export default function Navbar() {
  const pathname = usePathname()
  const router = useRouter()
  const { user, logout } = useUserStore()

  const handleLogout = () => { logout(); router.push('/login') }
  const initials = user?.full_name.split(' ').map(w=>w[0]).join('').toUpperCase().slice(0,2) ?? '?'
  const planLabel = user?.plan === 'elite' ? '🏆 Elite' : user?.plan === 'pro' ? '⭐ Pro' : '🎯 Starter'
  const credits = user?.plan === 'elite' ? '∞' : (user?.credits ?? '—')

  return (
    <nav className="sticky top-0 z-50 flex items-center justify-between px-6 h-14 border-b backdrop-blur-xl"
         style={{ background:'rgba(8,12,16,0.85)', borderColor:'var(--border)' }}>
      <Link href="/agenda" className="flex items-center gap-2">
        <span className="font-display font-extrabold text-lg tracking-tight">
          Rock<span style={{color:'var(--accent)'}}>AI</span>
        </span>
        <span className="w-1.5 h-1.5 rounded-full pulse"
              style={{background:'var(--accent)',boxShadow:'0 0 8px var(--accent-glow)'}}/>
      </Link>

      <div className="flex gap-1">
        {[{href:'/agenda',label:'Agenda'},{href:'/stats',label:'Statistiques'},{href:'/pricing',label:'Tarifs'}]
          .map(({href,label}) => (
          <Link key={href} href={href}
            className="font-mono text-[0.7rem] uppercase tracking-widest px-4 py-1.5 rounded-md transition-all"
            style={{ color:pathname===href?'var(--accent)':'var(--text-dim)',
              background:pathname===href?'var(--accent-dim)':'transparent',
              border:pathname===href?'1px solid var(--border-accent)':'1px solid transparent' }}>
            {label}
          </Link>
        ))}
      </div>

      <div className="flex items-center gap-3">
        <Link href="/pricing" className="flex items-center gap-1.5 px-3 py-1 rounded-md font-mono text-[0.65rem] uppercase tracking-wide"
              style={{background:'var(--surface2)',border:'1px solid var(--border)',color:'var(--text-dim)'}}>
          <Gem size={11} style={{color:'var(--accent)'}}/>
          <span className="font-display font-bold text-[0.78rem]" style={{color:'var(--accent)'}}>{credits}</span>
          <span>crédits</span>
        </Link>
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-full flex items-center justify-center font-display font-bold text-[0.68rem]"
               style={{background:'linear-gradient(135deg,#00d4dc,#0080ff)',color:'#080c10'}}>
            {initials}
          </div>
          <span className="font-mono text-[0.75rem]" style={{color:'var(--text-dim)'}}>
            {user?.full_name?.split(' ')[0] ?? '—'}
          </span>
          <span className="font-mono text-[0.6rem] px-1.5 py-0.5 rounded"
                style={{background:'var(--gold-dim)',color:'var(--gold)',border:'1px solid rgba(255,215,0,0.2)'}}>
            {planLabel}
          </span>
        </div>
        <button onClick={handleLogout} title="Déconnexion" className="p-1 rounded"
                style={{color:'var(--text-muted)'}}
                onMouseEnter={e=>(e.currentTarget.style.color='var(--red)')}
                onMouseLeave={e=>(e.currentTarget.style.color='var(--text-muted)')}>
          <LogOut size={14}/>
        </button>
      </div>
    </nav>
  )
}
'@

# ══════════════════════════════════════════════════════════════════
# components/MatchCard.tsx
# ══════════════════════════════════════════════════════════════════
Set-Content "$base\components\MatchCard.tsx" @'
import { Match } from '@/lib/api'

const EMOJI: Record<string,string> = {
  'Arsenal':'🔴','Chelsea':'🔵','Liverpool':'🔴','Man City':'🔵','Man United':'🔴',
  'Tottenham':'⚪','PSG':'🔵','Lyon':'🔴','Marseille':'🔵','Monaco':'🔴',
  'Bayern':'🔴','Dortmund':'🟡','Real Madrid':'⚪','Barcelona':'🔵','Atletico':'🔴',
  'Inter':'⚫','Juventus':'⚪','Napoli':'🔵','Lakers':'🟣','Celtics':'🍀',
}
function emoji(name:string){for(const[k,v]of Object.entries(EMOJI)){if(name.includes(k))return v}return'⚽'}

export default function MatchCard({match,onClick}:{match:Match,onClick:()=>void}){
  const time = new Date(match.commence_time).toLocaleTimeString('fr-FR',{hour:'2-digit',minute:'2-digit'})
  const ev   = match.best_ev_pct
  return(
    <div onClick={onClick} className="rounded-xl px-5 py-4 cursor-pointer transition-all duration-200 relative overflow-hidden"
         style={{background:'var(--surface)',border:`1px solid ${match.is_strong?'var(--border-accent)':'var(--border)'}`}}
         onMouseEnter={e=>{e.currentTarget.style.transform='translateX(4px)';e.currentTarget.style.background='var(--surface2)'}}
         onMouseLeave={e=>{e.currentTarget.style.transform='translateX(0)';e.currentTarget.style.background='var(--surface)'}}>
      <div className="absolute left-0 top-0 bottom-0 w-[3px] rounded-l-xl"
           style={{background:match.is_strong?'var(--accent)':'var(--border)',
                   boxShadow:match.is_strong?'0 0 10px var(--accent-glow)':'none'}}/>
      <div className="flex items-center gap-4 pl-2">
        <div className="flex flex-col min-w-[60px]">
          <span className="font-mono text-[0.58rem] uppercase tracking-wider truncate max-w-[80px]"
                style={{color:'var(--text-muted)'}}>{match.league}</span>
          <span className="font-display font-bold text-xl tracking-tight">{time}</span>
        </div>
        <div className="flex-1 flex items-center gap-4 justify-center">
          <div className="flex flex-col items-center gap-1">
            <span className="text-2xl">{emoji(match.team_home)}</span>
            <span className="font-display font-semibold text-sm text-center">{match.team_home}</span>
          </div>
          <div className="flex flex-col items-center gap-1">
            <span className="font-mono text-[0.6rem]" style={{color:'var(--text-muted)'}}>VS</span>
            <div className="flex gap-1">
              {[match.odds_home,match.odds_draw,match.odds_away].map((o,i)=>o?(
                <span key={i} className="font-mono text-[0.68rem] px-1.5 py-0.5 rounded"
                      style={{background:'var(--surface2)',border:'1px solid var(--border)',color:'var(--text-dim)'}}>
                  {o.toFixed(2)}
                </span>
              ):null)}
            </div>
          </div>
          <div className="flex flex-col items-center gap-1">
            <span className="text-2xl">{emoji(match.team_away)}</span>
            <span className="font-display font-semibold text-sm text-center">{match.team_away}</span>
          </div>
        </div>
        <div className="flex flex-col items-end gap-1.5 min-w-[110px]">
          {match.is_strong?(
            <span className="font-mono text-[0.62rem] uppercase px-2 py-0.5 rounded"
                  style={{background:'var(--accent-dim)',color:'var(--accent)',border:'1px solid var(--border-accent)'}}>
              🔥 Value Bet
            </span>
          ):match.has_value?(
            <span className="font-mono text-[0.62rem] uppercase px-2 py-0.5 rounded"
                  style={{background:'var(--accent-dim)',color:'var(--accent)',border:'1px solid var(--border-accent)'}}>
              Value Bet ↑
            </span>
          ):(
            <span className="font-mono text-[0.62rem] uppercase px-2 py-0.5 rounded"
                  style={{background:'var(--surface2)',color:'var(--text-muted)',border:'1px solid var(--border)'}}>
              Pas de value
            </span>
          )}
          {ev!=null?(
            <>
              <span className="font-display font-bold text-lg" style={{color:'var(--accent)'}}>+{ev}%</span>
              <span className="font-mono text-[0.6rem]" style={{color:'var(--text-muted)'}}>EV · {match.best_bookmaker}</span>
            </>
          ):(
            <span className="font-mono text-[0.65rem]" style={{color:'var(--text-muted)'}}>Clique pour analyser</span>
          )}
        </div>
      </div>
    </div>
  )
}
'@

# ══════════════════════════════════════════════════════════════════
# app/login/page.tsx
# ══════════════════════════════════════════════════════════════════
Set-Content "$base\app\login\page.tsx" @'
'use client'
import{useState}from 'react'
import{useRouter}from 'next/navigation'
import toast from 'react-hot-toast'
import{authLogin,authRegister,getMe,setToken}from '@/lib/api'
import{useUserStore}from '@/lib/store'

export default function LoginPage(){
  const router=useRouter()
  const setUser=useUserStore(s=>s.setUser)
  const[tab,setTab]=useState<'login'|'register'>('login')
  const[loading,setLoading]=useState(false)
  const[loginEmail,setLoginEmail]=useState('')
  const[loginPassword,setLoginPassword]=useState('')
  const[regName,setRegName]=useState('')
  const[regEmail,setRegEmail]=useState('')
  const[regPassword,setRegPassword]=useState('')

  const afterAuth=async(token:string)=>{
    setToken(token);const user=await getMe();setUser(user)
    toast.success(`Bienvenue ${user.full_name} ! 🎯`);router.push('/agenda')
  }

  const handleLogin=async()=>{
    if(!loginEmail||!loginPassword){toast.error('Remplis email et mot de passe');return}
    setLoading(true)
    try{const res=await authLogin(loginEmail,loginPassword);await afterAuth(res.access_token)}
    catch(e:any){toast.error(e.message)}finally{setLoading(false)}
  }

  const handleRegister=async()=>{
    if(!regName||!regEmail||!regPassword){toast.error('Remplis tous les champs');return}
    if(regPassword.length<8){toast.error('8 caractères minimum');return}
    setLoading(true)
    try{const res=await authRegister(regEmail,regPassword,regName);await afterAuth(res.access_token);toast.success('50 crédits offerts 🎉')}
    catch(e:any){toast.error(e.message)}finally{setLoading(false)}
  }

  const inp="w-full px-4 py-3 rounded-lg font-mono text-[0.85rem] outline-none transition-colors"
  const inpStyle={background:'var(--bg)',border:'1px solid var(--border)',color:'var(--text)'}

  return(
    <div className="min-h-screen flex items-center justify-center relative overflow-hidden">
      <div className="absolute inset-0" style={{background:'radial-gradient(ellipse 60% 50% at 30% 50%,rgba(0,210,220,0.07),transparent)'}}/>
      <div className="grid-bg absolute inset-0"/>
      <div className="relative z-10 w-full max-w-5xl mx-auto px-6 py-12 grid grid-cols-1 lg:grid-cols-2 gap-16 items-center">

        {/* Hero */}
        <div className="fade-up">
          <div className="flex items-center gap-2 mb-8">
            <span className="font-display font-extrabold text-2xl tracking-tight">
              Rock<span style={{color:'var(--accent)'}}>AI</span>
            </span>
            <span className="w-2 h-2 rounded-full pulse" style={{background:'var(--accent)',boxShadow:'0 0 8px var(--accent-glow)'}}/>
            <span className="font-mono text-[0.65rem] uppercase tracking-widest" style={{color:'var(--text-muted)'}}>Beta</span>
          </div>
          <h1 className="font-display font-extrabold text-5xl leading-none tracking-tighter mb-5">
            L&apos;edge<br/>des <em className="not-italic text-accent-glow">pros</em><br/>accessible<br/>à tous.
          </h1>
          <p className="text-[0.9rem] leading-relaxed mb-8 font-light" style={{color:'var(--text-dim)'}}>
            Détection de value bets en temps réel par méthode Pinnacle, analyse IA de chaque match, suivi de bankroll automatisé.
          </p>
          <div className="flex gap-3 mb-8">
            {[{val:'+18.4%',label:'ROI moyen'},{val:'63%',label:'Taux win'},{val:'35+',label:'Sports'}].map(({val,label})=>(
              <div key={label} className="flex flex-col px-4 py-2.5 rounded-lg"
                   style={{background:'var(--surface)',border:'1px solid var(--border)'}}>
                <span className="font-display font-bold text-lg" style={{color:'var(--accent)'}}>{val}</span>
                <span className="font-mono text-[0.6rem] uppercase tracking-wider" style={{color:'var(--text-muted)'}}>{label}</span>
              </div>
            ))}
          </div>
          <div className="flex flex-col gap-3">
            {[
              {icon:'🎯',text:'Value bets détectés via Pinnacle — méthode des pros'},
              {icon:'🤖',text:'Analyse IA : xG, forme récente & head-to-head'},
              {icon:'📊',text:'Gestion de bankroll automatique (critère de Kelly)'},
              {icon:'🔔',text:'Alertes retournement en temps réel (bientôt)'},
            ].map(({icon,text})=>(
              <div key={text} className="flex items-center gap-3 text-[0.83rem]" style={{color:'var(--text-dim)'}}>
                <div className="w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0"
                     style={{background:'var(--accent-dim)',border:'1px solid var(--border-accent)'}}>{icon}</div>
                {text}
              </div>
            ))}
          </div>
        </div>

        {/* Card */}
        <div className="fade-up rounded-2xl p-8 relative overflow-hidden"
             style={{background:'var(--surface)',border:'1px solid var(--border)',animationDelay:'0.1s'}}>
          <div className="absolute top-0 left-0 right-0 h-px"
               style={{background:'linear-gradient(90deg,transparent,var(--accent),transparent)'}}/>

          {/* Tabs */}
          <div className="flex p-1 rounded-xl mb-6" style={{background:'var(--bg)',border:'1px solid var(--border)'}}>
            {(['login','register']as const).map(t=>(
              <button key={t} onClick={()=>setTab(t)}
                className="flex-1 py-2 rounded-lg font-mono text-[0.72rem] uppercase tracking-wider transition-all"
                style={{background:tab===t?'var(--surface2)':'transparent',color:tab===t?'var(--text)':'var(--text-muted)',
                        border:tab===t?'1px solid var(--border)':'1px solid transparent'}}>
                {t==='login'?'Connexion':'Inscription'}
              </button>
            ))}
          </div>

          {tab==='login'&&(
            <div className="space-y-4">
              <div>
                <label className="block font-mono text-[0.65rem] uppercase tracking-widest mb-1.5" style={{color:'var(--text-dim)'}}>Email</label>
                <input type="email" value={loginEmail} onChange={e=>setLoginEmail(e.target.value)}
                  onKeyDown={e=>e.key==='Enter'&&handleLogin()} placeholder="vous@exemple.fr"
                  className={inp} style={inpStyle}
                  onFocus={e=>(e.target.style.borderColor='var(--accent)')}
                  onBlur={e=>(e.target.style.borderColor='var(--border)')}/>
              </div>
              <div>
                <label className="block font-mono text-[0.65rem] uppercase tracking-widest mb-1.5" style={{color:'var(--text-dim)'}}>Mot de passe</label>
                <input type="password" value={loginPassword} onChange={e=>setLoginPassword(e.target.value)}
                  onKeyDown={e=>e.key==='Enter'&&handleLogin()} placeholder="••••••••••"
                  className={inp} style={inpStyle}
                  onFocus={e=>(e.target.style.borderColor='var(--accent)')}
                  onBlur={e=>(e.target.style.borderColor='var(--border)')}/>
              </div>
              <button onClick={handleLogin} disabled={loading}
                className="w-full py-3 mt-2 rounded-xl font-display font-bold text-[0.9rem] transition-all disabled:opacity-50"
                style={{background:'var(--accent)',color:'#080c10'}}
                onMouseEnter={e=>{e.currentTarget.style.background='#00c5cc';e.currentTarget.style.boxShadow='0 0 25px var(--accent-glow)'}}
                onMouseLeave={e=>{e.currentTarget.style.background='var(--accent)';e.currentTarget.style.boxShadow='none'}}>
                {loading?'Connexion...':'Accéder à la plateforme →'}
              </button>
              <p className="text-center font-mono text-[0.7rem]" style={{color:'var(--text-muted)'}}>
                Pas encore de compte ?{' '}
                <button onClick={()=>setTab('register')} style={{color:'var(--accent)'}}>Créer un compte gratuit</button>
              </p>
            </div>
          )}

          {tab==='register'&&(
            <div className="space-y-4">
              {[
                {label:'Prénom & Nom',type:'text',val:regName,set:setRegName,ph:'Jean Dupont'},
                {label:'Email',type:'email',val:regEmail,set:setRegEmail,ph:'vous@exemple.fr'},
                {label:'Mot de passe',type:'password',val:regPassword,set:setRegPassword,ph:'8 caractères minimum'},
              ].map(({label,type,val,set,ph})=>(
                <div key={label}>
                  <label className="block font-mono text-[0.65rem] uppercase tracking-widest mb-1.5" style={{color:'var(--text-dim)'}}>{label}</label>
                  <input type={type} value={val} onChange={e=>set(e.target.value)}
                    onKeyDown={e=>e.key==='Enter'&&handleRegister()} placeholder={ph}
                    className={inp} style={inpStyle}
                    onFocus={e=>(e.target.style.borderColor='var(--accent)')}
                    onBlur={e=>(e.target.style.borderColor='var(--border)')}/>
                </div>
              ))}
              <button onClick={handleRegister} disabled={loading}
                className="w-full py-3 rounded-xl font-display font-bold text-[0.9rem] transition-all disabled:opacity-50"
                style={{background:'var(--accent)',color:'#080c10'}}
                onMouseEnter={e=>{e.currentTarget.style.background='#00c5cc';e.currentTarget.style.boxShadow='0 0 25px var(--accent-glow)'}}
                onMouseLeave={e=>{e.currentTarget.style.background='var(--accent)';e.currentTarget.style.boxShadow='none'}}>
                {loading?'Création...':'Créer mon compte gratuit →'}
              </button>
              <p className="text-center font-mono text-[0.62rem]" style={{color:'var(--text-muted)'}}>
                En créant un compte vous acceptez nos <span style={{color:'var(--accent)'}}>CGU</span>
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
'@

# ══════════════════════════════════════════════════════════════════
# app/agenda/page.tsx
# ══════════════════════════════════════════════════════════════════
Set-Content "$base\app\agenda\page.tsx" @'
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
'@

# ══════════════════════════════════════════════════════════════════
# app/match/[id]/page.tsx
# ══════════════════════════════════════════════════════════════════
Set-Content "src\app\match\[id]\page.tsx" @'
'use client'
import{useEffect,useState}from 'react'
import{useParams,useRouter}from 'next/navigation'
import toast from 'react-hot-toast'
import Navbar from '@/components/Navbar'
import{getMatch,Match,ValueBet}from '@/lib/api'
import{ArrowLeft,TrendingUp}from 'lucide-react'

export default function MatchPage(){
  const{id}=useParams<{id:string}>()
  const router=useRouter()
  const[match,setMatch]=useState<Match|null>(null)
  const[loading,setLoading]=useState(true)

  useEffect(()=>{getMatch(id).then(setMatch).catch(e=>toast.error(e.message)).finally(()=>setLoading(false))},[id])

  if(loading)return(<div className="min-h-screen"><Navbar/><div className="max-w-5xl mx-auto px-6 py-8 space-y-4">{[...Array(4)].map((_,i)=><div key={i} className="h-24 rounded-xl animate-pulse" style={{background:'var(--surface)'}}/>)}</div></div>)
  if(!match)return(<div className="min-h-screen"><Navbar/><div className="text-center py-20 font-mono" style={{color:'var(--text-muted)'}}>Match introuvable</div></div>)

  const time=new Date(match.commence_time).toLocaleTimeString('fr-FR',{hour:'2-digit',minute:'2-digit'})
  const dateStr=new Date(match.commence_time).toLocaleDateString('fr-FR',{weekday:'long',day:'numeric',month:'long'})

  return(
    <div className="min-h-screen">
      <Navbar/>
      <div className="max-w-5xl mx-auto px-6 py-8">
        <div className="flex items-center gap-4 mb-6">
          <button onClick={()=>router.back()}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg font-mono text-[0.68rem] uppercase tracking-wider transition-all"
            style={{background:'var(--surface)',border:'1px solid var(--border)',color:'var(--text-dim)'}}
            onMouseEnter={e=>e.currentTarget.style.color='var(--text)'}
            onMouseLeave={e=>e.currentTarget.style.color='var(--text-dim)'}>
            <ArrowLeft size={12}/> Agenda
          </button>
          <div>
            <h1 className="font-display font-extrabold text-2xl tracking-tight">{match.team_home} vs {match.team_away}</h1>
            <p className="font-mono text-[0.68rem]" style={{color:'var(--text-muted)'}}>{match.league} · {dateStr} · {time}</p>
          </div>
          {match.is_strong&&(
            <span className="ml-auto font-mono text-[0.7rem] px-3 py-1 rounded-full"
                  style={{background:'var(--accent-dim)',color:'var(--accent)',border:'1px solid var(--border-accent)'}}>
              🔥 Value Bet Détecté
            </span>
          )}
        </div>

        {/* Pinnacle odds */}
        <div className="rounded-2xl p-6 mb-6 relative overflow-hidden" style={{background:'var(--surface)',border:'1px solid var(--border)'}}>
          <div className="absolute inset-0" style={{background:'radial-gradient(ellipse 60% 80% at 50% 50%,rgba(0,210,220,0.04),transparent)'}}/>
          <div className="relative flex items-center justify-between">
            <div className="text-center"><div className="text-4xl mb-2">⚽</div><div className="font-display font-bold text-xl">{match.team_home}</div></div>
            <div className="text-center">
              <div className="font-mono text-[0.65rem] uppercase tracking-wider mb-2" style={{color:'var(--text-muted)'}}>Cotes Pinnacle (référence)</div>
              <div className="flex gap-3">
                {[{label:'1',val:match.odds_home},{label:'X',val:match.odds_draw},{label:'2',val:match.odds_away}].map(({label,val})=>val?(
                  <div key={label} className="flex flex-col items-center px-4 py-2 rounded-xl"
                       style={{background:'var(--surface2)',border:'1px solid var(--border)'}}>
                    <span className="font-display font-bold text-xl">{val.toFixed(2)}</span>
                    <span className="font-mono text-[0.58rem]" style={{color:'var(--text-muted)'}}>{label}</span>
                  </div>
                ):null)}
              </div>
              <div className="font-mono text-[0.6rem] mt-2" style={{color:'var(--text-muted)'}}>Coup d&apos;envoi · {time}</div>
            </div>
            <div className="text-center"><div className="text-4xl mb-2">⚽</div><div className="font-display font-bold text-xl">{match.team_away}</div></div>
          </div>
        </div>

        {/* Value bets table */}
        <div className="rounded-2xl overflow-hidden mb-6" style={{background:'var(--surface)',border:'1px solid var(--border)'}}>
          <div className="px-6 py-4 border-b" style={{borderColor:'var(--border)'}}>
            <div className="flex items-center gap-2">
              <TrendingUp size={16} style={{color:'var(--accent)'}}/>
              <span className="font-display font-bold">Value Bets — Méthode Pinnacle</span>
            </div>
            <p className="font-mono text-[0.65rem] mt-1" style={{color:'var(--text-muted)'}}>
              // {match.value_bets.length} opportunité(s) · EV = (cote bk ÷ fair odds Pinnacle) − 1
            </p>
          </div>
          {match.value_bets.length===0?(
            <div className="px-6 py-12 text-center">
              <p className="font-mono text-[0.8rem]" style={{color:'var(--text-muted)'}}>❌ Aucune value bet — marché efficient sur ce match</p>
            </div>
          ):(
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead><tr style={{borderBottom:'1px solid var(--border)'}}>
                  {['Pari','Bookmaker','Cote','Fair Odds','EV %','Kelly %','Mise/1000€'].map(h=>(
                    <th key={h} className="px-4 py-3 font-mono text-[0.6rem] uppercase tracking-wider text-left"
                        style={{color:'var(--text-muted)'}}>{h}</th>
                  ))}
                </tr></thead>
                <tbody>
                  {match.value_bets.map((vb,i)=>(
                    <tr key={i} style={{borderBottom:'1px solid var(--border)',background:i===0?'rgba(0,210,220,0.03)':''}}
                        onMouseEnter={e=>(e.currentTarget.style.background='var(--surface2)')}
                        onMouseLeave={e=>(e.currentTarget.style.background=i===0?'rgba(0,210,220,0.03)':'')}>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          <span className="font-display font-bold text-[0.85rem]">{vb.bet_label}</span>
                          {vb.is_strong&&<span className="font-mono text-[0.58rem] px-1.5 py-0.5 rounded"
                            style={{background:'var(--accent-dim)',color:'var(--accent)',border:'1px solid var(--border-accent)'}}>FORT</span>}
                        </div>
                      </td>
                      <td className="px-4 py-3 font-mono text-[0.75rem]" style={{color:'var(--text-dim)'}}>{vb.bookmaker}</td>
                      <td className="px-4 py-3 font-display font-bold text-lg">{vb.odds.toFixed(2)}</td>
                      <td className="px-4 py-3 font-mono text-[0.78rem]" style={{color:'var(--text-muted)'}}>{vb.fair_odds.toFixed(2)}</td>
                      <td className="px-4 py-3 font-display font-bold text-lg" style={{color:'var(--accent)'}}>+{vb.ev_pct}%</td>
                      <td className="px-4 py-3 font-mono text-[0.78rem]" style={{color:'var(--text-dim)'}}>{vb.kelly_pct}%</td>
                      <td className="px-4 py-3 font-display font-bold" style={{color:'var(--accent)'}}>{vb.stake_1000}€</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {match.value_bets.length>0&&(
          <div className="rounded-xl p-5" style={{background:'var(--accent-dim)',border:'1px solid var(--border-accent)'}}>
            <div className="font-mono text-[0.65rem] uppercase tracking-wider mb-1" style={{color:'var(--accent)'}}>📈 Projection long terme</div>
            <p className="font-display font-bold text-2xl mt-1" style={{color:'var(--accent)'}}>
              → +{Math.round(1000*(Math.pow(1+(match.value_bets[0].kelly_pct/100)*(match.value_bets[0].ev_pct/100),500)-1)).toLocaleString()}€ sur 500 paris
            </p>
          </div>
        )}
      </div>
    </div>
  )
}
'@

# ══════════════════════════════════════════════════════════════════
# app/stats/page.tsx
# ══════════════════════════════════════════════════════════════════
Set-Content "$base\app\stats\page.tsx" @'
'use client'
import{useEffect,useState}from 'react'
import{useRouter}from 'next/navigation'
import toast from 'react-hot-toast'
import Navbar from '@/components/Navbar'
import{getStats,getBets,Stats,Bet}from '@/lib/api'
import{useUserStore}from '@/lib/store'

export default function StatsPage(){
  const router=useRouter()
  const{loadUser}=useUserStore()
  const[stats,setStats]=useState<Stats|null>(null)
  const[bets,setBets]=useState<Bet[]>([])
  const[loading,setLoading]=useState(true)

  useEffect(()=>{
    loadUser().then(()=>{if(!useUserStore.getState().user)router.push('/login')})
    Promise.all([getStats(),getBets()]).then(([s,b])=>{setStats(s);setBets(b.bets)})
      .catch(e=>toast.error(e.message)).finally(()=>setLoading(false))
  },[])

  const kpis=[
    {label:'ROI Global',val:stats?`${stats.roi>=0?'+':''}${stats.roi}%`:'—',color:'var(--accent)'},
    {label:'Taux de réussite',val:stats?`${stats.win_rate}%`:'—',color:'#00b8ff'},
    {label:'Profit net',val:stats?`${stats.total_profit>=0?'+':''}${stats.total_profit}€`:'—',color:'var(--gold)'},
    {label:'Paris placés',val:stats?String(stats.total_bets):'—',color:'var(--text)'},
  ]

  return(
    <div className="min-h-screen">
      <Navbar/>
      <div className="max-w-5xl mx-auto px-6 py-8">
        <div className="mb-8">
          <h1 className="font-display font-extrabold text-3xl tracking-tight mb-1">Statistiques</h1>
          <p className="font-mono text-[0.72rem]" style={{color:'var(--text-muted)'}}>// Suivi de performance · méthode Pinnacle</p>
        </div>
        <div className="grid grid-cols-4 gap-4 mb-8">
          {kpis.map(({label,val,color})=>(
            <div key={label} className="rounded-xl p-5" style={{background:'var(--surface)',border:'1px solid var(--border)'}}>
              <div className="font-mono text-[0.62rem] uppercase tracking-wider mb-2" style={{color:'var(--text-muted)'}}>{label}</div>
              <div className="font-display font-extrabold text-3xl tracking-tight" style={{color}}>{val}</div>
            </div>
          ))}
        </div>
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
'@

# ══════════════════════════════════════════════════════════════════
# app/pricing/page.tsx
# ══════════════════════════════════════════════════════════════════
Set-Content "$base\app\pricing\page.tsx" @'
'use client'
import{useState}from 'react'
import toast from 'react-hot-toast'
import Navbar from '@/components/Navbar'
import{Check,X}from 'lucide-react'

const PLANS=[
  {name:'Starter',monthly:0,annual:0,credits:'50',isFree:true,features:[
    {text:'Agenda des matchs en temps réel',ok:true},{text:'Value bets (méthode Pinnacle)',ok:true},
    {text:'50 analyses IA par mois',ok:true},{text:'Suivi de 5 paris max',ok:true},
    {text:'xG & statistiques avancées',ok:false},{text:'Alertes retournement live',ok:false},
    {text:'Historique illimité',ok:false},{text:'Export CSV',ok:false}]},
  {name:'Pro',monthly:19.90,annual:15.90,credits:'500',featured:true,features:[
    {text:'Tout le plan Starter',ok:true},{text:'500 analyses IA par mois',ok:true},
    {text:'xG pré-match & stats avancées',ok:true},{text:'Forme récente + H2H complet',ok:true},
    {text:'Suivi de paris illimité',ok:true},{text:'Historique complet exportable',ok:true},
    {text:'Alertes retournement (bientôt)',ok:true},{text:'Support prioritaire',ok:true}]},
  {name:'Elite',monthly:49.90,annual:39.90,credits:'∞',features:[
    {text:'Tout le plan Pro',ok:true},{text:'Crédits illimités',ok:true},
    {text:'Scanner 24h/24 multi-sports',ok:true},{text:'Alertes retournement live',ok:true},
    {text:'TrapScore live (bientôt)',ok:true},{text:'API privée (webhook)',ok:true},
    {text:'Accès bêta fonctionnalités',ok:true},{text:'Support Discord dédié',ok:true}]},
]

export default function PricingPage(){
  const[annual,setAnnual]=useState(false)
  return(
    <div className="min-h-screen">
      <Navbar/>
      <div className="text-center px-6 pt-12 pb-10">
        <div className="font-mono text-[0.68rem] uppercase tracking-widest mb-3" style={{color:'var(--accent)'}}>💎 Plans & Crédits</div>
        <h1 className="font-display font-extrabold text-4xl tracking-tight mb-2">
          Choisissez votre <em className="not-italic text-accent-glow">edge</em>
        </h1>
        <p className="font-mono text-[0.78rem]" style={{color:'var(--text-muted)'}}>// 1 crédit = 1 analyse · renouvellement mensuel</p>
        <div className="flex items-center justify-center gap-3 mt-6">
          <span className="font-mono text-[0.72rem] uppercase" style={{color:annual?'var(--text-muted)':'var(--text)'}}>Mensuel</span>
          <button onClick={()=>setAnnual(!annual)} className="w-10 h-5 rounded-full relative transition-colors"
            style={{background:annual?'var(--accent-dim)':'var(--surface2)',border:`1px solid ${annual?'var(--border-accent)':'var(--border)'}`}}>
            <span className="absolute top-0.5 w-4 h-4 rounded-full transition-all"
                  style={{background:annual?'var(--accent)':'var(--text-muted)',left:annual?'20px':'2px'}}/>
          </button>
          <span className="font-mono text-[0.72rem] uppercase" style={{color:annual?'var(--text)':'var(--text-muted)'}}>Annuel</span>
          <span className="font-mono text-[0.6rem] px-1.5 py-0.5 rounded" style={{background:'var(--gold-dim)',color:'var(--gold)',border:'1px solid rgba(255,215,0,0.2)'}}>-20%</span>
        </div>
      </div>
      <div className="max-w-5xl mx-auto px-6 pb-16 grid grid-cols-3 gap-5">
        {PLANS.map(plan=>(
          <div key={plan.name} className="rounded-2xl p-6 flex flex-col relative overflow-hidden transition-all"
               style={{background:(plan as any).featured?'linear-gradient(135deg,var(--surface),rgba(0,212,220,0.04))':'var(--surface)',
                 border:`1px solid ${(plan as any).featured?'var(--border-accent)':'var(--border)'}`}}>
            {(plan as any).featured&&<div className="absolute top-0 left-0 right-0 h-px" style={{background:'linear-gradient(90deg,transparent,var(--accent),transparent)'}}/>}
            {(plan as any).featured&&<div className="absolute top-4 right-4 font-mono text-[0.58rem] uppercase px-2 py-0.5 rounded"
              style={{background:'var(--accent-dim)',color:'var(--accent)',border:'1px solid var(--border-accent)'}}>⭐ Populaire</div>}
            <div className="font-mono text-[0.72rem] uppercase tracking-wider mb-3" style={{color:'var(--text-dim)'}}>{plan.name}</div>
            {plan.isFree?(
              <div className="font-display font-extrabold text-3xl tracking-tight mb-1" style={{color:'var(--text-dim)'}}>0€</div>
            ):(
              <div className="font-display font-extrabold text-4xl tracking-tighter mb-1">
                <sup className="text-xl font-semibold">€</sup>{annual?plan.annual:plan.monthly}
              </div>
            )}
            <div className="font-mono text-[0.62rem] uppercase tracking-wide mb-4" style={{color:'var(--text-muted)'}}>
              {plan.isFree?'Pour toujours gratuit':annual?'par mois · facturé annuellement':'par mois · facturé mensuellement'}
            </div>
            <div className="flex items-center gap-2 px-4 py-2.5 rounded-xl mb-5" style={{background:'var(--surface2)',border:'1px solid var(--border)'}}>
              <span className="font-display font-bold text-xl" style={{color:'var(--accent)'}}>{plan.credits}</span>
              <span className="font-mono text-[0.62rem] uppercase" style={{color:'var(--text-muted)'}}>crédits / mois</span>
            </div>
            <ul className="flex-1 space-y-2.5 mb-6">
              {plan.features.map(({text,ok})=>(
                <li key={text} className="flex items-start gap-2 text-[0.8rem]" style={{color:ok?'var(--text-dim)':'var(--text-muted)'}}>
                  {ok?<Check size={13} className="mt-0.5 flex-shrink-0" style={{color:'var(--accent)'}}/>
                     :<X size={13} className="mt-0.5 flex-shrink-0" style={{color:'var(--text-muted)'}}/>}
                  {text}
                </li>
              ))}
            </ul>
            <button onClick={()=>plan.isFree?toast('Plan actuel 🎯'):toast('Stripe bientôt disponible ! 📩',{duration:4000})}
              className="w-full py-3 rounded-xl font-display font-bold text-[0.88rem] transition-all"
              style={(plan as any).featured?{background:'var(--accent)',color:'#080c10'}:{background:'transparent',color:'var(--text-dim)',border:'1px solid var(--border)'}}>
              {plan.isFree?'Plan actuel':`Passer au ${plan.name} →`}
            </button>
          </div>
        ))}
      </div>
    </div>
  )
}
'@

# ══════════════════════════════════════════════════════════════════
# .env.local + tailwind.config.ts
# ══════════════════════════════════════════════════════════════════
Set-Content ".env.local" "NEXT_PUBLIC_API_URL=http://localhost:8000"

Set-Content "tailwind.config.ts" @'
import type { Config } from 'tailwindcss'
const config: Config = {
  content: ['./src/**/*.{js,ts,jsx,tsx,mdx}'],
  theme: { extend: {
    fontFamily: { display:['Syne','sans-serif'], mono:['DM Mono','monospace'], sans:['DM Sans','sans-serif'] },
    colors: { accent:'#00d4dc' },
  }},
  plugins: [],
}
export default config
'@

Write-Host ""
Write-Host "✅ Tous les fichiers créés !" -ForegroundColor Green
Write-Host ""
Write-Host "Lance maintenant :" -ForegroundColor Cyan
Write-Host "  npm run dev" -ForegroundColor Yellow
Write-Host ""
Write-Host "Puis ouvre : http://localhost:3000" -ForegroundColor Cyan
