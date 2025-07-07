import React, { useState, useEffect, useCallback } from 'react';
import Header from './components/Header';
import ControlPanel from './components/ControlPanel';
import ResultsSection from './components/ResultsSection';
import ReportModal from './components/ReportModal';
import Toast from './components/Toast';

// Define tipos para mejorar la legibilidad y la seguridad de tipos
interface SEOResult {
  // Asumiendo que SEOResult tiene algunas propiedades, añádelas aquí
  // Por ejemplo: url: string; title: string; description: string;
  [key: string]: any; // Marcador de posición si la estructura real es desconocida
}

interface ApiResponse<T> {
  data?: T;
  message?: string;
  // Añadir otras propiedades comunes de respuesta de API si las hay
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
  const [isConfirmationModalOpen, setIsConfirmationModalOpen] = useState(false); // Nuevo estado para el modal de confirmación
  const [results, setResults] = useState<SEOResult[]>([]); // Este estado permanecerá, aunque no se poblará con /results/
  const [generatedReport, setGeneratedReport] = useState<string>('');
  const [isLoading, setIsLoading] = useState(false); // Para la iniciación del rastreo
  const [isGeneratingReport, setIsGeneratingReport] = useState(false); // Para la generación del informe
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' } | null>(null);
  const [apiKey, setApiKey] = useState<string>(''); // Nuevo estado para almacenar la clave API
  const [apiKeyInput, setApiKeyInput] = useState<string>(''); // Estado para el input del modal de la clave API

  // Obtener la URL base de la API desde las variables de entorno de Vite
  // Asegúrate de que VITE_APP_API_URL esté configurada en Render para tu servicio de frontend
  // con la URL de tu backend (ej. https://technicalseoagent.onrender.com)
  //
  // ¡ACTUALIZADO AQUÍ CON LA URL PROPORCIONADA!
  const API_BASE_URL = import.meta.env.VITE_APP_API_URL || "https://technicalseoagentbackend.onrender.com";

  // Cargar la clave API desde localStorage al iniciar
  useEffect(() => {
    const storedApiKey = localStorage.getItem('openai_api_key');
    if (storedApiKey) {
      setApiKey(storedApiKey);
      setApiKeyInput(storedApiKey); // También inicializar el input del modal
    }
  }, []);

  // Función para guardar la clave API (ahora manejada directamente en App.tsx)
  const handleSaveApiKey = () => {
    setApiKey(apiKeyInput); // Usa el valor del input local
    localStorage.setItem('openai_api_key', apiKeyInput);
    showToast('Clave API guardada con éxito!', 'success');
    setIsApiKeyModalOpen(false); // Cierra el modal
  };

