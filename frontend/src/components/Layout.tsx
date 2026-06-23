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
        <div className="p-4 border-b">
          <h1 className="text-lg font-bold">ai-fixer</h1>
          <p className="text-xs text-muted-foreground">智能运维修复 Agent</p>
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
        <div className="p-4 border-t text-xs text-muted-foreground">
          v0.1.0
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
