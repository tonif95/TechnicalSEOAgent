import React from 'react';
import { FileText, Trash2, Wand2, ExternalLink } from 'lucide-react';
import { SEOResult } from '../types';

interface ResultsSectionProps {
  results: SEOResult[];
  onGenerateReport: () => void;
  onClearData: () => void;
  isGeneratingReport: boolean;
}

const ResultsSection: React.FC<ResultsSectionProps> = ({
  results,
  onGenerateReport,
  onClearData,
  isGeneratingReport
}) => {
  if (results.length === 0) {
    return (
      <div className="bg-white rounded-xl shadow-lg border border-gray-200 p-12 text-center">
        <div className="flex justify-center mb-4">
          <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center">
            <FileText className="h-8 w-8 text-gray-400" />
          </div>
        </div>
        <h3 className="text-xl font-semibold text-gray-900 mb-2">No Analysis Data Yet</h3>
        <p className="text-gray-600 max-w-md mx-auto">
          Your analysis results will be displayed here after you start a crawl. 
          Enter a website URL above to begin your SEO analysis.
        </p>
      </div>
    );
  }

  const getStatusColor = (status: number) => {
    if (status >= 200 && status < 300) return 'text-green-600 bg-green-50';
    if (status >= 300 && status < 400) return 'text-yellow-600 bg-yellow-50';
    return 'text-red-600 bg-red-50';
  };

  return (
    <div className="bg-white rounded-xl shadow-lg border border-gray-200 overflow-hidden">
      <div className="p-6 border-b border-gray-200">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-xl font-semibold text-gray-900">Analysis Results</h3>
            <p className="text-gray-600">Found {results.length} pages to analyze</p>
          </div>
          
          <div className="flex items-center space-x-3">
            <button
              onClick={onGenerateReport}
              disabled={isGeneratingReport}
              className="flex items-center space-x-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors duration-200"
            >
              <Wand2 className="h-4 w-4" />
              <span>{isGeneratingReport ? 'Generating...' : 'Generate AI Report'}</span>
            </button>
            
            <button
              onClick={onClearData}
              className="flex items-center space-x-2 px-4 py-2 text-red-600 border border-red-200 rounded-lg hover:bg-red-50 transition-colors duration-200"
            >
              <Trash2 className="h-4 w-4" />
              <span>Clear Results</span>
            </button>
          </div>
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                URL
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Status
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Title
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Meta Description
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Headers
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Links
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Images
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Performance
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {results.map((result) => (
              <tr key={result.id} className="hover:bg-gray-50 transition-colors duration-200">
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="flex items-center space-x-2">
                    <a
                      href={result.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-blue-600 hover:text-blue-800 truncate max-w-xs"
                    >
                      {result.url}
                    </a>
                    <ExternalLink className="h-4 w-4 text-gray-400" />
                  </div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <span className={`px-2 py-1 text-xs font-medium rounded-full ${getStatusColor(result.status_code)}`}>
                    {result.status_code}
                  </span>
                </td>
                <td className="px-6 py-4">
                  <div className="max-w-xs truncate" title={result.title_tag}>
                    {result.title_tag || 'No title'}
                  </div>
                </td>
                <td className="px-6 py-4">
                  <div className="max-w-xs truncate" title={result.meta_description}>
                    {result.meta_description || 'No description'}
                  </div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="text-sm text-gray-900">
                    H1: {result.h1_count} | H2: {result.h2_count} | H3: {result.h3_count}
                  </div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="text-sm text-gray-900">
                    Int: {result.internal_links} | Ext: {result.external_links}
                  </div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="text-sm text-gray-900">
                    Total: {result.image_count}
                    {result.images_without_alt > 0 && (
                      <span className="text-red-600 ml-1">
                        ({result.images_without_alt} no alt)
                      </span>
                    )}
                  </div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="text-sm text-gray-900">
                    <div>Load: {result.load_time}s</div>
                    <div>Words: {result.word_count}</div>
                    <div className="flex items-center space-x-2 mt-1">
                      {result.mobile_friendly && (
                        <span className="text-green-600 text-xs">📱 Mobile</span>
                      )}
                      {result.has_schema && (
                        <span className="text-blue-600 text-xs">🔗 Schema</span>
                      )}
                    </div>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default ResultsSection;