//引入createRouter
import { createRouter, createWebHistory} from 'vue-router'
import { ref } from 'vue'
//创建路由
import Account from '@/components/AccountView.vue'
import Publish from '@/components/PublishView.vue'
import Website from '@/components/WebsiteView.vue'
import Data from '@/components/DataView.vue'
import VideoPublish from '@/components/VideoPublishView.vue'
import MultiPublish from '@/components/MultiPublishView.vue'
import MaterialLibrary from '@/components/MaterialLibraryView.vue'

// 存储动态添加的视频发布路由
const videoRoutes = ref([])

// 添加新的视频发布路由
function addVideoRoute() {
  const id = `video-${Date.now()}`;
  const newRoute = {
    id,
    path: `/video-publish/${id}`, // 修改路径为参数化形式
    name: `VideoPublish-${id}`,
    // 使用工厂函数返回组件，确保每个路由使用独立的组件实例
    component: () => import('@/components/VideoPublishView.vue'),
    props: route => ({ id: route.params.id }), // 将路由参数映射到组件props
    meta: { title: `发布视频 ${videoRoutes.value.length + 1}`, isVideoPublish: true }
  };
  videoRoutes.value.push(newRoute);
  
  // 动态添加路由
  if (!router.hasRoute(newRoute.name)) {
    router.addRoute(newRoute);
  }
  
  return newRoute;
}

// 删除视频发布路由
function removeVideoRoute(id) {
  const index = videoRoutes.value.findIndex(route => route.id === id)
  if (index !== -1) {
    const route = videoRoutes.value[index]
    // 从router中移除路由
    if (router.hasRoute(route.name)) {
      router.removeRoute(route.name)
    }
    // 从数组中移除路由
    videoRoutes.value.splice(index, 1)
  }
}

const router = createRouter({
	history: createWebHistory(),
	routes: [
		{
			path: '/',
			redirect: '/account'
		},
		{
			path: '/account',
			component: Account,
			meta: { title: '账号管理', icon: 'icon-account' }
		},
		{
			path: '/publish',
			component: Publish,
			meta: { title: '发布中心', icon: 'icon-publish' }
		},
		{
			path: '/multi-publish',
			component: MultiPublish,
			meta: { title: '多平台发布', icon: 'icon-multi-publish' }
		},
		{
			path: '/material-library',
			component: MaterialLibrary,
			meta: { title: '素材库', icon: 'icon-material' }
		},
		{
			path: '/website',
			component: Website,
			meta: { title: '网站', icon: 'icon-website' }
		},
		{
			path: '/data',
			component: Data,
			meta: { title: '数据', icon: 'icon-data' }
		},
	]
})
export default router

// 导出视频路由相关功能
export { videoRoutes, addVideoRoute, removeVideoRoute }