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
