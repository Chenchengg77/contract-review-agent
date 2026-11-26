<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '../../api'

const route = useRoute()
const router = useRouter()

const users = ref<any[]>([])
const loading = ref(false)
const selected = ref<any>(null)
const selection = ref<any[]>([])

const keyword = ref(String(route.query.q || ''))
const roleFilter = ref('')
const page = ref(1)
const pageSize = 10

const filtered = computed(() => {
  const kw = keyword.value.trim().toLowerCase()
  return users.value.filter((u) => {
    if (kw && !String(u.username).toLowerCase().includes(kw)) return false
    if (roleFilter.value && u.role !== roleFilter.value) return false
    return true
  })
})

const paged = computed(() => {
  const start = (page.value - 1) * pageSize
  return filtered.value.slice(start, start + pageSize)
})

const activeAdmins = computed(
  () => users.value.filter((u) => u.role === 'admin' && u.user_status !== 'disabled').length
)

function onFilter() {
  page.value = 1
}

async function load() {
  loading.value = true
  try {
    const { data } = await api.get('/admin/users')
    users.value = data.users || []
  } catch {
    ElMessage.error('加载失败')
  } finally {
    loading.value = false
  }
}

onMounted(load)

function onSelection(rows: any[]) {
  selection.value = rows
}

// 新增用户
const dialog = ref(false)
const form = ref({ username: '', password: '', role: 'user' })
const saving = ref(false)

function openCreate() {
  form.value = { username: '', password: '', role: 'user' }
  dialog.value = true
}

async function create() {
  if (!form.value.username || form.value.password.length < 6) {
    ElMessage.warning('用户名必填，密码至少 6 位')
    return
  }
  saving.value = true
  try {
    await api.post('/admin/users', form.value)
    ElMessage.success('已创建')
    dialog.value = false
    load()
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '创建失败')
  } finally {
    saving.value = false
  }
}

// 编辑
const editDialog = ref(false)
const editing = ref<any>(null)
const editForm = ref({ role: 'user', password: '' })

function openEdit(u: any) {
  editing.value = u
  editForm.value = { role: u.role, password: '' }
  editDialog.value = true
}

async function saveEdit() {
  if (!editing.value) return
  if (editForm.value.password && editForm.value.password.length < 6) {
    ElMessage.warning('新密码至少 6 位')
    return
  }
  saving.value = true
  try {
    await api.patch(`/admin/users/${editing.value.id}`, {
      role: editForm.value.role,
      password: editForm.value.password || undefined,
    })
    ElMessage.success('已更新')
    editDialog.value = false
    load()
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '更新失败')
  } finally {
    saving.value = false
  }
}

// 启用 / 禁用
async function toggle(u: any) {
  const next = u.user_status === 'disabled' ? 'active' : 'disabled'
  const verb = next === 'disabled' ? '禁用' : '启用'
  try {
    await ElMessageBox.confirm(`确定${verb}用户「${u.username}」？`, `确认${verb}`, { type: 'warning' })
  } catch {
    return
  }
  await applyStatus([u.id], next, verb)
}

async function batchStatus(next: 'active' | 'disabled') {
  if (!selection.value.length) return
  const verb = next === 'disabled' ? '禁用' : '启用'
  try {
    await ElMessageBox.confirm(
      `确定${verb}选中的 ${selection.value.length} 个账号？`,
      `批量${verb}`,
      { type: 'warning' }
    )
  } catch {
    return
  }
  await applyStatus(selection.value.map((u) => u.id), next, verb)
}

async function applyStatus(ids: number[], status: 'active' | 'disabled', verb: string) {
  let ok = 0
  let fail = 0
  for (const id of ids) {
    try {
      await api.patch(`/admin/users/${id}/status`, { status })
      ok += 1
    } catch {
      fail += 1
    }
  }
  if (ok) ElMessage.success(`已${verb} ${ok} 个账号`)
  if (fail) ElMessage.error(`${fail} 个账号操作失败（可能不能禁用自己或最后一个管理员）`)
  load()
}

async function del(u: any) {
  try {
    await ElMessageBox.confirm(
      `删除后该用户「${u.username}」的审查记录将一并移除，不可恢复。`,
      '确认删除',
      { type: 'warning', confirmButtonText: '确认删除', confirmButtonClass: 'el-button--danger' }
    )
  } catch {
    return
  }
  try {
    await api.delete('/admin/users/' + u.id)
    ElMessage.success('已删除')
    load()
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '删除失败')
  }
}

