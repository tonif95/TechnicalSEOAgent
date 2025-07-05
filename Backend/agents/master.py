import subprocess
import sys
import os

# --- Configuración ---
# Define la ruta al script 'crawler.py'.
# Ajusta esta ruta si 'crawler.py' no está en el mismo directorio que 'master.py'.
CRAWLER_SCRIPT_PATH = os.path.join(os.path.dirname(__file__), 'crawler.py') # Asume que crawler.py está en el mismo directorio

# Añade el directorio actual al sys.path para permitir importaciones locales
# Esto es útil si 'strategist.py' y 'seo_utils.py' están en el mismo directorio que 'master.py'
sys.path.append(os.path.dirname(__file__))

try:
    from strategist import SEOStrategist
except ImportError as e:
    print(f"Error al importar la clase SEOStrategist de strategist.py: {e}")
    print("Asegúrate de que 'strategist.py' esté en el mismo directorio o en el PYTHONPATH.")
    sys.exit(1)

def run_full_seo_process():
    """
    Orquesta el proceso completo de SEO: rastreo y generación de plan estratégico.
    """
    # 1. Solicitar la URL al usuario
    target_url = input("Por favor, introduce la URL principal que deseas rastrear (ej: https://www.python.org): ")

    if not target_url:
        print("No se proporcionó ninguna URL. Saliendo.")
        sys.exit(0) # Salida limpia si no hay URL

    # 2. Ejecutar crawler.py
    print(f"\n🚀 Iniciando la ejecución de {CRAWLER_SCRIPT_PATH} con la URL: {target_url}...")

    if not os.path.exists(CRAWLER_SCRIPT_PATH):
        print(f"Error: No se encontró el archivo '{CRAWLER_SCRIPT_PATH}'.")
        print("Asegúrate de que la ruta al script 'crawler.py' sea correcta.")
        sys.exit(1)

    try:
        # Ejecutar crawler.py pasando la URL como un argumento de línea de comandos
        crawler_result = subprocess.run(
            [sys.executable, CRAWLER_SCRIPT_PATH, target_url], # Pasa target_url como argumento
            capture_output=True,  # Captura stdout y stderr
            text=True,            # Decodifica la salida como texto
            check=True            # Lanza una CalledProcessError si el comando devuelve un código de salida distinto de cero
        )
        print("\n--- Salida de crawler.py (stdout) ---")
        print(crawler_result.stdout)
        if crawler_result.stderr:
            print("\n--- Errores de crawler.py (stderr) ---")
            print(crawler_result.stderr)
        print("✅ Ejecución de crawler.py finalizada exitosamente.")

        # 3. Una vez que crawler.py ha terminado exitosamente, instanciar y ejecutar el estratega
        print("\n--- Iniciando la generación del plan estratégico SEO ---")
        strategist_instance = SEOStrategist()
        strategic_plan = strategist_instance.generate_strategic_plan()
        
        if strategic_plan:
            print("\n--- Plan Estratégico SEO Final ---")
            print(strategic_plan)
            print("\n--- Fin del Plan Estratégico SEO ---")
        else:
            print("❌ No se pudo generar el plan estratégico SEO.")

    except subprocess.CalledProcessError as e:
        print(f"❌ Error al ejecutar crawler.py: El script terminó con un error (código de salida {e.returncode}).")
        print(f"Salida estándar:\n{e.stdout}")
        print(f"Salida de error:\n{e.stderr}")
    except FileNotFoundError:
        print(f"❌ Error: El comando '{sys.executable}' (intérprete de Python) no se encontró.")
        print("Asegúrate de que Python esté correctamente instalado y accesible en tu PATH.")
    except Exception as e:
        print(f"❌ Ocurrió un error inesperado durante el proceso: {e}")

if __name__ == "__main__":
    run_full_seo_process()
    print("\nProceso de master.py finalizado.")
