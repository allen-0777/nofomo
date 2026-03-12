import React from 'react';
import { Link, Outlet } from 'react-router-dom';
import { LayoutDashboard, LineChart, List, Settings } from 'lucide-react';

const Layout = () => {
  return (
    <div className="min-h-screen bg-background text-foreground flex">
      {/* Sidebar */}
      <aside className="w-64 border-r bg-card p-4 hidden md:flex flex-col">
        <div className="mb-8 px-4">
          <h1 className="text-2xl font-bold bg-gradient-to-r from-blue-600 to-cyan-500 bg-clip-text text-transparent">
            NoFOMO
          </h1>
        </div>
        
        <nav className="space-y-2 flex-1">
          <NavLink to="/" icon={<LayoutDashboard size={20} />} label="Dashboard" />
          <NavLink to="/analysis" icon={<LineChart size={20} />} label="Analysis" />
          <NavLink to="/trades" icon={<List size={20} />} label="Trade Log" />
        </nav>

        <div className="mt-auto pt-4 border-t">
          <NavLink to="/settings" icon={<Settings size={20} />} label="Settings" />
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 overflow-auto">
        <header className="h-16 border-b flex items-center px-6 bg-card/50 backdrop-blur-sm sticky top-0 z-10">
          <h2 className="text-lg font-medium">Overview</h2>
        </header>
        <div className="p-6">
          <Outlet />
        </div>
      </main>
    </div>
  );
};

const NavLink = ({ to, icon, label }: { to: string; icon: React.ReactNode; label: string }) => (
  <Link
    to={to}
    className="flex items-center gap-3 px-4 py-2.5 rounded-lg text-muted-foreground hover:bg-secondary hover:text-foreground transition-colors"
  >
    {icon}
    <span>{label}</span>
  </Link>
);

export default Layout;
