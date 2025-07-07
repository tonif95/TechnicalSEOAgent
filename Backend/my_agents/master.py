import sys
import os
import contextlib
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, HttpUrl
import uvicorn
import asyncio
from urllib.parse import urlparse
from multiprocessing import Process, Queue
import time
import sqlite3
from fastapi.middleware.cors import CORSMiddleware

# Configuración de PYTHONPATH para asegurar que se puedan importar módulos locales
project_root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root_dir not in sys.path:
    sys.path.insert(0, project_root_dir)

# Importaciones de módulos de la aplicación
# Asegúrate de que estas rutas sean correctas en tu estructura de proyecto
from Backend.my_agents.crawler import setup_database, get_html_and_parse, analyze_html_content, save_to_database, DB_NAME as CRAWLER_DB_NAME
from Backend.my_agents.analyzer import _generate_report_in_process, load_analysis_results_from_db

# Lifespan Event Handler
@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Función de ciclo de vida de la aplicación FastAPI.
    Se ejecuta al iniciar y al cerrar la aplicación.
    """
    print("Iniciando la aplicación FastAPI...")
    try:
        setup_database()
        print(f"Base de datos {os.path.abspath(CRAWLER_DB_NAME)} verificada.") # Log de la ruta absoluta
    except Exception as e:
        print(f"ERROR: No se pudo inicializar la base de datos: {e}")
    yield
    print("Cerrando la aplicación FastAPI...")

# Instancia principal de FastAPI
app = FastAPI(
    title="SEO Crawler & Reporter API",
    description="API para rastrear sitios web, analizar SEO técnico y generar informes.",
    version="1.0.0",
    lifespan=lifespan
)
origins = [
    "http://localhost",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Modelo para la URL de rastreo
class CrawlRequest(BaseModel):
    url: HttpUrl
    max_pages: int = 5
    api_key: str

# Modelo para la solicitud de generación de informe con la clave API
class GenerateReportRequest(BaseModel):
    api_key: str

# Endpoint para iniciar el rastreo
@app.post("/crawl/", summary="Iniciar rastreo de un sitio web", response_description="Mensaje de inicio de rastreo")
async def start_crawl(request: CrawlRequest):
    """
    Inicia un proceso de rastreo y espera a que termine antes de responder.
    """
    target_url = str(request.url)
    max_pages = request.max_pages
    api_key = request.api_key

    if not target_url.startswith(("http://", "https://")):
        raise HTTPException(status_code=400, detail="La URL debe comenzar con 'http://' o 'https://'")
    
    if not api_key:
        raise HTTPException(status_code=400, detail="La clave API de OpenAI es requerida para iniciar el rastreo.")

    os.environ["OPENAI_API_KEY"] = api_key
    print(f"API - INFO: OPENAI_API_KEY establecida en el entorno del proceso principal para el rastreo.")

    print(f"API - Endpoint /crawl/ recibido para URL: {target_url}, max_pages: {max_pages}. Iniciando rastreo y **esperando su finalización**...")
    
    # Ejecutar el rastreo en un hilo separado y esperar su finalización
    # Esto asegura que el endpoint no responda hasta que run_crawl_process_sync haya terminado
    processed_pages_count = await asyncio.to_thread(run_crawl_process_sync, target_url, max_pages) 

    print(f"API - DEBUG: run_crawl_process_sync ha finalizado. Páginas procesadas y guardadas: {processed_pages_count}.")
    
    # Verificar el estado de la base de datos justo antes de responder
    conn = None
    try:
        conn = sqlite3.connect(CRAWLER_DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM crawled_pages")
        current_db_count = cursor.fetchone()[0]
        print(f"API - DEBUG: Filas en la base de datos ANTES de responder a /crawl/: {current_db_count}")
    except sqlite3.Error as e:
        print(f"API - ERROR: Error al verificar la base de datos antes de responder a /crawl/: {e}")
    finally:
        if conn:
            conn.close()

    print(f"API - Rastreo completado para {target_url}. El endpoint /crawl/ está **a punto de responder**.")
    return {"message": f"Rastreo completado para {target_url} con un máximo de {max_pages} páginas. Los resultados están listos para el informe."}

def run_crawl_process_sync(target_url: str, max_pages: int):
    """
    Lógica principal del rastreador de páginas web, diseñada para ser ejecutada sincrónicamente
    en un hilo separado por asyncio.to_thread.
    """
    print(f"CRAWLER - INFO: run_crawl_process_sync iniciado para {target_url} con límite de {max_pages} páginas.")
    processed_count = 0 # Contador para páginas realmente procesadas y guardadas
    urls_to_crawl = [target_url]
    processed_urls = set() # URLs que ya han sido puestas en cola o procesadas
    
    try:
        parsed_target_url = urlparse(target_url)
        base_domain = parsed_target_url.netloc

        while urls_to_crawl and processed_count < max_pages: # Cambiado a processed_count
            current_url = urls_to_crawl.pop(0)
            
            if current_url in processed_urls:
                print(f"CRAWLER - INFO: Saltando URL ya procesada: {current_url}")
                continue
            
            # Añadir la URL al conjunto de procesadas antes de intentar obtener el contenido
            # Esto evita que se procese la misma URL varias veces si se encuentra en diferentes enlaces
            processed_urls.add(current_url) 

            # Si ya hemos procesado y guardado suficientes páginas, salimos del bucle
            if processed_count >= max_pages: # Cambiado a processed_count
                print(f"CRAWLER - INFO: Límite de {max_pages} páginas con análisis guardado alcanzado. No se procesarán más.")
                break 

            print(f"CRAWLER - DEBUG: Procesando URL: {current_url}. Páginas guardadas hasta ahora: {processed_count}/{max_pages}. URLs restantes en cola: {len(urls_to_crawl)}")


            soup, original_html_content, prettified_html_content, found_links = \
                get_html_and_parse(current_url, base_domain) # Eliminado processed_urls y max_pages de aquí

            if soup:
                print(f"CRAWLER - DEBUG: HTML obtenido para {current_url}. Iniciando análisis SEO...")
                analysis_results = analyze_html_content(current_url, soup)
                
                if analysis_results:
                    print(f"CRAWLER - DEBUG: Análisis completado para {current_url}. Resultados: {len(analysis_results)} ítems. Guardando en DB...")
                    save_to_database(current_url, original_html_content, prettified_html_content, analysis_results)
                    processed_count += 1 # Incrementar solo si el análisis y guardado fueron exitosos
                    print(f"CRAWLER - INFO: Análisis y guardado en DB completado para: {current_url}")
                else:
                    print(f"CRAWLER - WARNING: 'analysis_results' es None para {current_url}. No se guardará en DB.")
            else:
                print(f"CRAWLER - WARNING: 'soup' es None para {current_url}. No se pudo obtener/parsear el HTML. Saltando análisis y guardado.")

            for link in found_links:
                # Solo añadir enlaces si no han sido procesados y si aún no hemos alcanzado el límite de páginas guardadas
                if link not in processed_urls and urlparse(link).netloc == base_domain:
                    if processed_count < max_pages: # Cambiado a processed_count
                        urls_to_crawl.append(link)
                    else:
                        print(f"CRAWLER - INFO: Límite de páginas con análisis guardado alcanzado al añadir nuevo enlace: {link}")
                        break

            time.sleep(1) # Pausa para evitar sobrecargar el servidor
            
        print(f"CRAWLER - INFO: Rastreo completado para {target_url}. Total de páginas con análisis guardado: {processed_count}. Resultados en la base de datos.")
        return processed_count # Devolver el contador de páginas procesadas
    except Exception as e:
        print(f"CRAWLER - ERROR: Un error inesperado ocurrió durante el rastreo: {e}")
        import traceback
        traceback.print_exc()
        return processed_count # Devolver el contador incluso si hay un error

# Endpoint para obtener todos los resultados de análisis (se mantiene aunque no se use en el frontend actual)
@app.get("/results/", summary="Obtener todos los resultados de análisis de la base de datos", response_description="Lista de resultados de análisis")
async def get_all_analysis_results():
    """
    Recupera y devuelve todos los resultados de análisis guardados en la base de datos.
    """
    try:
        print(f"API - DEBUG: Cargando resultados de la base de datos desde: {os.path.abspath(CRAWLER_DB_NAME)}")
        results = load_analysis_results_from_db()
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al cargar resultados de la base de datos: {e}")

# Endpoint para generar el informe SEO
@app.post("/generate-report/", summary="Generar informe SEO técnico", response_description="Contenido del informe SEO")
async def generate_seo_report(request: GenerateReportRequest):
    """
    Inicia la generación de un informe SEO técnico utilizando un agente de IA en un proceso separado.
    """
    print("API - Solicitud para generar informe recibida.")
    
    api_key = request.api_key

    if not api_key:
        raise HTTPException(status_code=400, detail="La clave API de OpenAI es requerida para generar el informe.")

    result_queue = Queue()
    
    process = Process(target=_generate_report_in_process, args=(result_queue, api_key))
    process.start()

    report_content = None
    try:
        report_content = await asyncio.to_thread(result_queue.get, timeout=300)
        
        if isinstance(report_content, dict) and "error" in report_content:
            raise HTTPException(status_code=500, detail=f"Error al generar el informe SEO en proceso hijo: {report_content['error']}")

        return {"report": report_content}
    except Exception as e:
        print(f"API - Error al generar el informe (principal): {e}")
        if process.is_alive():
            print("API - DEBUG: El proceso del informe sigue vivo, intentando terminarlo.")
            process.terminate()
            process.join()
        
        if "Empty" in str(e) or "timed out" in str(e):
             raise HTTPException(status_code=504, detail=f"La generación del informe tardó demasiado y excedió el tiempo límite. {e}")
        else:
            raise HTTPException(status_code=500, detail=f"Error al generar el informe SEO: {e}")
    finally:
        if process.is_alive():
            print("API - DEBUG: Finalizando el proceso del informe.")
            process.terminate()
            process.join()

# Endpoint para limpiar la base de datos
@app.delete("/clear-database/", summary="Limpiar la base de datos", response_description="Mensaje de confirmación de limpieza")
async def clear_database():
    """
    Elimina todos los datos de la tabla 'crawled_pages' en la base de datos.
    """
    conn = None
    try:
        db_path = CRAWLER_DB_NAME
        print(f"API - DEBUG: Intentando limpiar la base de datos en: {os.path.abspath(db_path)}")
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM crawled_pages")
        count_before = cursor.fetchone()[0]
        print(f"API - DEBUG: Filas en la base de datos antes de borrar: {count_before}")

        cursor.execute("DELETE FROM crawled_pages")
        conn.commit()
        
        cursor.execute("SELECT COUNT(*) FROM crawled_pages")
        count_after = cursor.fetchone()[0]
        print(f"API - DEBUG: Filas en la base de datos después de borrar: {count_after}")

        return {"message": "Base de datos limpiada exitosamente."}
    except sqlite3.Error as e:
        raise HTTPException(status_code=500, detail=f"Error al limpiar la base de datos: {e}")
    finally:
        if conn:
            conn.close()

# Bloque de ejecución principal para Uvicorn
if __name__ == "__main__":
    from multiprocessing import freeze_support
    freeze_support() 

    uvicorn.run(app, host="0.0.0.0", port=8000)
