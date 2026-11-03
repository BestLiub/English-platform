import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'home', component: () => import('@/views/HomeView.vue'), meta: { title: '今日' } },
    { path: '/study', name: 'study', component: () => import('@/views/StudyView.vue'), meta: { title: '背单词' } },
    { path: '/library', name: 'library', component: () => import('@/views/LibraryView.vue'), meta: { title: '精读' } },
    { path: '/read/:id', name: 'reader', component: () => import('@/views/ReaderView.vue'), meta: { title: '阅读' } },
    { path: '/stats', name: 'stats', component: () => import('@/views/StatsView.vue'), meta: { title: '统计' } },
    { path: '/settings', name: 'settings', component: () => import('@/views/SettingsView.vue'), meta: { title: '设置' } }
  ]
})

router.afterEach((to) => {
  const title = (to.meta.title as string) ?? ''
  document.title = title ? `${title} · English` : 'English'
})

export default router
