import { defineConfig } from 'vitepress'

export default defineConfig({
  title: 'ai-fixer',
  description: '智能运维修复 Agent',
  base: '/ai-fixer/',
  ignoreDeadLinks: true,
  head: [
    ['link', { rel: 'icon', type: 'image/svg+xml', href: '/favicon.svg' }]
  ],

  themeConfig: {
    logo: '/favicon.svg',

    nav: [
      { text: '首页', link: '/' },
      { text: '指南', link: '/guide/' },
      { text: '部署', link: '/deployment/' },
      { text: '开发', link: '/development/' },
      { text: 'API', link: '/api/' },
      {
        text: '相关链接',
        items: [
          { text: 'GitHub', link: 'https://github.com/FLM210/ai-fixer' },
          { text: 'Docker Hub', link: 'https://hub.docker.com/r/hahtangtang/ai-fixer' },
        ],
      },
    ],

    sidebar: {
      '/guide/': [
        {
          text: '入门',
          items: [
            { text: '什么是 ai-fixer', link: '/guide/' },
            { text: '快速开始', link: '/guide/quick-start' },
            { text: '核心概念', link: '/guide/concepts' },
          ],
        },
        {
          text: '使用指南',
          items: [
            { text: '配置管理', link: '/guide/configuration' },
            { text: '环境上下文', link: '/guide/environment' },
            { text: '飞书集成', link: '/guide/feishu' },
            { text: '告警处理', link: '/guide/alerts' },
            { text: '插件系统', link: '/guide/plugins' },
            { text: '管理后台', link: '/guide/dashboard' },
          ],
        },
      ],
      '/deployment/': [
        {
          text: '部署',
          items: [
            { text: '部署概览', link: '/deployment/' },
            { text: '飞书机器人创建', link: '/deployment/feishu-bot' },
            { text: '基础设施准备', link: '/deployment/infrastructure' },
            { text: 'Docker 部署', link: '/deployment/docker' },
            { text: 'Kubernetes 部署', link: '/deployment/kubernetes' },
            { text: '生产环境加固', link: '/deployment/production' },
            { text: '常见问题排查', link: '/deployment/troubleshooting' },
          ],
        },
      ],
      '/development/': [
        {
          text: '开发',
          items: [
            { text: '开发指南', link: '/development/' },
            { text: '架构设计', link: '/development/architecture' },
            { text: '插件开发', link: '/development/plugin-dev' },
            { text: '测试', link: '/development/testing' },
            { text: '贡献指南', link: '/development/contributing' },
          ],
        },
      ],
      '/api/': [
        {
          text: 'API',
          items: [
            { text: 'API 概览', link: '/api/' },
            { text: 'REST API', link: '/api/rest' },
            { text: 'Webhook', link: '/api/webhook' },
          ],
        },
      ],
    },

    socialLinks: [
      { icon: 'github', link: 'https://github.com/FLM210/ai-fixer' },
    ],

    footer: {
      message: '基于 MIT 许可发布',
      copyright: 'Copyright © 2024-present ai-fixer',
    },

    search: {
      provider: 'local',
    },

    editLink: {
      pattern: 'https://github.com/FLM210/ai-fixer/edit/main/docs/:path',
      text: '在 GitHub 上编辑此页面',
    },

    lastUpdated: {
      text: '最后更新于',
    },
  },
})
