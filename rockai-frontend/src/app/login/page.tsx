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
