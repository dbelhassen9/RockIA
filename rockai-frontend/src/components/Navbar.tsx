'use client'
import { useEffect } from 'react'
import Link from 'next/link'
import { usePathname, useRouter } from 'next/navigation'
import { useUserStore } from '@/lib/store'
import { getToken } from '@/lib/api'
import { Gem, LogOut } from 'lucide-react'

export default function Navbar() {
  const pathname = usePathname()
  const router = useRouter()
  const { user, logout, loadUser } = useUserStore()

  useEffect(() => {
    if (!user && getToken()) {
      loadUser()
    }
  }, [])

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
