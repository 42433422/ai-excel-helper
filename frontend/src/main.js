import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'

import './styles/css/base.css'
import './styles/css/components/sidebar.css'
import './styles/css/components/chat.css'
import './styles/css/components/tables.css'
import './styles/css/components/modals.css'
import './styles/css/components/ui-components.css'
import './styles/css/animations/transitions.css'
import './styles/css/animations/ui-effects.css'
import './styles/css/animations/pro-mode.css'
import './styles/css/animations/gpu-optimizations.css'
import './styles/font-awesome.css'

const app = createApp(App)
const pinia = createPinia()

app.use(pinia)

app.mount('#app')
