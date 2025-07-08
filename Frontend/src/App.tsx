import React, { useState, useEffect, useCallback } from 'react';
import Header from './components/Header';
import ControlPanel from './components/ControlPanel';
import ResultsSection from './components/ResultsSection';
import ReportModal from './components/ReportModal';
import Toast from './components/Toast';

// Define tipos para mejorar la legibilidad y la seguridad de tipos
interface SEOResult {
  [key: string]: any;
}

interface ApiResponse<T> {
  data?: T;
  message?: string;
}

// Nuevo tipo para el estado de la tarea de rastreo
interface CrawlStatus {
  status: 'pending' | 'running' | 'completed' | 'failed';
  progress: number;
  total_pages: number;
  crawled_pages: number;
  url: string;
  error?: string;
}

// Componente de Modal de Confirmación Personalizado
const ConfirmationModal: React.FC<{
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  message: string;
  title: string;
}> = ({ isOpen, onClose, onConfirm, message, title }) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-gray-600 bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white p-6 rounded-lg shadow-xl max-w-sm w-full">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">{title}</h3>
        <p className="text-sm text-gray-700 mb-6">{message}</p>
        <div className="flex justify-end space-x-3">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-gray-200 text-gray-800 rounded-md hover:bg-gray-300 transition-colors duration-200"
          >
            Cancelar
          </button>
          <button
            onClick={onConfirm}
            className="px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 transition-colors duration-200"
          >
            Confirmar
          </button>
        </div>
      </div>
    </div>
  );
};


