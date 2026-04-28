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
