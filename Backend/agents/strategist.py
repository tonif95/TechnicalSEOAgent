import os
from agents import Agent, Runner
from dotenv import load_dotenv

# --- Constantes ---
REPORTS_DIR = "informes" # Debe coincidir con la carpeta donde el analizador guarda su informe
ANALYZER_REPORT_FILE_NAME = "informe_seo_tecnico_analizador.txt"
STRATEGIST_PLAN_FILE_NAME = "plan_estrategico_seo.txt"

# Carga las variables de entorno para la clave de API de OpenAI
# Ajusta la ruta si tu .env no está en el mismo nivel que la carpeta padre de 'informes'
load_dotenv(dotenv_path="../.env") 

# 1. Función para cargar el informe del Agente Analizador
def load_analyzer_report():
    """
    Carga el contenido del archivo .txt generado por el Agente Analizador.
    """
    report_filepath = os.path.join(REPORTS_DIR, ANALYZER_REPORT_FILE_NAME)
    
    print(f"Buscando el informe del analizador en: '{report_filepath}'...")

    if not os.path.exists(report_filepath):
        raise FileNotFoundError(
            f"¡Error! No se encontró el informe del analizador en '{report_filepath}'. "
            f"Asegúrate de que el Agente Analizador se haya ejecutado y haya guardado el archivo."
        )

    with open(report_filepath, 'r', encoding='utf-8') as f:
        report_content = f.read()
    
    print(f"Informe del analizador cargado exitosamente.")
    return report_content

# 2. Función principal para ejecutar el Agente Estratega
def generate_strategic_seo_plan():
    print("✅ Iniciando Agente Estratega para generar el plan de acción SEO...")

    # --- AGENTE ESTRATEGA (SEO Strategist Agent) ---
    instructions_strategist = (
        "You are an elite SEO Strategist and a meticulous project manager with a deep understanding of technical SEO implications. "
        "Your expertise lies in translating complex audit findings into clear, actionable, and prioritized plans. "
        "You MUST strictly adhere to the issues and recommendations PRESENTED in the provided audit report. "
        "Do NOT invent or infer new problems or solutions not explicitly mentioned in the input report. "
        "For each identified issue (from the report's 'Recomendaciones Prácticas'), you will provide:"
        "1. A clear, user-friendly title for the issue."
        "2. Step-by-step instructions for the solution, simple enough for a non-technical user."
        "3. Concrete examples relevant to a website like 'chollovacaciones.com' if the issue is general."
        "4. An estimated SEO Impact (Alto, Medio, Bajo) and implementation Effort (Alto, Medio, Bajo)."
        "Your final output should be a structured, prioritized action plan, written entirely in Spanish from Spain."
    
    )

    strategist_agent = Agent(
        name="SEO Strategist Agent",
        instructions=instructions_strategist,
        model="gpt-4o-mini" # Puedes ajustar el modelo si es necesario
    )

    # Cargar el informe generado por el agente analizador
    analyzer_report_content = load_analyzer_report()

    # El prompt para el agente estratega, utilizando el contenido del informe del analizador
    prompt_strategist = f"""
    Como **Agente Estratega SEO de élite**, tu misión es transformar un informe de auditoría técnica en un **plan de acción claro, priorizado y accionable**.

    **TU ÚNICA FUENTE DE INFORMACIÓN SON LOS DATOS CONTENIDOS EN EL INFORME DE AUDITORÍA ADJUNTO.**
    **BAJO NINGUNA CIRCUNSTANCIA DEBES INVENTAR O INFERIR PROBLEMAS, CAUSAS O SOLUCIONES QUE NO ESTÉN EXPLÍCITAMENTE MENCIONADOS EN EL INFORME RECIBIDO.**

    **Objetivo Principal:** Convertir los hallazgos y recomendaciones del Agente Analizador en un plan de trabajo concreto y fácil de entender, dirigido a un propietario de sitio web o un equipo de desarrollo sin un profundo conocimiento técnico de SEO.

    **Estructura de la Respuesta Requerida:**

    ### 1. Plan de Acción Priorizado

    Presenta un listado numerado de los problemas identificados en el informe, ordenados de mayor a menor prioridad. La prioridad debe basarse en el **impacto potencial en el SEO** y la **urgencia de solución**. Utiliza un título claro para cada problema.

    ### 2. Soluciones Detalladas y Accionables

    Para **CADA UNO de los problemas priorizados** en la sección anterior, proporciona:

    * **Título del Problema**: (El mismo que en la priorización)
    * **Recomendación**: Una breve descripción de la solución general.
    * **Pasos a Seguir**: Instrucciones claras, numeradas y paso a paso, que un usuario no técnico pueda seguir. Evita la jerga.
    * **Ejemplo Concreto**: Si el problema es genérico (ej. "imágenes sin alt"), proporciona un ejemplo práctico aplicable a un sitio web de viajes como 'chollovacaciones.com' o describe cómo se vería la solución en el código o en un CMS típico (como WordPress). Si el informe ya da un ejemplo específico, úsalo.

    * **Impacto SEO Estimado**: Indica "Alto", "Medio" o "Bajo". Este es el beneficio potencial de implementar la solución en la visibilidad y el tráfico orgánico.
    * **Esfuerzo de Implementación Estimado**: Indica "Alto", "Medio" o "Bajo". Este es el tiempo y los recursos aproximados para llevar a cabo la solución.

    ### 3. Resumen Ejecutivo del Plan

    Ofrece una conclusión concisa destacando los puntos clave del plan y cómo su implementación contribuirá a mejorar significativamente el SEO técnico del sitio.

    ---

    **Idioma de la Respuesta:** Español de España.

    **Aquí tienes el informe de auditoría técnica que debes analizar para crear este plan:**

    --- INFORME DE AUDITORÍA TÉCNICA PROPORCIONADO POR EL ANALIZADOR ---
    {analyzer_report_content}
    --- FIN DEL INFORME DE AUDITORÍA ---
    """

    print("🚀 Ejecutando Agente Estratega para generar el plan de acción estratégico...")
    strategist_result = Runner.run_sync(strategist_agent, prompt_strategist)

    strategic_plan_content = strategist_result.final_output
    
    # Asegúrate de que la carpeta 'informes' exista para guardar el plan
    os.makedirs(REPORTS_DIR, exist_ok=True)

    # Guarda el plan estratégico en un archivo .txt
    strategic_plan_file_path = os.path.join(REPORTS_DIR, STRATEGIST_PLAN_FILE_NAME)
    with open(strategic_plan_file_path, 'w', encoding='utf-8') as f:
        f.write(strategic_plan_content)

    print(f"\n🏆 Plan de Acción Estratégico SEO Generado y guardado en: {strategic_plan_file_path}")
    print("--------------------------------------------------")

# Ejecutar directamente cuando el script se ejecuta
if __name__ == "__main__":
    generate_strategic_seo_plan()