import sys
import os
import contextlib
from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from pydantic import BaseModel, HttpUrl
import uvicorn
import asyncio
from urllib.parse import urlparse
from dotenv import load_dotenv
from multiprocessing import Process, Queue
import time
import uuid # Para generar IDs únicos para las tareas

# --- IMPORTACIONES ADICIONALES PARA DB Y CORS ---
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text
# --- FIN IMPORTACIONES ADICIONALES ---

# Configuración de PYTHONPATH para asegurar que se puedan importar módulos locales
project_root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root_dir not in sys.path:
    sys.path.insert(0, project_root_dir)

# Importaciones de módulos de la aplicación
from Backend.my_agents.crawler import setup_database, get_html_and_parse, analyze_html_content, save_to_database, SessionLocal, CrawledPage
from Backend.my_agents.analyzer import _generate_report_in_process

# --- OBTENER DATABASE_URL DE LAS VARIABLES DE ENTORNO ---
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    print("ERROR: La variable de entorno DATABASE_URL no está configurada. La aplicación no puede iniciar.")
    raise Exception("DATABASE_URL no está configurada en las variables de entorno.")

# --- Diccionario para almacenar el estado de las tareas de rastreo (en memoria) ---
# En un entorno de producción real, esto debería ser una tabla en la base de datos
# para persistir el estado entre reinicios del servidor.
crawl_tasks_status = {}

# --- Dependencia para obtener una sesión de base de datos ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

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
        print("Base de datos PostgreSQL verificada.")
    except Exception as e:
        print(f"ERROR: No se pudo inicializar la base de datos: {e}")
        raise

    yield
    print("Cerrando la aplicación FastAPI...")
    # Limpiar el diccionario de tareas al cerrar la aplicación
    crawl_tasks_status.clear()

# Instancia principal de FastAPI
app = FastAPI(
    title="SEO Crawler & Reporter API",
    description="API para rastrear sitios web, analizar SEO técnico y generar informes.",
    version="1.0.0",
    lifespan=lifespan
)

# --- CONFIGURACIÓN DE CORS ---
FRONTEND_RENDER_URL = "https://technicalseoagent-1.onrender.com"

