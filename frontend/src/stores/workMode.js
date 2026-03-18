import { defineStore } from 'pinia'
import { wechatApi } from '@/api/wechat'

export const useWorkModeStore = defineStore('workMode', {
  state: () => ({
    isActive: false,
    contacts: [],
    lastMessageSourceSize: null,
    pollingInterval: null,
    loading: false,
    error: null,
    isTaskAcquisition: false,
    currentOrder: null
  }),

  getters: {
    starredContacts: (state) => state.contacts.filter(c => c.starred),
    unreadContacts: (state) => state.contacts.filter(c => c.unreadCount > 0)
  },

  actions: {
    async startWorkMode() {
      this.isActive = true
      this.isTaskAcquisition = false
      this.currentOrder = null
      
      await this.loadContacts()
      await this.getMessageSourceSize()
      
      this.startPolling()
    },

    async stopWorkMode() {
      this.isActive = false
      this.isTaskAcquisition = false
      this.currentOrder = null
      
      this.stopPolling()
    },

    async loadContacts() {
      this.loading = true
      this.error = null
      
      try {
        const response = await wechatApi.getContacts({ starred: true })
        this.contacts = response.data || []
      } catch (error) {
        this.error = error.message
        console.error('Failed to load contacts:', error)
      } finally {
        this.loading = false
      }
    },

    async getMessageSourceSize() {
      try {
        const response = await fetch('/api/wechat_contacts/message_source_size')
        const data = await response.json()
        this.lastMessageSourceSize = data.size
      } catch (error) {
        console.error('Failed to get message source size:', error)
      }
    },

    async refreshMessagesCache() {
      try {
        await fetch('/api/wechat_contacts/refresh_messages_cache', { method: 'POST' })
        await this.getMessageSourceSize()
      } catch (error) {
        console.error('Failed to refresh messages cache:', error)
      }
    },

    async fetchWorkModeFeed() {
      try {
        const response = await fetch('/api/wechat_contacts/work_mode_feed')
        const data = await response.json()
        
        this.contacts = data.contacts || this.contacts
        
        if (data.newMessages && data.newMessages.length > 0) {
          this.processNewMessages(data.newMessages)
        }
        
        if (data.taskAcquisition) {
          this.handleTaskAcquisition(data.taskAcquisition)
        }
      } catch (error) {
        console.error('Failed to fetch work mode feed:', error)
      }
    },

    processNewMessages(messages) {
      messages.forEach(msg => {
        const contact = this.contacts.find(c => c.id === msg.contactId)
        if (contact) {
          contact.lastMessage = msg.content
          contact.lastMessageTime = msg.timestamp
          contact.unreadCount = (contact.unreadCount || 0) + 1
        }
      })
    },

    handleTaskAcquisition(taskData) {
      if (this.isTaskAcquisitionMessage(taskData.content)) {
        this.isTaskAcquisition = true
        this.currentOrder = taskData.order
      }
    },

    isTaskAcquisitionMessage(content) {
      const keywords = ['订单', 'order', '购买', 'buy', '需要', 'need']
      return keywords.some(keyword => content.toLowerCase().includes(keyword))
    },

    async sendMessage(contactId, message) {
      try {
        await wechatApi.sendMessage(contactId, message)
        
        const contact = this.contacts.find(c => c.id === contactId)
        if (contact) {
          contact.lastMessage = message
          contact.lastMessageTime = new Date().toISOString()
          contact.unreadCount = 0
        }
      } catch (error) {
        this.error = error.message
        console.error('Failed to send message:', error)
        throw error
      }
    },

    async sendOpeningMessage(contactId) {
      const openingMessages = [
        '您好，有什么可以帮助您的吗？',
        '您好，请问有什么需求？',
        '您好，欢迎咨询！'
      ]
      
      const message = openingMessages[Math.floor(Math.random() * openingMessages.length)]
      await this.sendMessage(contactId, message)
    },

    startPolling() {
      this.stopPolling()
      
      this.pollingInterval = setInterval(async () => {
        if (this.isActive) {
          await this.fetchWorkModeFeed()
        }
      }, 10000)
    },

    stopPolling() {
      if (this.pollingInterval) {
        clearInterval(this.pollingInterval)
        this.pollingInterval = null
      }
    },

    resetTaskAcquisition() {
      this.isTaskAcquisition = false
      this.currentOrder = null
    },

    async downloadOrder(orderId) {
      try {
        const response = await fetch(`/api/shipment/download/${orderId}`)
        const blob = await response.blob()
        
        const url = window.URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = `order_${orderId}.xlsx`
        document.body.appendChild(a)
        a.click()
        document.body.removeChild(a)
        window.URL.revokeObjectURL(url)
      } catch (error) {
        this.error = error.message
        console.error('Failed to download order:', error)
        throw error
      }
    }
  }
})
