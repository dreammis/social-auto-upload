import { createApp } from 'vue';
import { createPinia } from 'pinia';
import App from './App.vue';
import router from './router';
import { useAuthStore } from './stores/auth.store';

const pinia = createPinia();
const app = createApp(App);

app.use(pinia);
app.use(router);

// Hydrate auth state from localStorage BEFORE mount — prevents FOUC
const authStore = useAuthStore();
authStore.hydrate().then(() => {
  app.mount('#app');
});