origins = [
    "http://localhost",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    FRONTEND_RENDER_URL,
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# --- FIN CONFIGURACIÓN DE CORS ---

# Modelo para la URL de rastreo
class CrawlRequest(BaseModel):
    url: HttpUrl
    max_pages: int = 5

# Modelo para la solicitud de generación de informe
class GenerateReportRequest(BaseModel):
    openai_api_key: str # La clave API que vendrá del frontend

# Endpoint para iniciar el rastreo
@app.post("/crawl/", summary="Iniciar rastreo de un sitio web", response_description="Mensaje de inicio de rastreo")
async def start_crawl(request: CrawlRequest, background_tasks: BackgroundTasks):
    """
    Inicia un proceso de rastreo en segundo plano para la URL y el número de páginas especificados.
    Devuelve un ID de tarea para que el frontend pueda consultar el estado.
    """
    target_url = str(request.url)
    max_pages = request.max_pages
    task_id = str(uuid.uuid4()) # Generar un ID único para la tarea

    if not target_url.startswith(("http://", "https://")):
        raise HTTPException(status_code=400, detail="La URL debe comenzar con 'http://' o 'https://'")

    # Inicializar el estado de la tarea
    crawl_tasks_status[task_id] = {"status": "pending", "progress": 0, "total_pages": max_pages, "crawled_pages": 0, "url": target_url}

    print(f"API - Endpoint /crawl/ recibido para URL: {target_url}, max_pages: {max_pages}, Task ID: {task_id}")
    # Pasar el task_id a la tarea de fondo para que pueda actualizar su estado
    background_tasks.add_task(run_crawl_process, target_url, max_pages, task_id)
    print(f"API - Tarea de rastreo añadida a BackgroundTasks con ID: {task_id}.")
    return {"message": f"Rastreo iniciado para {target_url} con un máximo de {max_pages} páginas. Esto se ejecutará en segundo plano.", "task_id": task_id}

async def run_crawl_process(target_url: str, max_pages: int, task_id: str):
    """
    Lógica principal del rastreador de páginas web.
    Actualiza el estado de la tarea en crawl_tasks_status.
    """
    print(f"CRAWLER - INFO: run_crawl_process iniciado para {target_url} con límite de {max_pages} páginas. Task ID: {task_id}")
    
    if max_pages < 1:
        print("CRAWLER - WARNING: max_pages debe ser al menos 1. Ajustando a 1.")
        max_pages = 1
        crawl_tasks_status[task_id]["total_pages"] = 1 # Actualizar el total de páginas si se ajusta

    crawl_tasks_status[task_id]["status"] = "running"
    
    try:
        parsed_target_url = urlparse(target_url)
        base_domain = parsed_target_url.netloc

        urls_to_crawl = [target_url]
        processed_urls = set()
        
        while urls_to_crawl and len(processed_urls) < max_pages:
            current_url = urls_to_crawl.pop(0)

            if current_url in processed_urls:
                print(f"CRAWLER - INFO: Saltando URL ya procesada: {current_url}")
                continue
            
            if len(processed_urls) >= max_pages:
                print(f"CRAWLER - INFO: Límite de {max_pages} páginas alcanzado. No se procesarán más.")
                break 

            processed_urls.add(current_url) 
            # Actualizar el progreso de la tarea
            crawl_tasks_status[task_id]["crawled_pages"] = len(processed_urls)
            crawl_tasks_status[task_id]["progress"] = int((len(processed_urls) / max_pages) * 100)
            
            print(f"CRAWLER - DEBUG: Procesando URL: {current_url}. Páginas procesadas hasta ahora: {len(processed_urls)}/{max_pages}. URLs restantes en cola: {len(urls_to_crawl)}")

            soup, original_html_content, prettified_html_content, found_links = \
                get_html_and_parse(current_url, base_domain)

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
                if urlparse(link).netloc == base_domain and \
                   link not in processed_urls and \
                   link not in urls_to_crawl:
                    
                    if len(processed_urls) < max_pages:
                        urls_to_crawl.append(link)
                    else:
                        print(f"CRAWLER - INFO: Límite de páginas {max_pages} (procesadas) alcanzado. No se añadirán más enlaces a la cola después de: {link}")
                        break 

            await asyncio.sleep(1) 
            
        print(f"CRAWLER - INFO: Rastreo completado para {target_url}. Total de páginas procesadas: {len(processed_urls)}. Resultados en la base de datos. Task ID: {task_id}")
        crawl_tasks_status[task_id]["status"] = "completed"
        crawl_tasks_status[task_id]["progress"] = 100
        crawl_tasks_status[task_id]["crawled_pages"] = len(processed_urls) # Asegurarse de que el conteo final sea exacto
    except Exception as e:
        print(f"CRAWLER - ERROR: Un error inesperado ocurrió durante el rastreo: {e}. Task ID: {task_id}")
        import traceback
        traceback.print_exc()
        crawl_tasks_status[task_id]["status"] = "failed"
        crawl_tasks_status[task_id]["error"] = str(e)

# --- NUEVO ENDPOINT PARA CONSULTAR EL ESTADO DEL RASTREO ---
@app.get("/crawl-status/{task_id}", summary="Obtener el estado de una tarea de rastreo", response_description="Estado actual de la tarea de rastreo")
async def get_crawl_status(task_id: str):
    """
    Devuelve el estado actual de una tarea de rastreo específica.
    """
    status = crawl_tasks_status.get(task_id)
    if not status:
        raise HTTPException(status_code=404, detail="ID de tarea de rastreo no encontrado.")
    return status

@app.get("/results/", summary="Obtener todos los resultados de análisis de la base de datos", response_description="Lista de resultados de análisis")
async def get_all_analysis_results(db: Session = Depends(get_db)):
    """
    Recupera y devuelve todos los resultados de análisis guardados en la base de datos.
    """
    try:
        results = db.query(CrawledPage).all()
        return [
            {
                "url": page.url,
                "timestamp": page.timestamp.isoformat() if page.timestamp else None,
                "analysis_results": page.analysis_results
            } for page in results
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al cargar resultados de la base de datos: {e}")

@app.post("/generate-report/", summary="Generar informe SEO técnico", response_description="Contenido del informe SEO")
async def generate_seo_report(request: GenerateReportRequest):
    """
    Inicia la generación de un informe SEO técnico utilizando un agente de IA en un proceso separado.
    La clave API se recibe del frontend en el payload.
    """
    print("API - Solicitud para generar informe recibida.")
    
    openai_api_key = request.openai_api_key

    if not openai_api_key:
        raise HTTPException(status_code=400, detail="La clave API de OpenAI es requerida en el payload.")

    result_queue = Queue()
    
    process = Process(target=_generate_report_in_process, args=(result_queue, openai_api_key, DATABASE_URL))
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
async def clear_database(db: Session = Depends(get_db)):
    """
    Elimina todos los datos de la tabla 'crawled_pages' en la base de datos.
    """
    try:
        db.execute(text("DELETE FROM crawled_pages"))
        db.commit()
        return {"message": "Base de datos limpiada exitosamente."}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error al limpiar la base de datos: {e}")

# Bloque de ejecución principal para Uvicorn (solo para desarrollo local)
if __name__ == "__main__":
    from multiprocessing import freeze_support
    freeze_support() 
    print("Para ejecutar localmente, asegúrate de que DATABASE_URL y OPENAI_API_KEY estén configuradas.")
    print("Usa 'uvicorn Backend.my_agents.master:app --reload' y configura DATABASE_URL y OPENAI_API_KEY en tu entorno.")