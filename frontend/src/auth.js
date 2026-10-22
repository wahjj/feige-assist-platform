import { reactive } from 'vue'

export const auth = reactive({
  ready: false,
  authenticated: false,
  username: '',
  csrfToken: '',

  async bootstrap() {
    try {
      const response = await fetch('/api/auth/session', { credentials: 'include' })
      const payload = await response.json()
      this.authenticated = Boolean(payload.authenticated)
      this.username = payload.username || ''
      this.csrfToken = payload.csrf_token || ''
    } finally {
      this.ready = true
    }
  },

  setSession(payload) {
    this.ready = true
    this.authenticated = Boolean(payload.authenticated)
    this.username = payload.username || ''
    this.csrfToken = payload.csrf_token || ''
  },

  clear() {
    this.authenticated = false
    this.username = ''
    this.csrfToken = ''
  },
})
