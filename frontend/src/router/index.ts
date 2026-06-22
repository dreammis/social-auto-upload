import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router';
import { useAuthStore } from '@/stores/auth.store';

const routes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/LoginView.vue'),
    meta: { requiresAuth: false },
  },
  {
    path: '/register',
    name: 'Register',
    component: () => import('@/views/RegisterView.vue'),
    meta: { requiresAuth: false },
  },
  // Authenticated layout wrapper
  {
    path: '/app',
    component: () => import('@/views/AppLayout.vue'),
    meta: { requiresAuth: true },
    children: [
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: () => import('@/views/DashboardView.vue'),
      },
      {
        path: 'accounts',
        name: 'Accounts',
        component: () => import('@/views/AccountsView.vue'),
      },
      {
        path: 'trends',
        name: 'Trends',
        component: () => import('@/views/TrendsView.vue'),
      },
    ],
  },
  {
    path: '/',
    redirect: '/app/dashboard',
  },
];

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
});

router.beforeEach(async (to, from, next) => {
  const authStore = useAuthStore();

  // Wait for store initialization
  if (!authStore.initialized) {
    await authStore.hydrate();
  }

  const requiresAuth = to.meta.requiresAuth as boolean;
  const isAuthenticated = authStore.isAuthenticated;

  // Route requires auth but user not authenticated
  if (requiresAuth && !isAuthenticated) {
    return next('/login');
  }

  // User is authenticated but trying to access login/register
  if ((to.name === 'Login' || to.name === 'Register') && isAuthenticated) {
    return next('/app/dashboard');
  }

  next();
});

export default router;
