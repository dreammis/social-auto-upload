//引入createApp用于创建应用
import { createApp } from 'vue'
//引入APP根组件
import App from './App.vue'

const app = createApp(App)
import router from './router'

app.use(router)

app.mount('#app')