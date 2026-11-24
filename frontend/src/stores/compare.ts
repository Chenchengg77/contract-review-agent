import { defineStore } from 'pinia'
import api from '../api'

let timer: any = null

export const useCompareStore = defineStore('compare', {
  state: () => ({
    contracts: [] as string[],
    a: '',
    b: '',
    loading: false,
    progress: 0,
    stage: 0,
    result: null as any,
    error: '',
  }),
  actions: {
    async loadContracts() {
      if (this.contracts.length) return
      try {
        const { data } = await api.get('/contracts')
        this.contracts = data.contracts || []
        if (this.contracts.length > 1 && !this.a) {
          this.a = this.contracts[0]
          this.b = this.contracts[1]
        }
      } catch {
        /* ignore */
      }
    },
    _tick() {
      this.progress = Math.min(this.progress + 3, 92)
      this.stage = this.progress < 25 ? 0 : this.progress < 55 ? 1 : this.progress < 80 ? 2 : 3
    },
    async run() {
      if (this.loading) return
      if (!this.a || !this.b) {
        this.error = '请分别选择 A、B 两份合同'
        return
      }
      if (this.a === this.b) {
        this.error = 'A 和 B 不能是同一份合同'
        return
      }
      this.loading = true
      this.result = null
      this.error = ''
      this.progress = 0
      this.stage = 0
      timer = setInterval(() => this._tick(), 250)
      try {
        const { data } = await api.post('/compare', { a: this.a, b: this.b })
        this.progress = 100
        this.stage = 3
        this.result = data
      } catch (e: any) {
        this.error = e.response?.data?.detail || '对比失败'
      } finally {
        if (timer) clearInterval(timer)
        timer = null
        this.loading = false
      }
    },
  },
})
