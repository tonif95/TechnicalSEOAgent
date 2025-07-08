import os
import json
# import sqlite3 # Ya no es necesario para PostgreSQL

# --- NUEVAS IMPORTACIONES PARA SQLAlchemy y PostgreSQL ---
# Importamos SessionLocal y CrawledPage desde el módulo crawler
# que ya tiene la configuración de SQLAlchemy para PostgreSQL
from Backend.my_agents.crawler import SessionLocal, CrawledPage
from sqlalchemy.orm import Session # Para el tipo de la sesión
# --- FIN NUEVAS IMPORTACIONES ---

# La constante DB_NAME ya no es relevante para PostgreSQL
# DB_NAME = "crawler_results.db"

# --- Función load_analysis_results_from_db modificada para PostgreSQL ---
def load_analysis_results_from_db():
    """
    Carga los resultados de análisis desde la base de datos PostgreSQL.
    Esta función crea su propia sesión de DB, lo cual es adecuado para ser llamada
    desde un proceso separado (_generate_report_in_process).
    """
    db = SessionLocal() # Crea una nueva sesión para este proceso
    try:
        # Consulta todos los resultados de la tabla CrawledPage
        results = db.query(CrawledPage).all()
        
        all_results = []
        for page in results:
            # Los analysis_results ya deberían ser un diccionario Python gracias al tipo JSON en SQLAlchemy
            if isinstance(page.analysis_results, dict):
                all_results.append(page.analysis_results)
            else:
                # Si por alguna razón no es un dict (ej. datos antiguos o error), intentar parsear
                try:
                    analysis_data = json.loads(page.analysis_results)
                    all_results.append(analysis_data)
                except json.JSONDecodeError as e:
                    print(f"Advertencia: Error al decodificar JSON para URL {page.url}: {e}")
        
        if not all_results:
            print(f"DEBUG: No se encontraron resultados en la base de datos PostgreSQL.")
            raise Exception(f"No se encontraron resultados en la base de datos PostgreSQL.")
        
        return all_results

    except Exception as e:
        print(f"ERROR al cargar resultados desde PostgreSQL: {e}")
        raise Exception(f"Error de base de datos al cargar resultados: {e}")
    finally:
        db.close() # Asegúrate de cerrar la sesión

