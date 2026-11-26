import { defineStore } from 'pinia'
import api from '../api'

let timer: any = null

export const useReviewStore = defineStore('review', {
  state: () => ({
    contracts: [] as string[],
    selected: '',
    focus: '',
    perspective: '',
    lastReview: null as { filename: string; created_at: number } | null,
    loading: false,
    progress: 0,
    stage: 0,
    result: null as any,
    error: '',
    // —— LangGraph 人工确认 ——
    graphMode: false,
    pending: null as any,
  }),
  actions: {
    async loadContracts() {
      if (this.contracts.length) return
      try {
        const [c, s] = await Promise.all([api.get('/contracts'), api.get('/me/stats')])
        this.contracts = c.data.contracts || []
        const recent = s.data?.recent || []
        if (recent.length) {
          this.lastReview = {
            filename: recent[0].filename,
            created_at: recent[0].created_at,
          }
        }
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
      // 人工确认模式：示例合同或上传文件都走 LangGraph 编排
      if (this.graphMode) {
        return this.startGraph(file)
      }
      this.loading = true
      this.result = null
      this.pending = null
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
          fd.append('perspective', this.perspective)
          data = (await api.post('/review', fd)).data
        } else {
          data = (
            await api.post('/review_sample', {
              name: this.selected,
              focus: this.focus,
              perspective: this.perspective,
            })
          ).data
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
    /** LangGraph 编排：无高风险直接出结果；有高风险则停在 pending 等确认 */
    async startGraph(file: File | null = null) {
      if (!file && !this.selected) {
        this.error = '请先选择或上传合同'
        return
      }
      this.loading = true
      this.result = null
      this.pending = null
      this.error = ''
      this.progress = 0
      this.stage = 0
      timer = setInterval(() => this._tick(), 250)
      try {
        const fd = new FormData()
        if (file) fd.append('file', file)
        else fd.append('name', this.selected)
        const { data } = await api.post('/review_graph', fd)
        this.progress = data.status === 'pending' ? 80 : 100
        this.stage = data.status === 'pending' ? 2 : 3
        if (data.status === 'pending') {
          this.pending = data
        } else {
          this.result = data
        }
      } catch (e: any) {
        this.error = e.response?.data?.detail || '审查失败'
      } finally {
        if (timer) clearInterval(timer)
        timer = null
        this.loading = false
      }
    },
    /** 人工确认后恢复执行（approve / 逐条修改） */
    async resumeGraph(action: 'approve' | 'edit' = 'approve', changes: Record<string, any> = {}) {
      if (!this.pending) return
      this.loading = true
      this.error = ''
      try {
        const { data } = await api.post('/review_graph/resume', {
          thread_id: this.pending.thread_id,
          action,
          changes,
        })
        this.result = data
        this.pending = null
        this.progress = 100
        this.stage = 4
      } catch (e: any) {
        this.error = e.response?.data?.detail || '确认失败'
      } finally {
        this.loading = false
      }
    },
  },
})
