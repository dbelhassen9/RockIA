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
