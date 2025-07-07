import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/crawl': 'http://127.0.0.1:8000',
      '/results': 'http://127.0.0.1:8000',
      '/generate-report': 'http://127.0.0.1:8000',
      '/clear-database': 'http://127.0.0.1:8000',
      // Para cualquier otra ruta de tu API que empiece con '/'
      // Puedes usar una regla más genérica si todas tus rutas de API están bajo un prefijo común
      // Por ejemplo, si todas tus APIs empiezan por '/api', sería:
      // '/api': 'http://127.0.0.1:8000'
      // Pero como tus endpoints están en la raíz, los listamos explícitamente o usamos una wildcard más cuidadosa.
      // Si quieres que TODAS las peticiones que no sean archivos estáticos vayan al backend:
      // '/': 'http://127.0.0.1:8000',  <-- ¡CUIDADO CON ESTO! Podría redirigir archivos del frontend.
                                      // Mejor listar los endpoints específicos o usar un prefijo.
    }
  },
  optimizeDeps: {
    exclude: ['lucide-react'],
  },
});
