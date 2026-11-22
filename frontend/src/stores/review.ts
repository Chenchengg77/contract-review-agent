import { defineStore } from 'pinia'
import api from '../api'

let timer: any = null

export const useReviewStore = defineStore('review', {
  state: () => ({
    contracts: [] as string[],
    selected: '',
    focus: '',
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
        if (this.contracts.length && !this.selected) this.selected = this.contracts[0]
      } catch {
        /* ignore */
      }
    },
    _tick() {
      this.progress = Math.min(this.progress + 3, 92)
      this.stage = this.progress < 25 ? 0 : this.progress < 55 ? 1 : this.progress < 80 ? 2 : 3
    },
    async start(file: File | null) {
      if (this.loading) return
      if (!file && !this.selected) {
        this.error = '请先选择或上传合同'
        return
      }
      this.loading = true
      this.result = null
      this.error = ''
      this.progress = 0
      this.stage = 0
      timer = setInterval(() => this._tick(), 250)
      try {
        let data: any
        if (file) {
          const fd = new FormData()
          fd.append('file', file)
          fd.append('focus', this.focus)
          data = (await api.post('/review', fd)).data
        } else {
          data = (await api.post('/review_sample', { name: this.selected, focus: this.focus })).data
        }
        this.progress = 100
        this.stage = 3
        this.result = data
      } catch (e: any) {
        this.error = e.response?.data?.detail || '审查失败'
      } finally {
        if (timer) clearInterval(timer)
        timer = null
        this.loading = false
      }
    },
  },
})
