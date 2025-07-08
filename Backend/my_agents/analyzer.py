import os
import json
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import func

# Importar la librería de OpenAI
from openai import OpenAI

# Define la Base y el modelo CrawledPage dentro de este módulo también.
Base = declarative_base()

class CrawledPage(Base):
    __tablename__ = 'crawled_pages'

    id = Column(Integer, primary_key=True, autoincrement=True)
    url = Column(String, unique=True, nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    original_html = Column(Text)
    prettified_html = Column(Text)
    analysis_results = Column(JSON)

    def __repr__(self):
        return f"<CrawledPage(url='{self.url}')>"

def _generate_report_in_process(result_queue, openai_api_key, database_url):
    """
    Función que se ejecuta en un proceso separado para generar el informe.
    Inicializa su propia conexión a la base de datos y llama a la API de OpenAI.
    """
    try:
        print(f"PROCESO_ANALYZER - INFO: Iniciando generación de informe en proceso separado.")
        
        # Inicializar la conexión a la base de datos en este proceso hijo
        if database_url and database_url.startswith("postgres://"):
            database_url = database_url.replace("postgres://", "postgresql://", 1)
        
        engine = create_engine(database_url)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        
        print(f"PROCESO_ANALYZER - INFO: Conexión a la base de datos establecida en el proceso hijo.")

        db = SessionLocal()
        try:
            # Cargar todos los resultados de análisis de la base de datos
            analysis_data = []
            results = db.query(CrawledPage).all()
            for page in results:
                analysis_data.append({
                    "url": page.url,
                    "analysis_results": page.analysis_results
                })
            
            print(f"PROCESO_ANALYZER - INFO: Datos de {len(analysis_data)} páginas cargados de la DB.")

            if not analysis_data:
                report_content = "No se encontraron datos de rastreo para generar el informe."
                print("PROCESO_ANALYZER - WARNING: No hay datos de análisis para generar el informe.")
                result_queue.put(report_content)
                return

            # Inicializar el cliente de OpenAI con la clave API proporcionada
            client = OpenAI(api_key=openai_api_key)

            # Preparar el prompt para la IA
            # Es importante ser específico en el prompt para obtener un buen informe SEO
            prompt = f"""
            Genera un informe SEO técnico detallado y actionable basado en los siguientes datos de análisis de páginas web.
            El informe debe ser claro, conciso y estructurado, incluyendo:

            1.  **Resumen Ejecutivo:** Un breve párrafo con los hallazgos más importantes.
            2.  **Análisis por Página:** Para cada URL proporcionada, destaca los puntos fuertes y las áreas de mejora.
                Incluye:
                -   Título (title)
                -   Meta Description
                -   Etiquetas H1, H2 (si hay problemas de duplicidad o ausencia)
                -   Enlaces internos y externos (conteo y posibles problemas)
                -   Imágenes (conteo, imágenes sin alt, lazy loading)
                -   Uso de JavaScript (inline vs. externo, noscript)
                -   Datos Estructurados (JSON-LD)
                -   Atributos WAI-ARIA (si se encuentran)
                -   Compatibilidad móvil (viewport meta tag)
                -   Estado HTTP y URL final tras redirecciones
            3.  **Recomendaciones Generales:** Sugerencias prácticas y priorizadas para mejorar el SEO técnico del sitio web en general, basadas en patrones observados en los datos.
            4.  **Consideraciones Adicionales:** Cualquier otra observación relevante (robots.txt, sitemaps, etc.).

            Los datos de análisis son los siguientes (formato JSON):
            {json.dumps(analysis_data, indent=2)}

            Asegúrate de que el informe sea fácil de leer y entender para un profesional de SEO o un desarrollador web.
            """

            print("PROCESO_ANALYZER - INFO: Enviando solicitud a la API de OpenAI...")
            chat_completion = client.chat.completions.create(
                messages=[
                    {"role": "system", "content": "Eres un experto en SEO técnico y generas informes detallados y accionables."},
                    {"role": "user", "content": prompt}
                ],
                model="gpt-4o", # Puedes cambiar el modelo si lo deseas, gpt-4o es bueno para esto
                temperature=0.7, # Un poco más creativo para el informe
                max_tokens=3000 # Aumentar los tokens para un informe más completo
            )
            report_content = chat_completion.choices[0].message.content
            
            print(f"PROCESO_ANALYZER - INFO: Informe generado exitosamente por OpenAI.")
            result_queue.put(report_content)

        except Exception as db_error:
            db.rollback()
            print(f"PROCESO_ANALYZER - ERROR: Fallo en la generación del informe: Error de base de datos al cargar resultados: {db_error}")
            result_queue.put({"error": f"Error de base de datos al cargar resultados: {db_error}"})
        finally:
            db.close()

    except Exception as e:
        print(f"PROCESO_ANALYZER - ERROR: Error inesperado en _generate_report_in_process: {e}")
        import traceback
        traceback.print_exc()
        result_queue.put({"error": f"Error inesperado en el proceso de generación de informe: {e}"})