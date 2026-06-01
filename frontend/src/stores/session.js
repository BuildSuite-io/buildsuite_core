import { defineStore } from 'pinia'
import {
  clearAccessContextCache,
  getAccessContext,
  syncSessionFromCookie,
} from '@/utils/session'

export const useSessionStore = defineStore('session', {
  state: () => ({
    initialized: false,
    user: 'Guest',
    authenticated: false,
    access: {
      allowed: false,
      roles: [],
      reason: 'guest',
    },
    lastCheckedAt: null,
  }),

  actions: {
    hydrateFromRuntime() {
      const user = syncSessionFromCookie()
      this.user = user
      this.authenticated = user !== 'Guest'

      if (!this.authenticated) {
        this.access = {
          allowed: false,
          roles: [],
          reason: 'guest',
        }
        this.lastCheckedAt = Date.now()
      }

      return this.authenticated
    },

    async refreshAccess(options = {}) {
      this.hydrateFromRuntime()

      if (!this.authenticated) {
        return this.access
      }

      const context = await getAccessContext(options)
      this.user = context.user || this.user
      this.authenticated = this.user !== 'Guest'
      this.access = {
        allowed: Boolean(context.allowed),
        roles: Array.isArray(context.roles) ? context.roles : [],
        reason: context.reason || (context.allowed ? 'ok' : 'missing_role'),
      }
      this.lastCheckedAt = Date.now()
      return this.access
    },

    async bootstrapSession() {
      if (this.initialized) {
        return this.access
      }

      await this.refreshAccess({ force: false })
      this.initialized = true
      return this.access
    },

    async ensureAccess(options = {}) {
      if (!this.initialized) {
        await this.bootstrapSession()
        return this.access
      }

      return this.refreshAccess(options)
    },

    async recheckAccess() {
      clearAccessContextCache()
      return this.refreshAccess({ force: true })
    },

    resetSession() {
      clearAccessContextCache()
      this.initialized = false
      this.user = 'Guest'
      this.authenticated = false
      this.access = {
        allowed: false,
        roles: [],
        reason: 'guest',
      }
      this.lastCheckedAt = null
    },
  },
})
