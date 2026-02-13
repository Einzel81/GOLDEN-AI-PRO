// القائمة الجانبية
import React from 'react';
import Link from 'next/link';
import { 
  Home, 
  TrendingUp, 
  Activity, 
  Settings, 
  BarChart3 
} from 'lucide-react';

export const Sidebar: React.FC = () => {
  const menuItems = [
    { icon: Home, label: 'Dashboard', href: '/' },
    { icon: TrendingUp, label: 'Trading', href: '/trading' },
    { icon: Activity, label: 'Analysis', href: '/analysis' },
    { icon: BarChart3, label: 'Performance', href: '/performance' },
    { icon: Settings, label: 'Settings', href: '/settings' },
  ];

  return (
    <aside className="w-64 bg-gray-800 border-r border-gray-700">
      <div className="p-6">
        <h1 className="text-2xl font-bold text-yellow-500">Golden-AI Pro</h1>
      </div>
      <nav className="mt-6">
        {menuItems.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className="flex items-center px-6 py-3 text-gray-300 hover:bg-gray-700 hover:text-white transition-colors"
          >
            <item.icon className="w-5 h-5 mr-3" />
            {item.label}
          </Link>
        ))}
      </nav>
    </aside>
  );
};
