const { aiChat } = require('../../utils/ai-service')

Page({
  data: {
    messages: [],
    inputText: '',
    isThinking: false,
    scrollTop: 0,
    autoFocus: false,
    quickQuestions: [
      '推荐热门商品',
      '如何下单购买',
      '物流跟踪查询',
      '售后服务政策',
      '商品使用说明'
    ]
  },

  onLoad() {
    this.initChat()
  },

  onShow() {
    this.setData({ autoFocus: true })
  },

  // 初始化聊天
  initChat() {
    const welcomeMessage = {
      id: Date.now(),
      role: 'assistant',
      content: '您好！我是XCAGI智能助手，可以帮您解答商品咨询、订单问题、物流跟踪等。请问有什么可以帮您的？',
      time: this.getCurrentTime()
    }
    
    this.setData({
      messages: [welcomeMessage]
    })
    
    this.scrollToBottom()
  },

  // 输入处理
  onInput(e) {
    this.setData({
      inputText: e.detail.value
    })
  },

  // 发送消息
  async sendMessage() {
    const text = this.data.inputText.trim()
    if (!text || this.data.isThinking) return

    // 添加用户消息
    const userMessage = {
      id: Date.now(),
      role: 'user',
      content: text,
      time: this.getCurrentTime()
    }

    this.setData({
      messages: [...this.data.messages, userMessage],
      inputText: '',
      isThinking: true
    })

    this.scrollToBottom()

    try {
      // 调用AI服务
      const response = await aiChat(text, this.data.messages.slice(-5))
      
      // 添加AI回复
      const aiMessage = {
        id: Date.now() + 1,
        role: 'assistant',
        content: response,
        time: this.getCurrentTime()
      }

      this.setData({
        messages: [...this.data.messages, aiMessage],
        isThinking: false
      })

      this.scrollToBottom()

    } catch (error) {
      console.error('AI回复失败', error)
      
      const errorMessage = {
        id: Date.now() + 1,
        role: 'assistant',
        content: '抱歉，我暂时无法回答这个问题。请稍后再试或联系客服。',
        time: this.getCurrentTime()
      }

      this.setData({
        messages: [...this.data.messages, errorMessage],
        isThinking: false
      })

      this.scrollToBottom()
    }
  },

  // 发送快捷问题
  sendQuickQuestion(e) {
    const question = e.currentTarget.dataset.question
    this.setData({ inputText: question })
    this.sendMessage()
  },

  // 复制消息
  copyMessage(e) {
    const content = e.currentTarget.dataset.content
    wx.setClipboardData({
      data: content,
      success: () => {
        wx.showToast({ title: '已复制', icon: 'success' })
      }
    })
  },

  // 重新生成消息
  regenerateMessage(e) {
    const messageId = e.currentTarget.dataset.id
    const messageIndex = this.data.messages.findIndex(msg => msg.id === messageId)
    
    if (messageIndex > 0) {
      const previousMessage = this.data.messages[messageIndex - 1]
      
      // 移除原来的AI回复
      const newMessages = this.data.messages.slice(0, messageIndex)
      this.setData({ messages: newMessages })
      
      // 重新发送问题
      this.setData({ inputText: previousMessage.content })
      this.sendMessage()
    }
  },

  // 清空聊天
  clearChat() {
    wx.showModal({
      title: '确认清空',
      content: '确定要清空聊天记录吗？',
      success: (res) => {
        if (res.confirm) {
          this.initChat()
        }
      }
    })
  },

  // 切换主题
  toggleTheme() {
    wx.showToast({
      title: '主题切换功能开发中',
      icon: 'none'
    })
  },

  // 滚动到底部
  scrollToBottom() {
    setTimeout(() => {
      this.setData({
        scrollTop: 99999
      })
    }, 100)
  },

  // 获取当前时间
  getCurrentTime() {
    const now = new Date()
    return `${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}`
  }
})