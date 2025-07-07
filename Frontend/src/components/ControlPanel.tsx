import React, { useState } from 'react';
import { Play, Loader2, Globe } from 'lucide-react';

interface ControlPanelProps {
  onStartCrawl: (url: string, maxPages: number) => void;
  isLoading: boolean;
}

const ControlPanel: React.FC<ControlPanelProps> = ({ onStartCrawl, isLoading }) => {
  const [url, setUrl] = useState('');
  const [maxPages, setMaxPages] = useState(10);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (url.trim()) {
      onStartCrawl(url.trim(), maxPages);
    }
  };

  const isValidUrl = (string: string) => {
    try {
      new URL(string);
      return true;
    } catch (_) {
      return false;
    }
  };

  const canSubmit = url.trim() && isValidUrl(url.trim()) && !isLoading;

  return (
    <div className="bg-white rounded-xl shadow-lg border border-gray-200 p-6 sm:p-8">
      <div className="flex items-center space-x-3 mb-6">
        <div className="flex items-center justify-center w-12 h-12 bg-teal-100 rounded-lg">
          <Globe className="h-6 w-6 text-teal-600" />
        </div>
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Start a New Analysis</h2>
          <p className="text-gray-600">Enter your website URL to begin comprehensive SEO analysis</p>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div>
            <label htmlFor="url" className="block text-sm font-medium text-gray-700 mb-2">
              Website URL
            </label>
            <input
              id="url"
              type="url"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="https://example.com"
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-colors duration-200"
              required
            />
          </div>
          
          <div>
            <label htmlFor="maxPages" className="block text-sm font-medium text-gray-700 mb-2">
              Max Pages to Crawl
            </label>
            <input
              id="maxPages"
              type="number"
              min="1"
              max="100"
              value={maxPages}
              onChange={(e) => setMaxPages(parseInt(e.target.value) || 10)}
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-colors duration-200"
            />
          </div>
        </div>

        <div className="flex justify-center">
          <button
            type="submit"
            disabled={!canSubmit}
            className="flex items-center space-x-3 px-8 py-4 bg-teal-600 text-white rounded-lg hover:bg-teal-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200 transform hover:scale-105 disabled:hover:scale-100"
          >
            {isLoading ? (
              <Loader2 className="h-5 w-5 animate-spin" />
            ) : (
              <Play className="h-5 w-5" />
            )}
            <span className="font-medium">
              {isLoading ? 'Analyzing...' : 'Start Crawl & Analyze'}
            </span>
          </button>
        </div>
      </form>
    </div>
  );
};

export default ControlPanel;