// Vue Router 路由配置
import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    redirect: '/passenger',
  },
  {
    path: '/passenger',
    name: 'Passenger',
    component: () => import('@/views/PassengerView.vue'),
    meta: { title: '乘客端 - OptiBus' },
  },
  {
    path: '/driver',
    name: 'Driver',
    component: () => import('@/views/DriverView.vue'),
    meta: { title: '司机端 - OptiBus' },
  },
  {
    path: '/admin',
    name: 'Admin',
    component: () => import('@/views/AdminView.vue'),
    meta: { title: '管理员端 - OptiBus' },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