# --- Función _generate_report_in_process modificada ---
def _generate_report_in_process(result_queue, openai_api_key: str):
    """
    Genera el informe SEO en un proceso separado.
    Recibe la clave API de OpenAI como argumento.
    """
    # Importar la librería 'agents' aquí dentro del proceso hijo
    # para evitar problemas de serialización si no es un módulo de nivel superior
    from agents import Agent, Runner 

    try:
        if not openai_api_key:
            error_msg = "OPENAI_API_KEY no fue proporcionada al proceso de generación de informe."
            print(f"[Proceso Agente] {error_msg}")
            result_queue.put({"error": error_msg})
            return

        print(f"  OPENAI_API_KEY: {'*' * len(openai_api_key) if openai_api_key else 'NO PROPORCIONADA o VACÍA'}")

        # --- ¡CAMBIO CRÍTICO AQUÍ! ---
        # Configurar la clave API como una variable de entorno TEMPORALMENTE
        # Esto es lo que la mayoría de las librerías OpenAI esperan por defecto
        os.environ["OPENAI_API_KEY"] = openai_api_key
        print("[Proceso Agente] DEBUG: OPENAI_API_KEY configurada en el entorno del proceso.")

        print("✅ [Proceso Agente] Iniciando el proceso de auditoría y estrategia SEO...")
        print("\n--- [Proceso Agente] Paso 1: Ejecutando Agente Analizador (Technical SEO Expert Agent) ---")

        instructions_analyzer = (
            "You are a professional technical SEO agent. "
            "Your task is to identify technical SEO issues in website analysis data and produce concise, expert-level audit reports per URL. "
            "Only return bullet point lists of the issues, without any explanation or extra context."
        )
        
        # Ahora el Agente no necesita el argumento api_key, lo leerá del entorno
        seo_analyzer_agent = Agent(
            name="Technical SEO Expert Agent",
            instructions=instructions_analyzer,
            model="gpt-4o-mini",
            # api_key=openai_api_key # <--- ¡ELIMINAR ESTA LÍNEA!
        )

        loaded_results = load_analysis_results_from_db()
        print(f"[Proceso Agente] DEBUG: Resultados cargados de la DB. Total de páginas: {len(loaded_results)}")

        prompt_analyzer = f"""
        Eres un experto en SEO técnico con mucha experiencia en auditorías completas de sitios web.
        Has recibido un JSON con datos de análisis automático de varias páginas web de un mismo sitio. Tu tarea es realizar un informe técnico global que incluya:
        1. Una visión general del estado SEO técnico del sitio web.
        2. Análisis de problemas recurrentes o globales que afectan a varias páginas (por ejemplo, enlazado interno, estructura de URLs, canonicales, velocidad, etc.).
        3. Identificación de errores técnicos detectados en las páginas (por URL), como falta de etiquetas importantes, problemas de imágenes, scripts, etc.
        4. Explicaciones claras y sencillas que ayuden a un usuario no experto a entender los problemas y por qué afectan al SEO.
        5. Recomendaciones prácticas para solucionar cada problema, priorizando los que más impactan.
        6. Resumen final con puntos clave para mejorar el SEO técnico globalmente.
        Para cada página, también incluye un listado breve con los errores técnicos más importantes detectados, en formato de puntos (bullet points).
        Evita dar explicaciones técnicas muy complejas, sé claro y conciso y hazlo en español de España.
        Estos son los datos a analizar en JSON:
        {json.dumps(loaded_results, indent=2, ensure_ascii=False)}
        """
        print("[Proceso Agente] DEBUG: Prompt para el agente analizador generado. Enviando a Runner...")

        analyzer_result = Runner.run_sync(seo_analyzer_agent, prompt_analyzer)
        print("[Proceso Agente] DEBUG: Runner.run_sync completado.")
        analysis_report_content = analyzer_result.final_output
        print("[Proceso Agente] DEBUG: Contenido final del informe obtenido del agente.")
        
        result_queue.put(analysis_report_content)
        print("[Proceso Agente] DEBUG: Resultado puesto en la cola.")

    except Exception as e:
        error_msg = f"ERROR [Proceso Agente]: Fallo en la generación del informe: {e}"
        print(f"[Proceso Agente] {error_msg}")
        result_queue.put({"error": error_msg})
        import traceback
        traceback.print_exc()
    finally:
        # Es buena práctica limpiar la variable de entorno después de usarla,
        # aunque en un proceso que termina esto no siempre es estrictamente necesario,
        # ayuda a evitar fugas si el proceso se reutilizara.
        if "OPENAI_API_KEY" in os.environ:
            del os.environ["OPENAI_API_KEY"]
            print("[Proceso Agente] DEBUG: OPENAI_API_KEY eliminada del entorno del proceso.")


def generate_technical_seo_report_sync():
    pass 

if __name__ == "__main__":
    # Este bloque es solo para pruebas locales de analyzer.py
    # Para que funcione, necesitarías pasar una clave API de OpenAI válida aquí.

    from multiprocessing import Queue
    test_queue = Queue()
    # Clave API de prueba para ejecución local. NO USAR EN PRODUCCIÓN.
    dummy_api_key = os.getenv("OPENAI_API_KEY_LOCAL_TEST", "sk-your-local-test-key") 
    
    print("--- Ejecutando _generate_report_in_process para prueba local ---")
    _generate_report_in_process(test_queue, dummy_api_key) # <--- Pasar la clave API aquí
    if not test_queue.empty():
        report = test_queue.get()
        if isinstance(report, dict) and "error" in report:
            print(f"\n--- Error al ejecutar informe directamente ---\n{report['error']}")
        else:
            print("\n--- Contenido del informe (primeras 500 caracteres) ---")
            print(report[:500] + "..." if len(report) > 500 else report)
            print("\n--- Fin del contenido del informe ---")
    else:
        print("El proceso directo no devolvió ningún resultado.")
    print("--- Fin de la prueba local ---")
