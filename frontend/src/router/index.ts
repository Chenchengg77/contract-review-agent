import { createRouter, createWebHashHistory } from 'vue-router'
import { useUserStore } from '../stores/user'

const routes = [
  { path: '/login', component: () => import('../views/Login.vue') },
  { path: '/', redirect: '/home' },
  { path: '/home', component: () => import('../views/Home.vue') },
  { path: '/review', component: () => import('../views/Review.vue') },
  { path: '/chat', component: () => import('../views/Chat.vue') },
  { path: '/compare', component: () => import('../views/Compare.vue') },
  { path: '/templates', component: () => import('../views/Templates.vue') },
  { path: '/eval', component: () => import('../views/Eval.vue') },
  { path: '/admin', component: () => import('../views/Admin.vue'), meta: { admin: true } },
  { path: '/about', component: () => import('../views/About.vue') },
]

const router = createRouter({ history: createWebHashHistory(), routes })

router.beforeEach(async (to) => {
  const store = useUserStore()
  if (!store.token) {
    return to.path === '/login' ? true : '/login'
  }
  if (!store.user) await store.fetchMe()
  if (to.meta.admin && !store.isAdmin) return '/home'
  if (to.path === '/login') return '/home'
  return true
})

export default router
