'use client'
import { useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import toast from 'react-hot-toast'
import { authRegister, getMe, setToken } from '@/lib/api'
import { useUserStore } from '@/lib/store'

export default function RegisterPage() {
  const router  = useRouter()
  const setUser = useUserStore(s => s.setUser)
  const [name,     setName]     = useState('')
  const [email,    setEmail]    = useState('')
  const [password, setPassword] = useState('')
  const [loading,  setLoading]  = useState(false)

  const handleRegister = async () => {
    if (!name || !email || !password) { toast.error('Remplis tous les champs'); return }
    if (password.length < 8) { toast.error('Mot de passe : 8 caractères minimum'); return }
    setLoading(true)
    try {
      const res  = await authRegister(email, password, name)
      setToken(res.access_token)
      const user = await getMe()
      setUser(user)
      toast.success('Compte créé ! 50 crédits offerts 🎉')
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

          <h2 className="font-display font-extrabold text-2xl tracking-tight mb-1">Créer un compte</h2>
          <p className="font-mono text-[0.7rem] mb-6" style={{ color: 'var(--text-muted)' }}>
            50 crédits offerts dès l&apos;inscription
          </p>

          {/* Badges avantages */}
          <div className="flex gap-2 mb-6 flex-wrap">
            {['🎯 Value bets', '🤖 Analyse IA', '📊 Kelly auto'].map(b => (
              <span key={b} className="font-mono text-[0.58rem] uppercase tracking-wider px-2 py-1 rounded-md"
                style={{ background: 'var(--accent-dim)', color: 'var(--accent)', border: '1px solid var(--border-accent)' }}>
                {b}
              </span>
            ))}
          </div>

          <div className="space-y-4">
            <div>
              <label className="block font-mono text-[0.65rem] uppercase tracking-widest mb-1.5"
                style={{ color: 'var(--text-dim)' }}>Prénom & Nom</label>
              <input
                type="text" value={name} onChange={e => setName(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && handleRegister()}
                placeholder="Jean Dupont"
                className={inp} style={inpStyle}
                onFocus={e => (e.target.style.borderColor = 'var(--accent)')}
                onBlur={e  => (e.target.style.borderColor = 'var(--border)')}
              />
            </div>
            <div>
              <label className="block font-mono text-[0.65rem] uppercase tracking-widest mb-1.5"
                style={{ color: 'var(--text-dim)' }}>Email</label>
              <input
                type="email" value={email} onChange={e => setEmail(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && handleRegister()}
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
                onKeyDown={e => e.key === 'Enter' && handleRegister()}
                placeholder="8 caractères minimum"
                className={inp} style={inpStyle}
                onFocus={e => (e.target.style.borderColor = 'var(--accent)')}
                onBlur={e  => (e.target.style.borderColor = 'var(--border)')}
              />
              {password.length > 0 && password.length < 8 && (
                <p className="font-mono text-[0.62rem] mt-1" style={{ color: 'var(--red)' }}>
                  {8 - password.length} caractère{8 - password.length > 1 ? 's' : ''} manquant{8 - password.length > 1 ? 's' : ''}
                </p>
              )}
            </div>

            <button
              onClick={handleRegister} disabled={loading}
              className="w-full py-3.5 mt-2 rounded-xl font-display font-bold text-[0.9rem] transition-all disabled:opacity-50 active:scale-[0.98]"
              style={{ background: 'var(--accent)', color: '#080c10' }}
              onMouseEnter={e => { e.currentTarget.style.background = '#00c5cc'; e.currentTarget.style.boxShadow = '0 0 25px var(--accent-glow)' }}
              onMouseLeave={e => { e.currentTarget.style.background = 'var(--accent)'; e.currentTarget.style.boxShadow = 'none' }}>
              {loading ? 'Création...' : 'Créer mon compte gratuit →'}
            </button>

            <p className="text-center font-mono text-[0.62rem]" style={{ color: 'var(--text-muted)' }}>
              En créant un compte tu acceptes nos{' '}
              <span style={{ color: 'var(--accent)' }}>CGU</span>
            </p>
          </div>

          <p className="text-center font-mono text-[0.7rem] mt-4 pt-4 border-t" style={{ color: 'var(--text-muted)', borderColor: 'var(--border)' }}>
            Déjà un compte ?{' '}
            <Link href="/login" style={{ color: 'var(--accent)' }}
              className="hover:opacity-80 transition-opacity">
              Se connecter
            </Link>
          </p>
        </div>
      </div>
    </div>
  )
}
