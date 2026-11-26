<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '../../api'
import { useUserStore } from '../../stores/user'

const store = useUserStore()
const router = useRouter()

onMounted(() => {
  if (!store.user) store.fetchMe()
})

const initial = computed(() => (store.user?.username || '?').slice(0, 1).toUpperCase())

// 修改密码
const pwdOpen = ref(false)
const pwdForm = ref({ old: '', next: '', confirm: '' })
const saving = ref(false)

function openPwd() {
  pwdForm.value = { old: '', next: '', confirm: '' }
  pwdOpen.value = true
}

async function submitPwd() {
  const { old, next, confirm } = pwdForm.value
  if (!old) {
    ElMessage.warning('请输入旧密码')
    return
  }
  if (next.length < 6) {
    ElMessage.warning('新密码至少 6 位')
    return
  }
  if (next !== confirm) {
    ElMessage.warning('两次输入的新密码不一致')
    return
  }
  saving.value = true
  try {
    await api.post('/auth/change-password', { old_password: old, new_password: next })
    ElMessage.success('密码已修改，请用新密码登录')
    pwdOpen.value = false
    store.logout()
    router.push('/login')
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '修改失败')
  } finally {
    saving.value = false
  }
}

async function logout() {
  try {
    await ElMessageBox.confirm('确定退出当前账号吗？', '退出登录', {
      confirmButtonText: '确认退出',
      cancelButtonText: '取消',
      type: 'warning',
    })
  } catch {
    return
  }
  store.logout()
  router.push('/login')
}

// 设置安全问题（用于找回密码）
const qOpen = ref(false)
const qForm = ref({ question: '', answer: '' })

function openQuestion() {
  qForm.value = { question: '', answer: '' }
  qOpen.value = true
}

