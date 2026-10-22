import { createApp } from 'vue'

import App from './App.vue'
import { auth } from './auth'
import router from './router'
import './styles.css'

auth.bootstrap().finally(() => {
  createApp(App).use(router).mount('#app')
})
