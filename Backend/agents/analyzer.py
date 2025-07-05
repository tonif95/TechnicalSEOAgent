import os
import json
from agents import Agent, Runner # Asume que 'agents' está disponible en tu entorno
from dotenv import load_dotenv

# --- Constantes ---
RESULTS_DIR = "resultados"
JSON_FILE_NAME = "all_analysis_results.json"
load_dotenv(dotenv_path="../.env") # Asegúrate de que la ruta a tu .env sea correcta

# Función para cargar el archivo JSON
def load_analysis_results():
    """
    Carga los resultados del análisis SEO desde un archivo JSON.

    Returns:
        dict: Un diccionario con los datos del análisis.
    Raises:
        FileNotFoundError: Si no se encuentra el archivo JSON.
    """
    json_filepath = os.path.join(RESULTS_DIR, JSON_FILE_NAME)
    if not os.path.exists(json_filepath):
        raise FileNotFoundError(f"No se encontró el archivo '{json_filepath}'")

    with open(json_filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

# Función principal para orquestar la generación del informe SEO
def generate_technical_seo_report():
    """
    Orquesta la ejecución del agente analizador para generar un informe SEO técnico.

    Returns:
        str: El contenido del informe SEO técnico generado.
    """
    print("✅ Iniciando el proceso de auditoría y estrategia SEO...")

    # --- AGENTE ANALIZADOR (Technical SEO Expert Agent) ---
    print("\n--- Paso 1: Ejecutando Agente Analizador (Technical SEO Expert Agent) ---")

    instructions_analyzer = (
        "You are a professional technical SEO agent. "
        "Your task is to identify technical SEO issues in website analysis data and produce concise, expert-level audit reports per URL. "
        "Only return bullet point lists of the issues, without any explanation or extra context."
    )
    
    seo_analyzer_agent = Agent(
        name="Technical SEO Expert Agent",
        instructions=instructions_analyzer,
        model="gpt-4o-mini"
    )

    loaded_results = load_analysis_results()

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

    Evita dar explicaciones técnicas muy complejas, sé claro y conciso y hazlo en español de españa.

    Estos son los datos a analizar en JSON:

    {json.dumps(loaded_results, indent=2, ensure_ascii=False)}
    """

    print("🚀 Ejecutando Agente Analizador para generar el informe...")
    analyzer_result = Runner.run_sync(seo_analyzer_agent, prompt_analyzer)
    
    analysis_report_content = analyzer_result.final_output
    
    print("\n📋 Informe SEO técnico generado por el Analizador y almacenado en la variable 'analysis_report_content'.")
    print("--------------------------------------------------")
    

    return analysis_report_content

# Este bloque solo se ejecuta si el script se corre directamente, no cuando se importa
if __name__ == "__main__":
    try:
        report_content = generate_technical_seo_report()
        print("\n--- Contenido del informe (primeras 500 caracteres) ---")
        print(report_content[:500] + "..." if len(report_content) > 500 else report_content)
        print("\n--- Fin del contenido del informe ---")
    except FileNotFoundError as e:
        print(f"Error: {e}")
    except Exception as e:
        print(f"Ocurrió un error inesperado: {e}")