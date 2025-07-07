import sys
import os
import contextlib
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel, HttpUrl
import uvicorn
import asyncio
from urllib.parse import urlparse
from dotenv import load_dotenv
from multiprocessing import Process, Queue
import time

# --- ¡NUEVA IMPORTACIÓN NECESARIA PARA CORS! ---
from fastapi.middleware.cors import CORSMiddleware
# --- FIN NUEVA IMPORTACIÓN ---

# Configuración de PYTHONPATH para asegurar que se puedan importar módulos locales
# project_root_dir apunta a la carpeta 'Agenteseo'
project_root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root_dir not in sys.path:
    sys.path.insert(0, project_root_dir)

# Importaciones de módulos de la aplicación
# La función load_analysis_results_from_db se necesita para el endpoint /results/
from Backend.my_agents.crawler import setup_database, get_html_and_parse, analyze_html_content, save_to_database, DB_NAME as CRAWLER_DB_NAME
from Backend.my_agents.analyzer import _generate_report_in_process, load_analysis_results_from_db

# Cargar variables de entorno para el proceso principal (FastAPI)
# La ruta aquí es relativa a master.py (Backend/my_agents/) al archivo .env en Backend/
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))

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
        print(f"Base de datos {CRAWLER_DB_NAME} verificada.")
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

# --- ¡INICIO DEL BLOQUE DE CÓDIGO CORS QUE DEBES AÑADIR AQUÍ! ---

# Obtén la URL de tu frontend desplegado en Render.com
# 1. Ve a tu dashboard de Render.
# 2. Ve a tu servicio de frontend (se llama 'TechnicalSEOAgent-1' según tu captura).
# 3. Copia su "External URL" (será algo como: https://technicalseoagent-1.onrender.com).
#
# Es MUY IMPORTANTE que esta URL sea la correcta.
FRONTEND_RENDER_URL = "https://technicalseoagent-1.onrender.com" # <--- ¡REEMPLAZA CON LA URL REAL DE TU FRONTEND!

