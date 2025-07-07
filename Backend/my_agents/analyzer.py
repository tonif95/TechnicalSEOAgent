import json
import os
import sys
import sqlite3
from datetime import datetime
from agents import Agent, Runner
from multiprocessing import Queue
# from dotenv import load_dotenv # Eliminado: la clave API se pasará como argumento

# Configuración de PYTHONPATH para asegurar que se puedan importar módulos locales
project_root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root_dir not in sys.path:
    sys.path.insert(0, project_root_dir)

# Importar la base de datos del crawler para cargar los resultados
from Backend.my_agents.crawler import DB_NAME as CRAWLER_DB_NAME

# Cargar variables de entorno para la clave de API de OpenAI (eliminado aquí, se pasará por argumento)
# load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))

# Directorio para guardar los informes generados
REPORTS_DIR = os.path.join(os.path.dirname(__file__), "reports")
os.makedirs(REPORTS_DIR, exist_ok=True)

def load_analysis_results_from_db():
    """
    Carga todos los resultados de análisis de SEO técnico de la base de datos.
    """
    conn = None
    try:
        conn = sqlite3.connect(CRAWLER_DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT url, analysis_results FROM crawled_pages")
        rows = cursor.fetchall()

        results = []
        for row in rows:
            url, analysis_json = row
            try:
                analysis_data = json.loads(analysis_json)
                results.append({"url": url, "analysis_results": analysis_data})
            except json.JSONDecodeError:
                print(f"WARNING: No se pudo decodificar JSON para la URL: {url}. Saltando.")
        return results
    except sqlite3.Error as e:
        print(f"ERROR: Error de base de datos al cargar resultados: {e}")
        return []
    finally:
        if conn:
            conn.close()

def generate_technical_seo_report(): # Ya no acepta api_key directamente aquí
    """
    Genera un informe técnico de SEO utilizando un agente de IA.
    Carga los resultados de análisis de la base de datos y los pasa al agente.
    La clave API se espera que esté en las variables de entorno.
    """
    print("ANALYSER - INFO: Iniciando la generación del informe técnico de SEO.")

    # Cargar los resultados de análisis de la base de datos
    analysis_data = load_analysis_results_from_db()

    if not analysis_data:
        print("ANALYSER - WARNING: No se encontraron datos de análisis en la base de datos para generar el informe.")
        raise FileNotFoundError("No se encontraron datos de análisis en la base de datos. Por favor, realice un rastreo primero.")

    # Convertir los datos de análisis a una cadena JSON formateada para el prompt
    formatted_analysis_data = json.dumps(analysis_data, indent=2, ensure_ascii=False)
    print(f"ANALYSER - DEBUG: Datos de análisis cargados y formateados. Longitud: {len(formatted_analysis_data)} caracteres.")

    # --- AGENTE ANALIZADOR (SEO Analyzer Agent) ---
    instructions_analyzer = (
        "You are an expert Technical SEO Auditor. Your task is to analyze raw technical SEO data "
        "and synthesize it into a clear, concise, and actionable audit report. "
        "You MUST strictly adhere to the issues and recommendations PRESENTED in the provided data. "
        "Do NOT invent or infer new problems or solutions not explicitly mentioned in the input data. "
        "Focus on identifying critical technical SEO issues and providing practical recommendations. "
        "Your report should be structured logically, covering key areas like crawlability, indexability, "
        "on-page elements, performance, and security. "
        "The report should be written entirely in Spanish from Spain."
    )

    # El agente ahora leerá la clave API de las variables de entorno
    analyzer_agent = Agent(
        name="SEO Analyzer Agent",
        instructions=instructions_analyzer,
        model="gpt-4o-mini", # Puedes ajustar el modelo si es necesario
        # api_key=openai_api_key # Eliminado: ya no se pasa directamente aquí
    )

    prompt_analyzer = f"""
    Como **Auditor SEO Técnico experto**, tu misión es analizar los datos técnicos de SEO proporcionados y sintetizarlos en un **informe de auditoría claro, conciso y accionable**.

    **TU ÚNICA FUENTE DE INFORMACIÓN SON LOS DATOS CONTENIDOS EN EL JSON ADJUNTO.**
    **BAJO NINGUNA CIRCUNSTANCIA DEBES INVENTAR O INFERIR PROBLEMAS, CAUSAS O SOLUCIONES QUE NO ESTÉN EXPLÍCITAMENTE MENCIONADOS EN LOS DATOS RECIBIDOS.**

    **Objetivo Principal:** Identificar problemas críticos de SEO técnico y proporcionar recomendaciones prácticas.

    **Estructura del Informe Requerida:**

    ### 1. Resumen Ejecutivo

    * Una visión general de los hallazgos más importantes y su impacto general.

    ### 2. Hallazgos Clave y Recomendaciones Prácticas

    * Para cada URL analizada o para problemas generales que afecten a múltiples URLs, detalla los problemas técnicos encontrados.
    * Para cada problema, proporciona:
        * **Problema**: Descripción clara del problema técnico.
        * **Causa Potencial**: Breve explicación de por qué ocurre.
        * **Impacto SEO**: Cómo afecta a la visibilidad y rendimiento en buscadores.
        * **Recomendación**: Pasos concretos y accionables para solucionar el problema.

    ### 3. Conclusión

    * Un breve resumen de los próximos pasos o consideraciones finales.

    ---

    **Idioma del Informe:** Español de España.

    **Aquí tienes los datos de análisis técnico de SEO que debes auditar:**

    --- DATOS DE ANÁLISIS TÉCNICO ---
    {formatted_analysis_data}
    --- FIN DE LOS DATOS DE ANÁLISIS ---
    """

    print("ANALYSER - INFO: Ejecutando Agente Analizador para generar el informe...")
    analyzer_result = Runner.run_sync(analyzer_agent, prompt_analyzer)

    report_content = analyzer_result.final_output
    
    # Guardar el informe en un archivo
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file_name = f"seo_technical_audit_report_{timestamp}.md"
    report_file_path = os.path.join(REPORTS_DIR, report_file_name)
    
    with open(report_file_path, 'w', encoding='utf-8') as f:
        f.write(report_content)
    
    print(f"ANALYSER - INFO: Informe técnico de SEO generado y guardado en: {report_file_path}")
    print("--------------------------------------------------")
    
    return report_content

def _generate_report_in_process(result_queue: Queue, api_key: str): # Aceptar la clave API
    """
    Función wrapper para ejecutar generate_technical_seo_report en un proceso separado.
    Pone el resultado (o error) en una cola.
    """
    try:
        # Establecer la variable de entorno para la clave API en este proceso
        os.environ["OPENAI_API_KEY"] = api_key
        report = generate_technical_seo_report() # Ya no se pasa la clave directamente
        result_queue.put(report)
    except Exception as e:
        print(f"ANALYSER - ERROR: Error en _generate_report_in_process: {e}")
        result_queue.put({"error": str(e)})

# Bloque de ejecución principal para Uvicorn (si se ejecuta analyzer.py directamente)
if __name__ == "__main__":
    # Este bloque es principalmente para pruebas directas del analizador.
    # En un entorno de producción, main.py llamará a estas funciones.
    # Para probar aquí, necesitarías una clave API.
    # test_api_key = os.getenv("OPENAI_API_KEY") # Cargar desde .env para pruebas directas
    # if not test_api_key:
    #     print("ADVERTENCIA: OPENAI_API_KEY no configurada. El agente podría fallar.")
    #     sys.exit(1)

    # Para pruebas, puedes proporcionar una clave directamente o cargarla de un .env
    # Por ejemplo:
    test_api_key = "YOUR_OPENAI_API_KEY_HERE_FOR_TESTING" # Reemplaza con una clave real para probar
    if test_api_key == "YOUR_OPENAI_API_KEY_HERE_FOR_TESTING":
        print("ADVERTENCIA: Usando una clave API de prueba. Por favor, reemplázala por una real para uso en producción.")
        # O carga desde .env si quieres probar el flujo de env:
        # from dotenv import load_dotenv
        # load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))
        # test_api_key = os.getenv("OPENAI_API_KEY")
        # if not test_api_key:
        #     print("ERROR: La clave API de OpenAI no se encontró en las variables de entorno.")
        #     sys.exit(1)


    print("ANALYSER - INFO: Ejecutando analyzer.py directamente para generar un informe de prueba.")
    # Asegúrate de que haya datos en la base de datos para que el informe se genere.
    # Si no hay datos, esto fallará con FileNotFoundError.
    try:
        # Simular la llamada desde main.py
        q = Queue()
        _generate_report_in_process(q, test_api_key)
        report_output = q.get()
        if isinstance(report_output, dict) and "error" in report_output:
            print(f"ANALYSER - ERROR: Fallo al generar el informe: {report_output['error']}")
        else:
            print("\n--- Informe técnico de SEO generado (primeras 500 caracteres) ---")
            print(report_output[:500] + "..." if len(report_output) > 500 else report_output)
            print("\n--- Fin del informe ---")
    except Exception as e:
        print(f"ANALYSER - ERROR: Error inesperado durante la ejecución directa: {e}")
        import traceback
        traceback.print_exc()

