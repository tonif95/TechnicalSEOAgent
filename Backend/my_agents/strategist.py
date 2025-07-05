import os
from agents import Agent, Runner
from dotenv import load_dotenv
import sys

# Añade el directorio padre al sys.path para poder importar seo_utils
# Asegúrate de que la estructura de tu proyecto permita esta importación.
# Por ejemplo, si 'strategist.py' y 'seo_utils.py' están en el mismo nivel,
# o si 'seo_utils.py' está en una subcarpeta y necesitas ajustar la ruta.
# Si 'seo_utils.py' está en una carpeta 'utils' al mismo nivel que 'strategist.py',
# podrías necesitar: sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'utils')))
# Para este ejemplo, asumimos que seo_utils.py está en el mismo directorio
# o en un directorio que ya está en el PYTHONPATH.
try:
    # Se corrige la importación a 'seo_utils' según la conversación anterior
    from analyzer import generate_technical_seo_report
except ImportError as e:
    print(f"Error al importar la función generate_technical_seo_report de seo_utils: {e}")
    print("Asegúrate de que 'seo_utils.py' esté en el mismo directorio o en el PYTHONPATH.")
    sys.exit(1)


# Carga las variables de entorno para la clave de API de OpenAI
load_dotenv(dotenv_path="../.env") 

class SEOStrategist:
    """
    Clase para orquestar la generación de un plan estratégico SEO
    basado en un informe de auditoría técnica.
    """
    def __init__(self):
        # El constructor puede inicializar cualquier configuración necesaria
        pass

    def generate_strategic_plan(self):
        """
        Orquesta la ejecución del Agente Estratega para generar un plan de acción SEO.

        Returns:
            str: El contenido del plan estratégico SEO generado.
        """
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
            "3. Concrete examples relevant to a website like 'wikipedia.com' if the issue is general."
            "4. An estimated SEO Impact (Alto, Medio, Bajo) and implementation Effort (Alto, Medio, Bajo)."
            "Your final output should be a structured, prioritized action plan, written entirely in Spanish from Spain."
        )

        strategist_agent = Agent(
            name="SEO Strategist Agent",
            instructions=instructions_strategist,
            model="gpt-4o-mini" # Puedes ajustar el modelo si es necesario
        )

        # --- Obtener el informe directamente de la función del analizador ---
        print("\n--- Paso 1: Obteniendo el informe del Agente Analizador directamente ---")
        try:
            analyzer_report_content = generate_technical_seo_report()
            print("Informe del analizador obtenido exitosamente.")
        except FileNotFoundError as e:
            print(f"Error: {e}")
            print("Asegúrate de que el archivo JSON de resultados exista para que el analizador pueda generar el informe.")
            return None # Retorna None si no se puede obtener el informe del analizador
        except Exception as e:
            print(f"Ocurrió un error inesperado al obtener el informe del analizador: {e}")
            return None

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
        
        # Eliminado: os.makedirs(REPORTS_DIR, exist_ok=True)
        # Eliminado: with open(strategic_plan_file_path, 'w', encoding='utf-8') as f: f.write(strategic_plan_content)

        print(f"\n🏆 Plan de Acción Estratégico SEO Generado y almacenado en la variable 'strategic_plan_content'.")
        print("--------------------------------------------------")
       

        return strategic_plan_content

# Ejecutar directamente cuando el script se ejecuta
if __name__ == "__main__":
    strategist = SEOStrategist()
    strategic_plan = strategist.generate_strategic_plan()
    
    if strategic_plan:
        print("\n--- Contenido del plan estratégico (primeras 500 caracteres) ---")
        print(strategic_plan[:500] + "..." if len(strategic_plan) > 500 else strategic_plan)
        print("\n--- Fin del contenido del plan estratégico ---")
    else:
        print("No se pudo generar el plan estratégico.")

