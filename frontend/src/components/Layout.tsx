import { NavLink, Outlet } from 'react-router-dom';
import { cn } from '@/lib/utils';
import { Toaster } from '@/components/ui/sonner';

const navItems = [
  { to: '/', label: '仪表盘', icon: '📊' },
  { to: '/incidents', label: 'Incidents', icon: '🔥' },
  { to: '/config', label: '配置管理', icon: '⚙️' },
  { to: '/plugins', label: '插件', icon: '🔌' },
  { to: '/environment', label: '环境上下文', icon: '🌍' },
  { to: '/knowledge', label: '知识库', icon: '📚' },
];

export default function Layout() {
  return (
    <div className="flex h-screen bg-background">
      {/* 侧边栏 */}
      <aside className="w-56 border-r bg-card flex flex-col">
        <div className="p-4 border-b flex items-center gap-3">
          <img src="/favicon.svg" alt="ai-fixer" className="w-10 h-10" />
          <div>
            <h1 className="text-lg font-bold">ai-fixer</h1>
            <p className="text-xs text-muted-foreground">智能运维修复 Agent</p>
          </div>
        </div>
        <nav className="flex-1 p-2 space-y-1">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === '/'}
              className={({ isActive }) =>
                cn(
                  'flex items-center gap-3 rounded-md px-3 py-2 text-sm transition-colors',
                  isActive
                    ? 'bg-primary text-primary-foreground'
                    : 'hover:bg-muted text-muted-foreground hover:text-foreground'
                )
              }
            >
              <span>{item.icon}</span>
              <span>{item.label}</span>
            </NavLink>
          ))}
        </nav>
        <div className="p-4 border-t flex justify-between items-center text-xs text-muted-foreground">
          <span>{import.meta.env.VITE_APP_VERSION || 'v0.1.0'}</span>
          <a
            href="https://github.com/FLM210/ai-fixer"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1 hover:text-foreground transition-colors"
            title="GitHub Repository"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M15 22v-4a4.8 4.8 0 0 0-1-3.5c3 0 6-2 6-5.5.08-1.25-.27-2.48-1-3.5.28-1.15.28-2.35 0-3.5 0 0-1 0-3 1.5-2.64-.5-5.36-.5-8 0C6 2 5 2 5 2c-.3 1.15-.3 2.35 0 3.5A5.403 5.403 0 0 0 4 9c0 3.5 3 5.5 6 5.5-.39.49-.68 1.05-.85 1.65-.17.6-.22 1.23-.15 1.85v4" />
              <path d="M9 18c-4.51 2-5-2-7-2" />
            </svg>
          </a>
        </div>
      </aside>

      {/* 主内容区 */}
      <main className="flex-1 overflow-auto">
        <div className="p-6">
          <Outlet />
        </div>
      </main>

      <Toaster />
    </div>
  );
}