origins = [
    "http://localhost",
    "http://localhost:5173",  # Para desarrollo local de Vite
    "http://127.0.0.1:5173",  # Para desarrollo local de Vite
    FRONTEND_RENDER_URL,      # La URL de tu frontend desplegado en Render
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# --- ¡FIN DEL BLOQUE DE CÓDIGO CORS! ---


# Modelo para la URL de rastreo
class CrawlRequest(BaseModel):
    url: HttpUrl
    max_pages: int = 5

# Endpoint para iniciar el rastreo
@app.post("/crawl/", summary="Iniciar rastreo de un sitio web", response_description="Mensaje de inicio de rastreo")
async def start_crawl(request: CrawlRequest, background_tasks: BackgroundTasks):
    """
    Inicia un proceso de rastreo en segundo plano para la URL y el número de páginas especificados.
    """
    target_url = str(request.url)
    max_pages = request.max_pages

    if not target_url.startswith(("http://", "https://")):
        raise HTTPException(status_code=400, detail="La URL debe comenzar con 'http://' o 'https://'")

    print(f"API - Endpoint /crawl/ recibido para URL: {target_url}, max_pages: {max_pages}")
    background_tasks.add_task(run_crawl_process, target_url, max_pages)
    print(f"API - Tarea de rastreo añadida a BackgroundTasks.")
    return {"message": f"Rastreo iniciado para {target_url} con un máximo de {max_pages} páginas. Esto se ejecutará en segundo plano."}

async def run_crawl_process(target_url: str, max_pages: int):
    """
    Lógica principal del rastreador de páginas web.
    """
    print(f"CRAWLER - INFO: run_crawl_process iniciado para {target_url} con límite de {max_pages} páginas.")
    try:
        parsed_target_url = urlparse(target_url)
        base_domain = parsed_target_url.netloc

        urls_to_crawl = [target_url]
        processed_urls = set()
        
        while urls_to_crawl and len(processed_urls) < max_pages:
            current_url = urls_to_crawl.pop(0)
            
            print(f"CRAWLER - DEBUG: Intentando procesar URL: {current_url}. Páginas procesadas hasta ahora: {len(processed_urls)}/{max_pages}. URLs restantes en cola: {len(urls_to_crawl)}")

            # get_html_and_parse añade la URL al conjunto `processed_urls`
            # antes de intentar obtener el contenido.
            # Esto ayuda a manejar URLs que fallan en la solicitud sin entrar en un bucle infinito
            # y asegura que se cuenten para el límite `max_pages`.
            if current_url in processed_urls:
                print(f"CRAWLER - INFO: Saltando URL ya procesada: {current_url}")
                continue
            
            if len(processed_urls) >= max_pages:
                print(f"CRAWLER - INFO: Límite de {max_pages} páginas alcanzado. No se procesarán más.")
                break 

            soup, original_html_content, prettified_html_content, found_links = \
                get_html_and_parse(current_url, base_domain, processed_urls, max_pages)

            if soup:
                print(f"CRAWLER - DEBUG: 'soup' obtenido para {current_url}. Contiene HTML parseado.")
                analysis_results = analyze_html_content(current_url, soup)
                
                if analysis_results:
                    print(f"CRAWLER - DEBUG: 'analysis_results' obtenidos para {current_url}. Guardando en DB...")
                    save_to_database(current_url, original_html_content, prettified_html_content, analysis_results)
                    print(f"CRAWLER - INFO: Análisis y guardado en DB completado para: {current_url}")
                else:
                    print(f"CRAWLER - WARNING: 'analysis_results' es None para {current_url}. No se guardará en DB.")
            else:
                print(f"CRAWLER - WARNING: 'soup' es None para {current_url}. No se pudo obtener/parsear el HTML. Saltando análisis y guardado.")

            for link in found_links:
                if link not in processed_urls and urlparse(link).netloc == base_domain:
                    if len(processed_urls) < max_pages: 
                        urls_to_crawl.append(link)
                    else:
                        print(f"CRAWLER - INFO: Límite de páginas alcanzado al añadir nuevo enlace: {link}")
                        break

            await asyncio.sleep(1) # Pequeña pausa para evitar sobrecargar el servidor
            
        print(f"CRAWLER - INFO: Rastreo completado para {target_url}. Total de páginas procesadas: {len(processed_urls)}. Resultados en la base de datos.")
    except Exception as e:
        print(f"CRAWLER - ERROR: Un error inesperado ocurrió durante el rastreo: {e}")
        import traceback
        traceback.print_exc() # Imprimir el stack trace completo para depuración

# Endpoint para obtener todos los resultados de análisis
@app.get("/results/", summary="Obtener todos los resultados de análisis de la base de datos", response_description="Lista de resultados de análisis")
async def get_all_analysis_results():
    """
    Recupera y devuelve todos los resultados de análisis guardados en la base de datos.
    """
    try:
        results = load_analysis_results_from_db()
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al cargar resultados de la base de datos: {e}")

# Endpoint para generar el informe SEO
@app.post("/generate-report/", summary="Generar informe SEO técnico", response_description="Contenido del informe SEO")
async def generate_seo_report():
    """
    Inicia la generación de un informe SEO técnico utilizando un agente de IA en un proceso separado.
    """
    print("API - Solicitud para generar informe recibida.")
    
    result_queue = Queue() # Cola para comunicar resultados del proceso hijo
    
    # Iniciar el proceso para generar el informe
    # El target es la función que se ejecutará en el nuevo proceso
    process = Process(target=_generate_report_in_process, args=(result_queue,))
    process.start() # Inicia el proceso hijo

    report_content = None
    try:
        # Espera de forma asíncrona por el resultado de la cola del proceso hijo
        # Añade un timeout para evitar que la petición se quede colgada indefinidamente
        report_content = await asyncio.to_thread(result_queue.get, timeout=300) # Timeout en segundos (5 minutos)
        
        if isinstance(report_content, dict) and "error" in report_content:
            # Si el proceso hijo devolvió un error, lo propagamos como una HTTPException
            raise HTTPException(status_code=500, detail=f"Error al generar el informe SEO en proceso hijo: {report_content['error']}")

        return {"report": report_content}
    except Exception as e:
        print(f"API - Error al generar el informe (principal): {e}")
        # Intentar terminar el proceso hijo si todavía está vivo después de un error
        if process.is_alive():
            print("API - DEBUG: El proceso del informe sigue vivo, intentando terminarlo.")
            process.terminate() # Envía una señal de terminación
            process.join()      # Espera a que el proceso termine
        
        # Proporcionar mensajes de error más específicos al cliente
        if "Empty" in str(e) or "timed out" in str(e):
             raise HTTPException(status_code=504, detail=f"La generación del informe tardó demasiado y excedió el tiempo límite. {e}")
        else:
            # Captura otros errores inesperados
            raise HTTPException(status_code=500, detail=f"Error al generar el informe SEO: {e}")
    finally:
        # Asegurarse de que el proceso hijo termine, incluso si no hubo error
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
    import sqlite3 # Importación local para este endpoint
    conn = None
    try:
        conn = sqlite3.connect(CRAWLER_DB_NAME)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM crawled_pages")
        conn.commit()
        return {"message": "Base de datos limpiada exitosamente."}
    except sqlite3.Error as e:
        raise HTTPException(status_code=500, detail=f"Error al limpiar la base de datos: {e}")
    finally:
        if conn:
            conn.close()

# Bloque de ejecución principal para Uvicorn
if __name__ == "__main__":
    # Importante: Protege el bloque de multiprocesamiento para que funcione correctamente
    # en diferentes sistemas operativos (especialmente Windows).
    from multiprocessing import freeze_support
    freeze_support() 

    uvicorn.run(app, host="0.0.0.0", port=8000)