function App() {
  const [isApiKeyModalOpen, setIsApiKeyModalOpen] = useState(false);
  const [isReportModalOpen, setIsReportModalOpen] = useState(false);
  const [isConfirmationModalOpen, setIsConfirmationModalOpen] = useState(false);
  const [results, setResults] = useState<SEOResult[]>([]);
  const [generatedReport, setGeneratedReport] = useState<string>('');
  const [isLoading, setIsLoading] = useState(false); 
  const [isGeneratingReport, setIsGeneratingReport] = useState(false);
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' } | null>(null);
  const [apiKey, setApiKey] = useState<string>('');
  const [apiKeyInput, setApiKeyInput] = useState<string>('');
  const [currentCrawlStatus, setCurrentCrawlStatus] = useState<CrawlStatus | null>(null); // Nuevo estado para el progreso del rastreo

  const API_BASE_URL = import.meta.env.VITE_APP_API_URL || "https://technicalseoagentbackend.onrender.com";

  useEffect(() => {
    const storedApiKey = localStorage.getItem('openai_api_key');
    if (storedApiKey) {
      setApiKey(storedApiKey);
      setApiKeyInput(storedApiKey);
    }
  }, []);

  const handleSaveApiKey = () => {
    setApiKey(apiKeyInput);
    localStorage.setItem('openai_api_key', apiKeyInput);
    showToast('Clave API guardada con éxito!', 'success');
    setIsApiKeyModalOpen(false);
  };

  const showToast = useCallback((message: string, type: 'success' | 'error') => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 4000);
  }, []);

  const handleGenerateReport = useCallback(async () => {
    if (!apiKey) {
      showToast('Por favor, introduce tu clave API de OpenAI antes de generar el informe.', 'error');
      setIsApiKeyModalOpen(true);
      return;
    }

    setIsGeneratingReport(true);
    try {
      const response = await fetch(`${API_BASE_URL}/generate-report/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ openai_api_key: apiKey }), 
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Error desconocido' }));
        throw new Error(errorData.detail || 'Failed to generate report');
      }

      const data: { report: string } = await response.json();
      setGeneratedReport(data.report || '');
      setIsReportModalOpen(true);
      showToast('¡Informe SEO de IA generado con éxito!', 'success');

      try {
        const clearResponse = await fetch(`${API_BASE_URL}/clear-database/`, {
          method: 'DELETE',
        });

        if (!clearResponse.ok) {
          const errorData = await clearResponse.json().catch(() => ({ detail: 'Error desconocido al limpiar la base de datos' }));
          console.error('Error al limpiar la base de datos:', errorData.detail);
          showToast(`Error al limpiar la base de datos: ${errorData.detail}`, 'error');
        } else {
          showToast('Datos de la base de datos eliminados con éxito.', 'success');
          setResults([]);
        }
      } catch (clearError: any) {
        console.error('Error de red al intentar limpiar la base de datos:', clearError);
        showToast(`Error de red al limpiar la base de datos: ${clearError.message}`, 'error');
      }

    } catch (error: any) {
      console.error('Error al generar el informe:', error);
      showToast(`Error al generar el informe: ${error.message || 'Por favor, compruebe su clave API e inténtelo de nuevo.'}`, 'error');
    } finally {
      setIsGeneratingReport(false);
    }
  }, [showToast, apiKey, API_BASE_URL]);

  // Función para iniciar el rastreo y luego gestionar el polling
  const handleStartCrawl = useCallback(async (url: string, maxPages: number) => {
    if (!apiKey) {
      showToast('Por favor, introduce tu clave API de OpenAI antes de iniciar el rastreo.', 'error');
      setIsApiKeyModalOpen(true);
      return;
    }

    setIsLoading(true);
    setCurrentCrawlStatus(null); // Resetear el estado de rastreo anterior
    showToast('Iniciando rastreo...', 'success');

    try {
      const response = await fetch(`${API_BASE_URL}/crawl/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ url, max_pages: maxPages }), 
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Error desconocido' }));
        throw new Error(errorData.detail || 'Failed to start crawl');
      }

      const data: { message: string; task_id: string } = await response.json();
      const taskId = data.task_id;
      showToast(data.message, 'success');
      
      // Iniciar el polling para el estado del rastreo
      let pollInterval = setInterval(async () => {
        try {
          const statusResponse = await fetch(`${API_BASE_URL}/crawl-status/${taskId}`);
          if (!statusResponse.ok) {
            throw new Error('Failed to fetch crawl status');
          }
          const statusData: CrawlStatus = await statusResponse.json();
          setCurrentCrawlStatus(statusData); // Actualizar el estado en el UI

          if (statusData.status === 'completed') {
            clearInterval(pollInterval); // Detener el polling
            showToast('¡Rastreo completado! Ahora generando el informe SEO...', 'success');
            await handleGenerateReport(); // Llamar a la generación del informe
            setIsLoading(false);
          } else if (statusData.status === 'failed') {
            clearInterval(pollInterval); // Detener el polling
            showToast(`Rastreo fallido: ${statusData.error || 'Error desconocido'}`, 'error');
            setIsLoading(false);
          }
        } catch (pollError: any) {
          clearInterval(pollInterval); // Detener el polling en caso de error
          console.error('Error durante el polling del estado del rastreo:', pollError);
          showToast(`Error al verificar el estado del rastreo: ${pollError.message}`, 'error');
          setIsLoading(false);
        }
      }, 3000); // Poll cada 3 segundos

    } catch (error: any) {
      console.error('Error al iniciar el rastreo:', error);
      showToast(`Error al iniciar el rastreo: ${error.message || 'Por favor, compruebe su URL e inténtelo de nuevo.'}`, 'error');
      setIsLoading(false);
    }
  }, [showToast, handleGenerateReport, apiKey, API_BASE_URL]);

  const handleClearData = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/clear-database/`, {
        method: 'DELETE',
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Error desconocido' }));
        throw new Error(errorData.detail || 'Failed to clear database');
      }

      setResults([]);
      showToast('¡Todos los datos borrados con éxito!', 'success');
    } catch (error: any) {
      console.error('Error al borrar los datos:', error);
      showToast(`Error al borrar los datos: ${error.message || 'Por favor, inténtelo de nuevo.'}`, 'error');
    } finally {
      setIsConfirmationModalOpen(false);
    }
  }, [showToast, API_BASE_URL]);

  const openClearDataConfirmation = () => {
    setIsConfirmationModalOpen(true);
  };

  return (
    <div className="min-h-screen bg-gray-50 font-sans antialiased text-gray-800">
      <Header onOpenApiModal={() => setIsApiKeyModalOpen(true)} />

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="space-y-8">
          <ControlPanel
            onStartCrawl={handleStartCrawl}
            isLoading={isLoading}
          />

          {/* Mostrar el progreso del rastreo */}
          {currentCrawlStatus && (
            <div className="bg-white p-6 rounded-lg shadow-md text-center">
              <h3 className="text-lg font-semibold text-gray-900 mb-2">Estado del Rastreo: {currentCrawlStatus.status.toUpperCase()}</h3>
              {currentCrawlStatus.status === 'running' && (
                <p className="text-sm text-gray-700">
                  Páginas rastreadas: {currentCrawlStatus.crawled_pages} de {currentCrawlStatus.total_pages} ({currentCrawlStatus.progress}%)
                </p>
              )}
              {currentCrawlStatus.status === 'failed' && (
                <p className="text-sm text-red-600">Error: {currentCrawlStatus.error || 'Desconocido'}</p>
              )}
              {currentCrawlStatus.status === 'completed' && (
                <p className="text-sm text-green-600">Rastreo finalizado con éxito.</p>
              )}
            </div>
          )}

          <ResultsSection
            results={results}
            onGenerateReport={handleGenerateReport}
            onClearData={openClearDataConfirmation}
            isGeneratingReport={isGeneratingReport}
          />
        </div>
      </main>

      {isApiKeyModalOpen && (
        <div className="fixed inset-0 bg-gray-600 bg-opacity-50 flex items-center justify-center z-50 font-sans">
          <div className="bg-white p-6 rounded-lg shadow-xl max-w-sm w-full transform transition-all duration-300 scale-100 opacity-100">
            <h3 className="text-xl font-semibold text-gray-900 mb-4">Introduce tu Clave API de OpenAI</h3>
            <p className="text-sm text-gray-700 mb-6">
              Necesitas una clave API de OpenAI para generar informes SEO. Puedes obtener una en tu panel de control de OpenAI.
            </p>
            <input
              type="password"
              className="w-full p-3 border border-gray-300 rounded-md mb-6 focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all duration-200"
              placeholder="sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
              value={apiKeyInput}
              onChange={(e) => setApiKeyInput(e.target.value)}
            />
            <div className="flex justify-end space-x-3">
              <button
                onClick={() => setIsApiKeyModalOpen(false)}
                className="px-4 py-2 bg-gray-200 text-gray-800 rounded-md hover:bg-gray-300 transition-colors duration-200"
              >
                Cancelar
              </button>
              <button
                onClick={handleSaveApiKey}
                className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors duration-200"
              >
                Guardar Clave
              </button>
            </div>
          </div>
        </div>
      )}

      <ReportModal
        isOpen={isReportModalOpen}
        onClose={() => setIsReportModalOpen(false)}
        report={generatedReport}
      />

      <ConfirmationModal
        isOpen={isConfirmationModalOpen}
        onClose={() => setIsConfirmationModalOpen(false)}
        onConfirm={handleClearData}
        title="Confirmar Eliminación de Datos"
        message="¿Está seguro de que desea eliminar todos los datos de análisis? Esta acción no se puede deshacer."
      />

      {toast && (
        <Toast
          message={toast.message}
          type={toast.type}
          onClose={() => setToast(null)}
        />
      )}
    </div>
  );
}

export default App;