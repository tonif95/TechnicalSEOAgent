import os
import json
from agents import Agent, Runner
from dotenv import load_dotenv

# --- Constantes ---
RESULTS_DIR = "resultados"
JSON_FILE_NAME = "all_analysis_results.json"
REPORTS_DIR = "informes" # Nueva constante para la carpeta de informes
load_dotenv(dotenv_path="../.env") # Asegúrate de que la ruta a tu .env sea correcta

# 1. Cargar el archivo JSON
def load_analysis_results():
    json_filepath = os.path.join(RESULTS_DIR, JSON_FILE_NAME)
    if not os.path.exists(json_filepath):
        raise FileNotFoundError(f"No se encontró el archivo '{json_filepath}'")

    with open(json_filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

# 2. Función principal para orquestar ambos agentes
def generate_technical_seo_report():
    print("✅ Iniciando el proceso de auditoría y estrategia SEO...")

    # --- AGENTE ANALIZADOR (Technical SEO Expert Agent) ---
    # Este agente identifica problemas y genera el informe inicial
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

    # El prompt para el agente analizador, incluyendo los datos JSON
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
    
    # Captura la salida completa del agente analizador en una variable
    analysis_report_content = analyzer_result.final_output
    
    # --- NUEVA LÓGICA: GUARDAR EL INFORME EN UN ARCHIVO TXT ---
    # Asegúrate de que la carpeta 'informes' exista
    os.makedirs(REPORTS_DIR, exist_ok=True)
    
    # Define la ruta del archivo de informe
    report_file_path = os.path.join(REPORTS_DIR, "informe_seo_tecnico_analizador.txt")
    
    # Guarda el contenido en el archivo
    with open(report_file_path, 'w', encoding='utf-8') as f:
        f.write(analysis_report_content)
    
    print(f"\n📋 Informe SEO técnico generado por el Analizador y guardado en: {report_file_path}")
    print("--------------------------------------------------")

# Ejecutar directamente
if __name__ == "__main__":
    generate_technical_seo_report()
