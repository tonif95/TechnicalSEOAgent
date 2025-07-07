import React from 'react';
import { Settings, Zap } from 'lucide-react';

interface HeaderProps {
  onOpenApiModal: () => void;
}

const Header: React.FC<HeaderProps> = ({ onOpenApiModal }) => {
  return (
    <header className="bg-white shadow-sm border-b border-gray-200">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          <div className="flex items-center space-x-3">
            <div className="flex items-center justify-center w-10 h-10 bg-blue-600 rounded-lg">
              <Zap className="h-6 w-6 text-white" />
            </div>
            <div>
              <h1 className="text-xl font-semibold text-gray-900">AI Technical SEO Expert</h1>
              <p className="text-sm text-gray-500">Analyze and optimize your website's SEO</p>
            </div>
          </div>
          
          <button
            onClick={onOpenApiModal}
            className="flex items-center space-x-2 px-4 py-2 text-gray-600 hover:text-gray-900 hover:bg-gray-50 rounded-lg transition-colors duration-200"
          >
            <Settings className="h-5 w-5" />
            <span className="hidden sm:inline">Settings</span>
          </button>
        </div>
      </div>
    </header>
  );
};

export default Header;