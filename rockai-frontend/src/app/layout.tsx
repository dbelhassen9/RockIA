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