async function saveQuestion() {
  if (!qForm.value.question.trim() || !qForm.value.answer.trim()) {
    ElMessage.warning('安全问题和答案都不能为空')
    return
  }
  saving.value = true
  try {
    await api.post('/auth/security-question', qForm.value)
    ElMessage.success('安全问题已保存，忘记密码时可自助重置')
    qOpen.value = false
    await store.fetchMe()
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '保存失败')
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div class="page">
    <div class="page-head">
      <div class="page-icon">
        <svg viewBox="0 0 24 24" fill="none" stroke="#14161a" stroke-width="1.3">
          <circle cx="12" cy="8.5" r="3.6" />
          <path d="M5 20c0-3.6 3.1-6 7-6s7 2.4 7 6" stroke-linecap="round" />
        </svg>
      </div>
      <div>
        <h1 class="page-title">账户</h1>
        <p class="page-sub">账号信息与登录状态</p>
      </div>
    </div>

    <div class="account-card">
      <div class="profile">
        <div class="avatar">{{ initial }}</div>
        <div class="profile-info">
          <div class="name">{{ store.user?.username || '-' }}</div>
          <div class="role">{{ store.isAdmin ? '管理员' : '普通用户' }}</div>
        </div>
      </div>

      <div class="rows">
        <div class="row">
          <span class="k">用户名</span>
          <span class="v">{{ store.user?.username || '-' }}</span>
        </div>
        <div class="row">
          <span class="k">角色</span>
          <span class="v">{{ store.isAdmin ? '管理员' : '普通用户' }}</span>
        </div>
        <div class="row">
          <span class="k">账号 ID</span>
          <span class="v">{{ store.user?.id ?? '-' }}</span>
        </div>
        <div class="row">
          <span class="k">安全问题</span>
          <span class="v">
            <template v-if="store.user?.has_security_question">已设置</template>
            <template v-else>
              <span class="unset">未设置</span>
              <button class="link" @click="openQuestion">去设置</button>
            </template>
          </span>
        </div>
      </div>

      <div class="actions">
        <button class="btn-ghost" @click="openPwd">修改密码</button>
        <button class="btn-danger" @click="logout">退出登录</button>
      </div>
    </div>

    <el-dialog v-model="pwdOpen" title="修改密码" width="420px">
      <el-form label-width="86px">
        <el-form-item label="旧密码">
          <el-input v-model="pwdForm.old" type="password" placeholder="请输入当前密码" show-password />
        </el-form-item>
        <el-form-item label="新密码">
          <el-input v-model="pwdForm.next" type="password" placeholder="至少 6 位" show-password />
        </el-form-item>
        <el-form-item label="确认新密码">
          <el-input v-model="pwdForm.confirm" type="password" placeholder="再输入一次" show-password />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="pwdOpen = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submitPwd">确认修改</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="qOpen" title="设置安全问题" width="420px">
      <p class="q-tip">设置后，忘记密码时可以在登录页自助重置（没有则只能联系管理员）。</p>
      <el-form label-width="86px">
        <el-form-item label="安全问题">
          <el-input v-model="qForm.question" placeholder="例：我的第一份合同编号" />
        </el-form-item>
        <el-form-item label="答案">
          <el-input v-model="qForm.answer" placeholder="请牢记，重置时要答" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="qOpen = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveQuestion">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.page-title {
  font-weight: 600;
  letter-spacing: 0.5px;
}
.page-icon {
  width: 44px;
  height: 44px;
  border-radius: 12px;
  background: #f8f7f3;
  border: 1px solid #ece7de;
  display: flex;
  align-items: center;
  justify-content: center;
}
.page-icon svg {
  width: 24px;
  height: 24px;
}
/* 卡片：统一规范 */
.account-card {
  max-width: 640px;
  border-radius: 8px;
  padding: 32px;
  background: #fff;
  border: 1px solid #f2f2f2;
  box-shadow: 0 4px 14px rgba(64, 158, 255, 0.06);
  transition: all 0.25s ease;
}
.profile {
  display: flex;
  align-items: center;
  gap: 16px;
  padding-bottom: 22px;
  border-bottom: 1px solid #eeeeee;
}
.avatar {
  width: 52px;
  height: 52px;
  border-radius: 50%;
  background: #f2f5fa;
  color: #3b5b8c;
  font-size: 19px;
  font-weight: 600;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.name {
  font-size: 17px;
  font-weight: 600;
  color: #14161a;
  letter-spacing: 0.5px;
}
.role {
  font-size: 11.5px;
  color: #94a3b8;
  margin-top: 4px;
}
/* 信息行 */
.rows {
  padding: 6px 0;
}
.row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 0;
  border-bottom: 1px solid #eeeeee;
  font-size: 13px;
}
.row:last-child {
  border-bottom: none;
}
.k {
  color: #94a3b8;
  letter-spacing: 0.4px;
}
.v {
  color: #14161a;
  font-weight: 500;
}
.unset {
  color: #b3b0a8;
  margin-right: 8px;
}
.link {
  background: none;
  border: none;
  color: #2563eb;
  font-size: 12px;
  cursor: pointer;
  padding: 0;
}
.link:hover {
  text-decoration: underline;
}
.q-tip {
  font-size: 12px;
  color: #94a3b8;
  line-height: 1.7;
  margin: 0 0 14px;
}
/* 操作 */
.actions {
  display: flex;
  gap: 12px;
  margin-top: 18px;
}
.btn-ghost {
  padding: 8px 18px;
  border-radius: 8px;
  border: 1px solid #d6e2f7;
  background: #fff;
  color: #2563eb;
  font-size: 12.5px;
  cursor: pointer;
  transition: all 0.2s;
}
.btn-ghost:hover {
  background: #f7fafd;
  border-color: #a9c5f0;
}
.btn-danger {
  padding: 8px 18px;
  border-radius: 8px;
  border: 1px solid #fbdedd;
  background: #fff6f5;
  color: #c0615a;
  font-size: 12.5px;
  cursor: pointer;
  transition: all 0.2s;
}
.btn-danger:hover {
  background: #fdeeee;
  border-color: #f5c7c4;
}
</style>
