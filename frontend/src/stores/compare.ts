import { defineStore } from 'pinia'
import api from '../api'

let timer: any = null

export const useCompareStore = defineStore('compare', {
  state: () => ({
    contracts: [] as string[],
    a: '',
    b: '',
    aFile: null as File | null,
    bFile: null as File | null,
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
      this.progress = Math.min(this.progress + 2.5, 92)
      this.stage = this.progress < 22 ? 0 : this.progress < 48 ? 1 : this.progress < 74 ? 2 : 3
    },
    async run() {
      if (this.loading) return
      const hasA = !!this.aFile || !!this.a
      const hasB = !!this.bFile || !!this.b
      if (!hasA || !hasB) {
        this.error = '请分别为 A、B 选择合同或上传文件'
        return
      }
      if (!this.aFile && !this.bFile && this.a === this.b) {
        this.error = 'A 和 B 不能是同一份合同'
        return
      }
      this.loading = true
      this.result = null
      this.error = ''
      this.progress = 0
      this.stage = 0
      timer = setInterval(() => this._tick(), 260)
      try {
        const fd = new FormData()
        if (this.aFile) fd.append('a_file', this.aFile)
        else fd.append('a_name', this.a)
        if (this.bFile) fd.append('b_file', this.bFile)
        else fd.append('b_name', this.b)
        const { data } = await api.post('/compare_upload', fd)
        this.progress = 100
        this.stage = 4
        this.result = data
      } catch (e: any) {
        this.error = e.response?.data?.detail || '对比失败'
      } finally {
        if (timer) clearInterval(timer)
        timer = null
        this.loading = false
      }
    },
    reset() {
      this.result = null
      this.error = ''
      this.progress = 0
      this.stage = 0
    },
  },
})
