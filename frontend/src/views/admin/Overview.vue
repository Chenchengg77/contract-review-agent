<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import api from '../../api'

const router = useRouter()
const stats = ref<any>(null)

onMounted(async () => {
  try {
    const { data } = await api.get('/admin/stats')
    stats.value = data
  } catch {
    /* ignore */
  }
})

const cards = computed(() => {
  const s = stats.value || {}
  return [
    { label: '用户数', value: s.users ?? 0, color: '#2563eb', to: '/admin/users' },
    { label: '审查记录', value: s.total ?? 0, color: '#7c3aed', to: '/admin/reviews' },
    { label: '高风险条款', value: s.high ?? 0, color: '#dc2626' },
    { label: '中风险条款', value: s.mid ?? 0, color: '#d97706' },
    { label: '低风险条款', value: s.low ?? 0, color: '#16a34a' },
  ]
})

const catMax = computed(() =>
  Math.max(1, ...((stats.value?.by_category || []).map((c: any) => c.count) as number[]))
)

const userMax = computed(() =>
  Math.max(1, ...((stats.value?.top_users || []).map((u: any) => u.count) as number[]))
)
</script>

<template>
  <div class="page">
    <div class="page-head">
      <div class="page-icon" style="background: #f5f3ff; color: #7c3aed">🛡️</div>
      <div>
        <h1 class="page-title">系统概览</h1>
        <p class="page-sub">用户与审查数据的整体情况（聚合统计，不含个人合同明细）</p>
      </div>
    </div>

    <div class="stats">
      <div
        v-for="s in cards"
        :key="s.label"
        class="stat"
        :class="{ clickable: s.to }"
        @click="s.to && router.push(s.to)"
      >
        <div class="num" :style="{ color: s.color }">{{ s.value }}</div>
        <div class="label">{{ s.label }}</div>
      </div>
    </div>

    <div class="two-col">
      <div class="card">
        <div class="card-title">合同类型分布</div>
        <div v-if="stats?.by_category?.length" class="cat-list">
          <div v-for="c in stats.by_category" :key="c.name" class="cat-row">
            <span class="cat-name">{{ c.name }}</span>
            <div class="cat-track">
              <div class="cat-fill" :style="{ width: (c.count / catMax) * 100 + '%' }"></div>
            </div>
            <span class="cat-count">{{ c.count }}</span>
          </div>
        </div>
        <div v-else class="empty-line">暂无审查记录</div>
      </div>

      <div class="card">
        <div class="card-title">活跃用户 Top 5</div>
        <div v-if="stats?.top_users?.length" class="cat-list">
          <div v-for="u in stats.top_users" :key="u.username" class="cat-row">
            <span class="cat-name">{{ u.username }}</span>
            <div class="cat-track">
              <div class="cat-fill user-fill" :style="{ width: (u.count / userMax) * 100 + '%' }"></div>
            </div>
            <span class="cat-count">{{ u.count }}</span>
          </div>
        </div>
        <div v-else class="empty-line">暂无数据</div>
      </div>
    </div>

    <div class="two-col">
      <div class="entry" @click="router.push('/admin/users')">
        <div class="entry-icon" style="background: #eff6ff; color: #2563eb">👥</div>
        <div>
          <div class="entry-title">用户管理</div>
          <div class="entry-desc">查看全部用户、偏好与审查次数，删除账号</div>
        </div>
      </div>
      <div class="entry" @click="router.push('/admin/reviews')">
        <div class="entry-icon" style="background: #f5f3ff; color: #7c3aed">📋</div>
        <div>
          <div class="entry-title">审查记录</div>
          <div class="entry-desc">查看所有人的审查记录，可删除单条</div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.stats {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 14px;
  margin-bottom: 16px;
}
.stat {
  background: #fff;
  border: 1px solid #e8edf5;
  border-radius: 16px;
  padding: 18px;
  text-align: center;
  transition: all 0.2s;
}
.stat.clickable {
  cursor: pointer;
}
.stat:hover {
  transform: translateY(-2px);
  box-shadow: 0 14px 30px -18px rgba(15, 23, 42, 0.25);
}
.num {
  font-size: 24px;
  font-weight: 800;
}
.label {
  font-size: 12px;
  color: #94a3b8;
  margin-top: 4px;
}
.two-col {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  margin-bottom: 16px;
}
.card {
  background: #fff;
  border: 1px solid #e8edf5;
  border-radius: 16px;
  padding: 22px;
}
.card-title {
  font-size: 14px;
  font-weight: 600;
  color: #0f172a;
  margin-bottom: 16px;
}
.cat-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.cat-row {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 12px;
}
.cat-name {
  width: 64px;
  color: #64748b;
  flex-shrink: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.cat-track {
  flex: 1;
  height: 8px;
  background: #f1f5f9;
  border-radius: 999px;
  overflow: hidden;
}
.cat-fill {
  height: 100%;
  background: linear-gradient(90deg, #60a5fa, #6366f1);
  border-radius: 999px;
}
.user-fill {
  background: linear-gradient(90deg, #c4b5fd, #8b5cf6);
}
.cat-count {
  width: 30px;
  text-align: right;
  color: #94a3b8;
}
.empty-line {
  font-size: 12px;
  color: #cbd5e1;
}
.entry {
  display: flex;
  align-items: center;
  gap: 16px;
  background: #fff;
  border: 1px solid #e8edf5;
  border-radius: 16px;
  padding: 20px;
  cursor: pointer;
  transition: all 0.2s;
}
.entry:hover {
  transform: translateY(-2px);
  border-color: #ddd6fe;
  box-shadow: 0 16px 32px -20px rgba(139, 92, 246, 0.4);
}
.entry-icon {
  width: 44px;
  height: 44px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  flex-shrink: 0;
}
.entry-title {
  font-size: 14px;
  font-weight: 600;
  color: #0f172a;
  margin-bottom: 3px;
}
.entry-desc {
  font-size: 12px;
  color: #94a3b8;
}
@media (max-width: 1000px) {
  .stats {
    grid-template-columns: repeat(2, 1fr);
  }
  .two-col {
    grid-template-columns: 1fr;
  }
}
</style>
