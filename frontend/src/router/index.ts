import { createRouter, createWebHashHistory } from 'vue-router'
import { useUserStore } from '../stores/user'

const routes = [
  { path: '/login', component: () => import('../views/Login.vue') },

  // 用户端
  {
    path: '/',
    component: () => import('../layouts/UserLayout.vue'),
    children: [
      { path: '', redirect: '/home' },
      { path: 'home', component: () => import('../views/Home.vue') },
      { path: 'review', component: () => import('../views/Review.vue') },
      { path: 'chat', component: () => import('../views/Chat.vue') },
      { path: 'compare', component: () => import('../views/Compare.vue') },
      { path: 'templates', component: () => import('../views/Templates.vue') },
      { path: 'eval', component: () => import('../views/Eval.vue') },
      { path: 'about', component: () => import('../views/About.vue') },
      {
        path: 'me',
        component: () => import('../views/me/MeShell.vue'),
        children: [
          { path: '', redirect: '/me/overview' },
          { path: 'overview', component: () => import('../views/me/Overview.vue') },
          { path: 'reviews', component: () => import('../views/me/Reviews.vue') },
          { path: 'account', component: () => import('../views/me/Account.vue') },
        ],
      },
    ],
  },

  // 管理后台（独立布局）
  {
    path: '/admin',
    component: () => import('../layouts/AdminLayout.vue'),
    meta: { admin: true },
    children: [
      { path: '', redirect: '/admin/overview' },
      { path: 'overview', component: () => import('../views/admin/Overview.vue') },
      { path: 'users', component: () => import('../views/admin/Users.vue') },
      { path: 'reviews', component: () => import('../views/admin/Reviews.vue') },
      { path: 'ops', component: () => import('../views/admin/Ops.vue') },
    ],
  },
]

const router = createRouter({ history: createWebHashHistory(), routes })

router.beforeEach(async (to) => {
  const store = useUserStore()
  if (!store.token) {
    return to.path === '/login' ? true : '/login'
  }
  if (!store.user) await store.fetchMe()

  // 管理员只能待在管理端
  if (to.path === '/login') return store.isAdmin ? '/admin/overview' : '/home'
  if (store.isAdmin && !to.path.startsWith('/admin')) return '/admin/overview'

  // 普通用户不能进管理端
  if (to.meta.admin && !store.isAdmin) return '/home'
  return true
})

export default router
