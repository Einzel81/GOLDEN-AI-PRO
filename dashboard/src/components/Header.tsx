// رأس الصفحة
import React from 'react';
import { Bell, User } from 'lucide-react';

export const Header: React.FC = () => {
  return (
    <header className="bg-gray-800 border-b border-gray-700 px-6 py-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <span className="text-sm text-gray-400">XAUUSD</span>
          <span className="text-lg font-bold text-green-400">1,910.50</span>
          <span className="text-sm text-green-400">+0.25%</span>
        </div>
        <div className="flex items-center space-x-4">
          <button className="p-2 text-gray-400 hover:text-white">
            <Bell className="w-5 h-5" />
          </button>
          <button className="p-2 text-gray-400 hover:text-white">
            <User className="w-5 h-5" />
          </button>
        </div>
      </div>
    </header>
  );
};
