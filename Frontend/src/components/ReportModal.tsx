import React from 'react';
import { X, FileText, Download, Copy } from 'lucide-react';

interface ReportModalProps {
  isOpen: boolean;
  onClose: () => void;
  report: string;
}

const ReportModal: React.FC<ReportModalProps> = ({ isOpen, onClose, report }) => {
  const handleCopy = () => {
    navigator.clipboard.writeText(report);
  };

  const handleDownload = () => {
    const blob = new Blob([report], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `seo-report-${new Date().toISOString().split('T')[0]}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-xl shadow-xl max-w-4xl w-full max-h-[90vh] animate-in fade-in-0 duration-200">
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <div className="flex items-center space-x-3">
            <div className="flex items-center justify-center w-10 h-10 bg-blue-100 rounded-lg">
              <FileText className="h-5 w-5 text-blue-600" />
            </div>
            <div>
              <h2 className="text-xl font-semibold text-gray-900">AI SEO Report</h2>
              <p className="text-sm text-gray-500">Generated on {new Date().toLocaleString()}</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 transition-colors duration-200"
          >
            <X className="h-6 w-6" />
          </button>
        </div>
        
        <div className="p-6 max-h-[60vh] overflow-y-auto">
          <div className="bg-gray-50 rounded-lg p-4 font-mono text-sm whitespace-pre-wrap">
            {report}
          </div>
        </div>
        
        <div className="flex items-center justify-end space-x-3 p-6 border-t border-gray-200">
          <button
            onClick={handleCopy}
            className="flex items-center space-x-2 px-4 py-2 text-gray-600 hover:text-gray-800 transition-colors duration-200"
          >
            <Copy className="h-4 w-4" />
            <span>Copy to Clipboard</span>
          </button>
          <button
            onClick={handleDownload}
            className="flex items-center space-x-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors duration-200"
          >
            <Download className="h-4 w-4" />
            <span>Download Report</span>
          </button>
        </div>
      </div>
    </div>
  );
};

export default ReportModal;