import { defineStore } from 'pinia'
import api from '../api'

interface User {
  id: number
  username: string
  role: string
}

export const useUserStore = defineStore('user', {
  state: () => ({
    token: localStorage.getItem('token') || '',
    user: null as User | null,
  }),
  getters: {
    isAdmin: (s) => s.user?.role === 'admin',
    loggedIn: (s) => !!s.token,
  },
  actions: {
    async login(username: string, password: string) {
      const { data } = await api.post('/auth/login', { username, password })
      this.token = data.token
      this.user = data.user
      localStorage.setItem('token', data.token)
    },
    async register(username: string, password: string) {
      const { data } = await api.post('/auth/register', { username, password })
      this.token = data.token
      this.user = data.user
      localStorage.setItem('token', data.token)
    },
    async fetchMe() {
      if (!this.token) return
      try {
        const { data } = await api.get('/auth/me')
        this.user = data
      } catch {
        this.logout()
      }
    },
    logout() {
      this.token = ''
      this.user = null
      localStorage.removeItem('token')
    },
  },
})
