import os
import subprocess
import time

# --- Constantes ---
# Rutas a los scripts de los agentes. Asegúrate de que estas rutas son correctas
# con respecto a donde ejecutarás master.py
CRAWLER_SCRIPT_PATH = "crawler.py"
ANALYZER_SCRIPT_PATH = "analyzer.py" # O "analyzer_agent.py" si lo renombraste
STRATEGIST_SCRIPT_PATH = "strategist.py" # O "strategist_agent.py" si lo renombraste

# Directorios para los resultados y los informes
# Estos directorios deberían ser manejados por los scripts individuales,
# pero los mantenemos aquí para mensajes informativos.
RESULTS_DIR = "resultados"
REPORTS_DIR = "informes"

# --- Función de Orquestación del Agente Maestro ---
def run_full_seo_pipeline():
    """
    Orquesta la ejecución secuencial del Agente Crawler, Agente Analizador y Agente Estratega
    llamando a sus scripts individuales.
    """
    print("\n=======================================================")
    print("🚀 Agente Maestro: Iniciando la Orquestación Completa del SEO")
    print("=======================================================\n")

    try:
        # Paso opcional: Asegurarse de que los directorios de salida existan,
        # aunque los scripts individuales también deberían manejarlos.
        os.makedirs(RESULTS_DIR, exist_ok=True)
        os.makedirs(REPORTS_DIR, exist_ok=True)
        print(f"Master Agent: Carpetas '{RESULTS_DIR}' y '{REPORTS_DIR}' aseguradas.")

        # --- FASE 1: Ejecutar el Agente Crawler ---
        print(f"\n--- Agente Maestro: Paso 1/3 - Ejecutando Agente Crawler ({CRAWLER_SCRIPT_PATH}) ---")
        try:
            # Ejecuta el script del crawler. `check=True` lanzará un error si el script falla.
            subprocess.run(["python", CRAWLER_SCRIPT_PATH], check=True, text=True, capture_output=True, encoding='utf-8')
            print("Master Agent: Agente Crawler completado con éxito. Resultados generados en 'resultados/'.")
        except FileNotFoundError:
            print(f"¡Error! No se encontró el script del crawler en '{CRAWLER_SCRIPT_PATH}'. "
                  "Asegúrate de que la ruta sea correcta y el archivo exista.")
            raise
        except subprocess.CalledProcessError as e:
            print(f"¡Error! El Agente Crawler falló con código de salida {e.returncode}.")
            print(f"Salida estándar del Crawler:\n{e.stdout}")
            print(f"Salida de error del Crawler:\n{e.stderr}")
            raise
        
        time.sleep(1) # Pequeña pausa para mejor legibilidad en la consola

        # --- FASE 2: Ejecutar el Agente Analizador ---
        print(f"\n--- Agente Maestro: Paso 2/3 - Ejecutando Agente Analizador ({ANALYZER_SCRIPT_PATH}) ---")
        try:
            # Ejecuta el script del analizador.
            subprocess.run(["python", ANALYZER_SCRIPT_PATH], check=True, text=True, capture_output=True, encoding='utf-8')
            print("Master Agent: Agente Analizador completado con éxito. Informe guardado en 'informes/'.")
        except FileNotFoundError:
            print(f"¡Error! No se encontró el script del analizador en '{ANALYZER_SCRIPT_PATH}'. "
                  "Asegúrate de que la ruta sea correcta y el archivo exista.")
            raise
        except subprocess.CalledProcessError as e:
            print(f"¡Error! El Agente Analizador falló con código de salida {e.returncode}.")
            print(f"Salida estándar del Analizador:\n{e.stdout}")
            print(f"Salida de error del Analizador:\n{e.stderr}")
            raise

        time.sleep(1) # Pequeña pausa

        # --- FASE 3: Ejecutar el Agente Estratega ---
        print(f"\n--- Agente Maestro: Paso 3/3 - Ejecutando Agente Estratega ({STRATEGIST_SCRIPT_PATH}) ---")
        try:
            # Ejecuta el script del estratega.
            subprocess.run(["python", STRATEGIST_SCRIPT_PATH], check=True, text=True, capture_output=True, encoding='utf-8')
            print("Master Agent: Agente Estratega completado con éxito. Plan guardado en 'informes/'.")
        except FileNotFoundError:
            print(f"¡Error! No se encontró el script del estratega en '{STRATEGIST_SCRIPT_PATH}'. "
                  "Asegúrate de que la ruta sea correcta y el archivo exista.")
            raise
        except subprocess.CalledProcessError as e:
            print(f"¡Error! El Agente Estratega falló con código de salida {e.returncode}.")
            print(f"Salida estándar del Estratega:\n{e.stdout}")
            print(f"Salida de error del Estratega:\n{e.stderr}")
            raise

        print("\n=======================================================")
        print("✅ Agente Maestro: Proceso Completo de SEO Finalizado con Éxito.")
        print(f"Revisa las carpetas '{RESULTS_DIR}' e '{REPORTS_DIR}' para los outputs.")
        print("=======================================================\n")

    except Exception as e:
        print(f"\n❌ Agente Maestro: ¡Ha ocurrido un error inesperado durante la orquestación!")
        print(f"Detalles: {e}")
        # import traceback; traceback.print_exc() # Descomentar para depuración
        print("\nEl proceso ha sido interrumpido.")

# --- Punto de Entrada del Agente Maestro ---
if __name__ == "__main__":
    run_full_seo_pipeline()


