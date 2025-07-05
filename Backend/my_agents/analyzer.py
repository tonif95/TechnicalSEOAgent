import os
import json
import sqlite3
# No es necesario importar load_dotenv aquí a nivel global del archivo.

# Constantes
DB_NAME = "crawler_results.db"

def load_analysis_results_from_db():
    # ... (esta función se mantiene igual, no necesita cambios)
    conn = None
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT url, analysis_results FROM crawled_pages")
        
        all_results = []
        for row in cursor.fetchall():
            url = row[0]
            analysis_json_str = row[1]
            try:
                analysis_data = json.loads(analysis_json_str)
                all_results.append(analysis_data)
            except json.JSONDecodeError as e:
                print(f"Advertencia: Error al decodificar JSON para URL {url}: {e}")
        
        if not all_results:
            print(f"DEBUG: No se encontraron resultados en la base de datos '{DB_NAME}'.")
            raise Exception(f"No se encontraron resultados en la base de datos '{DB_NAME}'.")
        
        return all_results

    except sqlite3.Error as e:
        print(f"ERROR DB al cargar resultados: {e}")
        raise Exception(f"Error de base de datos al cargar resultados: {e}")
    except Exception as e:
        print(f"ERROR general al cargar resultados: {e}")
        raise e
    finally:
        if conn:
            conn.close()

def _generate_report_in_process(result_queue):
    # ¡Importar y cargar dotenv DENTRO del proceso hijo!
    from dotenv import load_dotenv
    from agents import Agent, Runner # Importar la librería 'agents' aquí dentro

    try:
        # Calcular la ruta absoluta al archivo .env.
        # Si .env está en Backend/, necesitamos subir solo un nivel desde my_agents/
        dotenv_path_absolute = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".env"))

        print(f"[Proceso Agente] CWD del proceso hijo: {os.getcwd()}")
        print(f"[Proceso Agente] Ruta ABSOLUTA calculada para .env: {dotenv_path_absolute}")

        if not os.path.exists(dotenv_path_absolute):
            error_msg = f"ERROR: El archivo .env NO existe en la ruta calculada: {dotenv_path_absolute}. Por favor, verifica la ubicación de tu archivo .env."
            print(f"[Proceso Agente] {error_msg}")
            result_queue.put({"error": error_msg})
            return

        loaded_success = load_dotenv(dotenv_path=dotenv_path_absolute, override=True, verbose=True)
        print(f"[Proceso Agente] dotenv cargado exitosamente: {loaded_success}")
        
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if not openai_api_key:
            error_msg = "OPENAI_API_KEY no está configurada en las variables de entorno del proceso hijo. ¡Verifica el archivo .env y su contenido!"
            print(f"[Proceso Agente] {error_msg}")
            result_queue.put({"error": error_msg})
            return

        print(f"  OPENAI_API_KEY: {'*' * len(openai_api_key) if openai_api_key else 'NO ESTABLECIDA o VACÍA'}")

        print("✅ [Proceso Agente] Iniciando el proceso de auditoría y estrategia SEO...")
        print("\n--- [Proceso Agente] Paso 1: Ejecutando Agente Analizador (Technical SEO Expert Agent) ---")

        instructions_analyzer = (
            "You are a professional technical SEO agent. "
            "Your task is to identify technical SEO issues in website analysis data and produce concise, expert-level audit reports per URL. "
            "Only return bullet point lists of the issues, without any explanation or extra context."
        )
        
        # --- ¡CAMBIO CRUCIAL AQUÍ! ---
        # Elimina el parámetro 'api_key'. La librería 'agents' ya leerá OPENAI_API_KEY
        # directamente de las variables de entorno porque ya las cargaste con dotenv.
        seo_analyzer_agent = Agent(
            name="Technical SEO Expert Agent",
            instructions=instructions_analyzer,
            model="gpt-4o-mini" # ¡Quita 'api_key=openai_api_key' de aquí!
        )
        # --- FIN CAMBIO CRUCIAL ---

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

def generate_technical_seo_report_sync():
    pass 

if __name__ == "__main__":
    from multiprocessing import Queue
    test_queue = Queue()
    _generate_report_in_process(test_queue)
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