  // Función de ayuda para mostrar mensajes toast
  const showToast = useCallback((message: string, type: 'success' | 'error') => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 4000);
  }, []);

  // Función para generar el informe SEO
  const handleGenerateReport = useCallback(async () => {
    if (!apiKey) {
      showToast('Por favor, introduce tu clave API de OpenAI antes de generar el informe.', 'error');
      setIsApiKeyModalOpen(true); // Abrir el modal para que el usuario introduzca la clave
      return;
    }

    setIsGeneratingReport(true);
    try {
      // *** CAMBIO AQUÍ: Usar API_BASE_URL ***
      const response = await fetch(`${API_BASE_URL}/generate-report/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ api_key: apiKey }), // Enviar la clave API en el cuerpo de la solicitud
      });

      if (!response.ok) {
        // Intentar leer el mensaje de error del backend
        const errorData = await response.json().catch(() => ({ detail: 'Error desconocido' }));
        throw new Error(errorData.detail || 'Failed to generate report');
      }

      const data: { report: string } = await response.json();
      setGeneratedReport(data.report || '');
      setIsReportModalOpen(true);
      showToast('¡Informe SEO de IA generado con éxito!', 'success');

      // --- NUEVA FUNCIONALIDAD: Eliminar datos de la base de datos después de generar el informe ---
      try {
        // *** CAMBIO AQUÍ: Usar API_BASE_URL ***
        const clearResponse = await fetch(`${API_BASE_URL}/clear-database/`, {
          method: 'DELETE',
        });

        if (!clearResponse.ok) {
          const errorData = await clearResponse.json().catch(() => ({ detail: 'Error desconocido al limpiar la base de datos' }));
          console.error('Error al limpiar la base de datos:', errorData.detail);
          showToast(`Error al limpiar la base de datos: ${errorData.detail}`, 'error');
        } else {
          showToast('Datos de la base de datos eliminados con éxito.', 'success');
          setResults([]); // Limpiar los resultados en el frontend también
        }
      } catch (clearError: any) {
        console.error('Error de red al intentar limpiar la base de datos:', clearError);
        showToast(`Error de red al limpiar la base de datos: ${clearError.message}`, 'error');
      }
      // --- FIN DE LA NUEVA FUNCIONALIDAD ---

    } catch (error: any) {
      console.error('Error al generar el informe:', error);
      showToast(`Error al generar el informe: ${error.message || 'Por favor, compruebe su clave API e inténtelo de nuevo.'}`, 'error');
    } finally {
      setIsGeneratingReport(false);
    }
  }, [showToast, apiKey, API_BASE_URL]); // Añadir API_BASE_URL a las dependencias

  // Función para iniciar el rastreo y luego generar el informe
  const handleStartCrawl = useCallback(async (url: string, maxPages: number) => {
    if (!apiKey) { // Asegurarse de que la clave API esté presente antes de iniciar el rastreo
      showToast('Por favor, introduce tu clave API de OpenAI antes de iniciar el rastreo.', 'error');
      setIsApiKeyModalOpen(true);
      return;
    }

    setIsLoading(true);
    try {
      // *** CAMBIO AQUÍ: Usar API_BASE_URL ***
      const response = await fetch(`${API_BASE_URL}/crawl/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ url, max_pages: maxPages, api_key: apiKey }), // Enviar la clave API en el cuerpo de la solicitud de rastreo
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Error desconocido' }));
        throw new Error(errorData.detail || 'Failed to start crawl');
      }

      // El backend ahora espera a que el rastreo termine antes de responder,
      // así que podemos llamar a handleGenerateReport con confianza.
      console.log('Frontend: Rastreo completado según el backend. Iniciando generación de informe...'); // Nuevo log
      showToast('¡Rastreo completado! Ahora generando el informe SEO...', 'success');
      await handleGenerateReport();

    } catch (error: any) {
      console.error('Error al iniciar el rastreo:', error);
      showToast(`Error al iniciar el rastreo: ${error.message || 'Por favor, compruebe su URL e inténtelo de nuevo.'}`, 'error');
    } finally {
      setIsLoading(false);
    }
  }, [showToast, handleGenerateReport, apiKey, API_BASE_URL]); // Añadir API_BASE_URL a las dependencias

  // Función para borrar todos los datos de análisis
  const handleClearData = useCallback(async () => {
    try {
      // *** CAMBIO AQUÍ: Usar API_BASE_URL ***
      const response = await fetch(`${API_BASE_URL}/clear-database/`, {
        method: 'DELETE',
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Error desconocido' }));
        throw new Error(errorData.detail || 'Failed to clear database');
      }

      setResults([]); // Borrar el estado de resultados local
      showToast('¡Todos los datos borrados con éxito!', 'success');
    } catch (error: any) {
      console.error('Error al borrar los datos:', error);
      showToast(`Error al borrar los datos: ${error.message || 'Por favor, inténtelo de nuevo.'}`, 'error');
    } finally {
      setIsConfirmationModalOpen(false); // Cerrar el modal de confirmación
    }
  }, [showToast, API_BASE_URL]); // Añadir API_BASE_URL a las dependencias

  // Manejador para abrir el modal de confirmación de borrado de datos
  const openClearDataConfirmation = () => {
    setIsConfirmationModalOpen(true);
  };

  return (
    <div className="min-h-screen bg-gray-50 font-sans antialiased text-gray-800">
      <Header onOpenApiModal={() => setIsApiKeyModalOpen(true)} />

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="space-y-8">
          {/* Panel de Control para iniciar el rastreo */}
          <ControlPanel
            onStartCrawl={handleStartCrawl}
            isLoading={isLoading}
          />

          {/* Sección de Resultados (aparecerá vacía si no hay obtención directa de resultados, pero mantiene las acciones de informe/borrado) */}
          <ResultsSection
            results={results} // Esto probablemente estará vacío ya que no se llama a /results/
            onGenerateReport={handleGenerateReport} // Todavía disponible si es necesario, aunque ahora forma parte del flujo de rastreo
            onClearData={openClearDataConfirmation} // Usar el nuevo manejador de confirmación
            isGeneratingReport={isGeneratingReport}
          />
        </div>
      </main>

      {/* Modal de Clave API (ahora integrado directamente) */}
      {isApiKeyModalOpen && (
        <div className="fixed inset-0 bg-gray-600 bg-opacity-50 flex items-center justify-center z-50 font-sans">
          <div className="bg-white p-6 rounded-lg shadow-xl max-w-sm w-full transform transition-all duration-300 scale-100 opacity-100">
            <h3 className="text-xl font-semibold text-gray-900 mb-4">Introduce tu Clave API de OpenAI</h3>
            <p className="text-sm text-gray-700 mb-6">
              Necesitas una clave API de OpenAI para generar informes SEO. Puedes obtener una en tu panel de control de OpenAI.
            </p>
            <input
              type="password" // Usar tipo password para ocultar la clave
              className="w-full p-3 border border-gray-300 rounded-md mb-6 focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all duration-200"
              placeholder="sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
              value={apiKeyInput}
              onChange={(e) => setApiKeyInput(e.target.value)} // Actualiza el estado con el valor del input
            />
            <div className="flex justify-end space-x-3">
              {/* Botón para cancelar y cerrar el modal */}
              <button
                onClick={() => setIsApiKeyModalOpen(false)}
                className="px-4 py-2 bg-gray-200 text-gray-800 rounded-md hover:bg-gray-300 transition-colors duration-200"
              >
                Cancelar
              </button>
              {/* Botón para guardar la clave API */}
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

      {/* Modal de Visualización de Informe */}
      <ReportModal
        isOpen={isReportModalOpen}
        onClose={() => setIsReportModalOpen(false)}
        report={generatedReport}
      />

      {/* Modal de Confirmación Personalizado para borrar datos */}
      <ConfirmationModal
        isOpen={isConfirmationModalOpen}
        onClose={() => setIsConfirmationModalOpen(false)}
        onConfirm={handleClearData}
        title="Confirmar Eliminación de Datos"
        message="¿Está seguro de que desea eliminar todos los datos de análisis? Esta acción no se puede deshacer."
      />

      {/* Notificaciones Toast */}
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
