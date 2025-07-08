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

# Instancia principal de FastAPI
app = FastAPI(
    title="SEO Crawler & Reporter API",
    description="API para rastrear sitios web, analizar SEO técnico y generar informes.",
    version="1.0.0",
    lifespan=lifespan
)

# --- CONFIGURACIÓN DE CORS ---
FRONTEND_RENDER_URL = "https://technicalseoagent-1.onrender.com" # <--- ¡REEMPLAZA CON LA URL REAL DE TU FRONTEND!

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
    
    # Validar que max_pages sea al menos 1
    if max_pages < 1:
        print("CRAWLER - WARNING: max_pages debe ser al menos 1. Ajustando a 1.")
        max_pages = 1

    try:
        parsed_target_url = urlparse(target_url)
        base_domain = parsed_target_url.netloc

        urls_to_crawl = [target_url]
        processed_urls = set()
        
        # Usamos una lista para URLs pendientes de añadir a la cola, para no modificar la cola mientras iteramos sobre ella
        # Aunque aquí el pop(0) lo haría seguro, es una buena práctica para bucles donde la iteración es directa sobre la lista.
        # No obstante, el principal error estaba en el len(processed_urls) y el break.
        
        while urls_to_crawl and len(processed_urls) < max_pages:
            current_url = urls_to_crawl.pop(0) # Obtener la siguiente URL de la cola

            # PRIMERO: Comprobamos si la URL ya ha sido procesada o si estamos a punto de superar el límite
            if current_url in processed_urls:
                print(f"CRAWLER - INFO: Saltando URL ya procesada: {current_url}")
                continue # Pasa a la siguiente iteración del bucle while
            
            if len(processed_urls) >= max_pages:
                print(f"CRAWLER - INFO: Límite de {max_pages} páginas alcanzado. No se procesarán más.")
                break # Salir del bucle while principal

            # AÑADIR LA URL AL CONJUNTO DE PROCESADAS ANTES DE PROCESARLA
            # Esto es CRUCIAL para que el contador de 'processed_urls' aumente.
            processed_urls.add(current_url) 
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

            # AÑADIR NUEVOS ENLACES A LA COLA SOLO SI NO SE HA ALCANZADO EL LÍMITE Y NO ESTÁN YA EN PROCESADAS/COLA
            for link in found_links:
                # Comprobar si el enlace pertenece al mismo dominio base y si NO ha sido ya procesado
                # NI está ya en la cola de urls_to_crawl
                if urlparse(link).netloc == base_domain and \
                   link not in processed_urls and \
                   link not in urls_to_crawl: # <--- IMPORTANTE: Evitar duplicados en la cola
                    
                    if len(processed_urls) + len(urls_to_crawl) < max_pages: # Contar las páginas procesadas MÁS las que ya están en cola
                        urls_to_crawl.append(link)
                    else:
                        print(f"CRAWLER - INFO: Límite de páginas {max_pages} (procesadas + en cola) alcanzado. No se añadirán más enlaces a la cola después de: {link}")
                        break # Salir del bucle 'for link in found_links'

            # Pequeña pausa para evitar sobrecargar el servidor y ser respetuosos con el sitio web
            await asyncio.sleep(1) 
            
        print(f"CRAWLER - INFO: Rastreo completado para {target_url}. Total de páginas procesadas: {len(processed_urls)}. Resultados en la base de datos.")
    except Exception as e:
        print(f"CRAWLER - ERROR: Un error inesperado ocurrió durante el rastreo: {e}")
        import traceback
        traceback.print_exc() # Imprimir el stack trace completo para depuración

# Endpoint para obtener todos los resultados de análisis
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

# Endpoint para generar el informe SEO
@app.post("/generate-report/", summary="Generar informe SEO técnico", response_description="Contenido del informe SEO")
async def generate_seo_report():
    """
    Inicia la generación de un informe SEO técnico utilizando un agente de IA en un proceso separado.
    """
    print("API - Solicitud para generar informe recibida.")
    
    result_queue = Queue()
    
    process = Process(target=_generate_report_in_process, args=(result_queue,))
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
    print("Para ejecutar localmente, asegúrate de que DATABASE_URL esté configurada.")
    print("Usa 'uvicorn Backend.my_agents.master:app --reload' y configura DATABASE_URL en tu entorno.")