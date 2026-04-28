'use client'
import { useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import toast from 'react-hot-toast'
import { authLogin, getMe, setToken } from '@/lib/api'
import { useUserStore } from '@/lib/store'

export default function LoginPage() {
  const router  = useRouter()
  const setUser = useUserStore(s => s.setUser)
  const [email,    setEmail]    = useState('')
  const [password, setPassword] = useState('')
  const [loading,  setLoading]  = useState(false)

  const handleLogin = async () => {
    if (!email || !password) { toast.error('Remplis email et mot de passe'); return }
    setLoading(true)
    try {
      const res  = await authLogin(email, password)
      setToken(res.access_token)
      const user = await getMe()
      setUser(user)
      toast.success(`Bienvenue ${user.full_name} !`)
      router.push('/agenda')
    } catch (e: any) {
      toast.error(e.message)
    } finally {
      setLoading(false)
    }
  }

  const inp = "w-full px-4 py-3 rounded-xl font-mono text-[0.85rem] outline-none transition-colors"
  const inpStyle = { background: 'var(--bg)', border: '1px solid var(--border)', color: 'var(--text)' }

  return (
    <div className="min-h-screen flex items-center justify-center relative overflow-hidden">
      {/* Fond */}
      <div className="absolute inset-0" style={{ background: 'radial-gradient(ellipse 70% 60% at 50% 40%, rgba(0,210,220,0.08), transparent)' }} />
      <div className="grid-bg absolute inset-0" />

      <div className="relative z-10 w-full max-w-sm mx-auto px-6">
        {/* Logo */}
        <div className="text-center mb-8 fade-up">
          <div className="inline-flex items-center gap-2 mb-3">
            <span className="font-display font-extrabold text-3xl tracking-tight">
              Rock<span style={{ color: 'var(--accent)' }}>AI</span>
            </span>
            <span className="w-2 h-2 rounded-full pulse"
              style={{ background: 'var(--accent)', boxShadow: '0 0 10px var(--accent-glow)' }} />
          </div>
          <p className="font-mono text-[0.7rem] uppercase tracking-widest" style={{ color: 'var(--text-muted)' }}>
            Value betting · Méthode Pinnacle
          </p>
        </div>

        {/* Card */}
        <div className="fade-up rounded-2xl p-8 relative overflow-hidden"
          style={{ background: 'var(--surface)', border: '1px solid var(--border)', animationDelay: '0.05s' }}>
          <div className="absolute top-0 left-0 right-0 h-px"
            style={{ background: 'linear-gradient(90deg,transparent,var(--accent),transparent)' }} />

          <h2 className="font-display font-extrabold text-2xl tracking-tight mb-1">Connexion</h2>
          <p className="font-mono text-[0.7rem] mb-6" style={{ color: 'var(--text-muted)' }}>
            Accède à tes value bets en temps réel
          </p>

          <div className="space-y-4">
            <div>
              <label className="block font-mono text-[0.65rem] uppercase tracking-widest mb-1.5"
                style={{ color: 'var(--text-dim)' }}>Email</label>
              <input
                type="email" value={email} onChange={e => setEmail(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && handleLogin()}
                placeholder="vous@exemple.fr"
                className={inp} style={inpStyle}
                onFocus={e => (e.target.style.borderColor = 'var(--accent)')}
                onBlur={e  => (e.target.style.borderColor = 'var(--border)')}
              />
            </div>
            <div>
              <label className="block font-mono text-[0.65rem] uppercase tracking-widest mb-1.5"
                style={{ color: 'var(--text-dim)' }}>Mot de passe</label>
              <input
                type="password" value={password} onChange={e => setPassword(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && handleLogin()}
                placeholder="••••••••"
                className={inp} style={inpStyle}
                onFocus={e => (e.target.style.borderColor = 'var(--accent)')}
                onBlur={e  => (e.target.style.borderColor = 'var(--border)')}
              />
            </div>

            <button
              onClick={handleLogin} disabled={loading}
              className="w-full py-3.5 mt-2 rounded-xl font-display font-bold text-[0.9rem] transition-all disabled:opacity-50 active:scale-[0.98]"
              style={{ background: 'var(--accent)', color: '#080c10' }}
              onMouseEnter={e => { e.currentTarget.style.background = '#00c5cc'; e.currentTarget.style.boxShadow = '0 0 25px var(--accent-glow)' }}
              onMouseLeave={e => { e.currentTarget.style.background = 'var(--accent)'; e.currentTarget.style.boxShadow = 'none' }}>
              {loading ? 'Connexion...' : 'Se connecter →'}
            </button>
          </div>

          <p className="text-center font-mono text-[0.7rem] mt-5" style={{ color: 'var(--text-muted)' }}>
            Pas encore de compte ?{' '}
            <Link href="/register" style={{ color: 'var(--accent)' }}
              className="hover:opacity-80 transition-opacity">
              S&apos;inscrire gratuitement
            </Link>
          </p>
        </div>
      </div>
    </div>
  )
}
