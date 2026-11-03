import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'home', component: () => import('@/views/HomeView.vue'), meta: { title: '今日' } },
    { path: '/study', name: 'study', component: () => import('@/views/StudyView.vue'), meta: { title: '背单词' } },
    { path: '/study/immersion', name: 'immersion', component: () => import('@/views/ImmersionView.vue'), meta: { title: '沉浸模式' } },
    { path: '/library', name: 'library', component: () => import('@/views/LibraryView.vue'), meta: { title: '精读' } },
    { path: '/read/:id', name: 'reader', component: () => import('@/views/ReaderView.vue'), meta: { title: '阅读' } },
    { path: '/profile', name: 'profile', component: () => import('@/views/ProfileView.vue'), meta: { title: '个人' } },
    // 旧的统计/设置入口已经合并进个人页，旧书签别落到空白路由
    { path: '/stats', redirect: '/profile' },
    { path: '/settings', redirect: '/profile' }
  ]
})

router.afterEach((to) => {
  const title = (to.meta.title as string) ?? ''
  document.title = title ? `${title} · English` : 'English'
})

export default router