function gotoReviews(u: any) {
  router.push({ path: '/admin/reviews', query: { user: u.username } })
}

function initials(name: string) {
  return (name || '?').slice(0, 1).toUpperCase()
}

function fmt(ts: number) {
  if (!ts) return '—'
  const d = new Date(ts * 1000)
  const p = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`
}
</script>

<template>
  <div class="page">
    <div class="page-head">
      <div>
        <h1 class="page-title">用户管理</h1>
        <p class="page-sub">共 {{ users.length }} 个账号，可按用户名搜索、按角色筛选</p>
      </div>
    </div>

    <el-card shadow="never">
      <div class="toolbar">
        <el-input v-model="keyword" placeholder="搜索用户名" clearable style="width: 200px" @input="onFilter" />
        <el-select v-model="roleFilter" placeholder="全部角色" clearable style="width: 132px" @change="onFilter">
          <el-option label="管理员" value="admin" />
          <el-option label="普通用户" value="user" />
        </el-select>

        <transition name="fade">
          <div v-if="selection.length" class="batch-bar">
            <span>已选 <b>{{ selection.length }}</b> 项</span>
            <el-button size="small" @click="batchStatus('active')">批量启用</el-button>
            <el-button size="small" @click="batchStatus('disabled')">批量禁用</el-button>
          </div>
        </transition>

        <div class="spacer"></div>
        <el-button class="create-btn" @click="openCreate">+ 新增用户</el-button>
      </div>

      <el-table
        :data="paged"
        v-loading="loading"
        row-key="id"
        style="width: 100%"
        stripe
        highlight-current-row
        :max-height="560"
        :row-style="{ height: '52px' }"
        :header-cell-style="{ background: '#f8fafc', color: '#475569', fontWeight: '600', height: '44px' }"
        @selection-change="onSelection"
        @current-change="(row: any) => (selected = row)"
      >
        <el-table-column type="selection" width="46" align="center" />
        <el-table-column label="ID" width="64" align="right">
          <template #default="{ row }"><span class="uid">{{ row.id }}</span></template>
        </el-table-column>
        <el-table-column label="用户名" min-width="180">
          <template #default="{ row }">
            <div class="user-cell">
              <span class="avatar" :class="{ admin: row.role === 'admin' }">{{ initials(row.username) }}</span>
              <span class="uname">{{ row.username }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="角色" width="120">
          <template #default="{ row }">
            <span class="tag" :class="row.role">{{ row.role === 'admin' ? '管理员' : '普通用户' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="注册时间" width="160" align="center">
          <template #default="{ row }"><span class="muted">{{ fmt(row.created_at) }}</span></template>
        </el-table-column>
        <el-table-column label="审查次数" width="110" align="right">
          <template #default="{ row }">
            <button class="count-link" @click.stop="gotoReviews(row)">{{ row.review_count ?? 0 }}</button>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100" align="center">
          <template #default="{ row }">
            <span class="status" :class="row.user_status === 'disabled' ? 'off' : 'on'">
              {{ row.user_status === 'disabled' ? '禁用' : '启用' }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="190" align="center">
          <template #default="{ row }">
            <el-button link size="small" @click.stop="openEdit(row)">编辑</el-button>
            <el-button
              link
              size="small"
              :disabled="row.id === selected?.id ? false : false"
              @click.stop="toggle(row)"
            >
              {{ row.user_status === 'disabled' ? '启用' : '禁用' }}
            </el-button>
            <el-button
              link
              size="small"
              class="del-btn"
              :disabled="row.username === 'admin' || (row.role === 'admin' && activeAdmins <= 1)"
              @click.stop="del(row)"
            >
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pager">
        <span class="pager-info">共 {{ filtered.length }} 条</span>
        <el-pagination
          :current-page="page"
          :page-size="pageSize"
          :total="filtered.length"
          layout="prev, pager, next"
          background
          @current-change="(p: number) => (page = p)"
        />
      </div>
    </el-card>

    <!-- 新增 -->
    <el-dialog v-model="dialog" title="新增用户" width="440px">
      <el-form label-width="76px">
        <el-form-item label="用户名">
          <el-input v-model="form.username" placeholder="至少 2 位" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input v-model="form.password" type="password" placeholder="至少 6 位" show-password />
        </el-form-item>
        <el-form-item label="角色">
          <el-select v-model="form.role" style="width: 100%">
            <el-option label="普通用户" value="user" />
            <el-option label="管理员" value="admin" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialog = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="create">创建</el-button>
      </template>
    </el-dialog>

    <!-- 编辑 -->
    <el-dialog v-model="editDialog" :title="`编辑：${editing?.username || ''}`" width="440px">
      <el-form label-width="86px">
        <el-form-item label="角色">
          <el-select v-model="editForm.role" style="width: 100%">
            <el-option label="普通用户" value="user" />
            <el-option label="管理员" value="admin" />
          </el-select>
        </el-form-item>
        <el-form-item label="重置密码">
          <el-input v-model="editForm.password" type="password" placeholder="留空表示不修改" show-password />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editDialog = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveEdit">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.page-title {
  font-weight: 600;
  letter-spacing: 0.5px;
}
:deep(.el-card) {
  border-radius: 12px;
  border-color: #e2e8f0;
  box-shadow:
    0 1px 2px rgba(15, 23, 42, 0.04),
    0 8px 24px -20px rgba(15, 23, 42, 0.35);
}
.toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
  min-height: 32px;
}
.spacer {
  flex: 1;
}
.batch-bar {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 12.5px;
  color: #0f766e;
  background: #f0fdfa;
  border: 1px solid #99f6e4;
  border-radius: 8px;
  padding: 3px 8px 3px 12px;
}
.batch-bar b {
  font-weight: 700;
}
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
.create-btn {
  background: #14b8a6;
  border-color: #14b8a6;
  color: #fff;
}
.create-btn:hover {
  background: #0d9488;
  border-color: #0d9488;
  color: #fff;
}
/* 表格 */
:deep(.el-table) {
  --el-table-row-hover-bg-color: #f0fdfa;
  --el-table-current-row-bg-color: #ccfbf1;
  --el-table-border-color: #eef2f7;
  font-size: 13px;
}
:deep(.el-table th.el-table__cell) {
  background: #f8fafc !important;
  color: #475569;
  font-weight: 600;
  border-bottom: 1px solid #e2e8f0;
}
:deep(.el-table__body tr.el-table__row--striped td.el-table__cell) {
  background: #fbfcfd;
}
:deep(.el-table__body tr:hover > td.el-table__cell) {
  background: #f0fdfa !important;
}
:deep(.el-table__body tr.current-row > td.el-table__cell) {
  background: #ccfbf1 !important;
  box-shadow: inset 2px 0 0 #14b8a6;
}
:deep(.el-table td.el-table__cell) {
  padding: 0;
}
:deep(.el-table .cell) {
  line-height: 52px;
}
/* 单元格 */
.uid {
  color: #94a3b8;
  font-size: 12px;
}
.user-cell {
  display: flex;
  align-items: center;
  gap: 10px;
}
.avatar {
  width: 26px;
  height: 26px;
  border-radius: 50%;
  background: #e2e8f0;
  color: #475569;
  font-size: 11px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.avatar.admin {
  background: #fef3c7;
  color: #b45309;
}
.uname {
  color: #0f172a;
  font-weight: 500;
}
.tag {
  font-size: 11.5px;
  padding: 2px 9px;
  border-radius: 999px;
  font-weight: 500;
}
.tag.admin {
  color: #b45309;
  background: #fffbeb;
  border: 1px solid #fde68a;
}
.tag.user {
  color: #475569;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
}
.muted {
  color: #94a3b8;
  font-size: 12px;
}
.count-link {
  background: none;
  border: none;
  color: #0f172a;
  font-weight: 700;
  font-size: 13px;
  cursor: pointer;
  padding: 0;
  border-bottom: 1px dashed transparent;
}
.count-link:hover {
  color: #0d9488;
  border-bottom-color: #5eead4;
}
.status {
  font-size: 12px;
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-weight: 500;
}
.status::before {
  content: '';
  width: 6px;
  height: 6px;
  border-radius: 50%;
}
.status.on {
  color: #0f766e;
}
.status.on::before {
  background: #10b981;
}
.status.off {
  color: #64748b;
}
.status.off::before {
  background: #cbd5e1;
}
.del-btn:not(.is-disabled) {
  color: #ef4444;
}
.pager {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 16px;
}
.pager-info {
  font-size: 12px;
  color: #94a3b8;
}
</style>
