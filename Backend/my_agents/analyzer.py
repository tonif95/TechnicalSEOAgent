import os
import json
# Importaciones de SQLAlchemy necesarias para crear el motor y la sesión en este proceso
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import func # Para CURRENT_TIMESTAMP

# Define la Base y el modelo CrawledPage dentro de este módulo también.
# Esto es necesario porque cada proceso necesita su propia "Base" ligada a su propio motor.
Base = declarative_base()

class CrawledPage(Base):
    __tablename__ = 'crawled_pages' # Asegúrate de que el nombre de la tabla coincida con crawler.py

    id = Column(Integer, primary_key=True, autoincrement=True)
    url = Column(String, unique=True, nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    original_html = Column(Text)
    prettified_html = Column(Text)
    analysis_results = Column(JSON)

    def __repr__(self):
        return f"<CrawledPage(url='{self.url}')>"

# Modificamos la función para que acepte database_url como un argumento
def _generate_report_in_process(result_queue, openai_api_key, database_url):
    """
    Función que se ejecuta en un proceso separado para generar el informe.
    Inicializa su propia conexión a la base de datos.
    """
    try:
        print(f"PROCESO_ANALYZER - INFO: Iniciando generación de informe en proceso separado.")
        
        # --- INICIALIZAR LA CONEXIÓN A LA BASE DE DATOS EN ESTE PROCESO HIJO ---
        # Asegúrate de que la URL de la DB sea 'postgresql://' si viene como 'postgres://'
        if database_url and database_url.startswith("postgres://"):
            database_url = database_url.replace("postgres://", "postgresql://", 1)
        
        # Crear un nuevo motor y una nueva sesión para este proceso
        engine = create_engine(database_url)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        
        # Opcional: Asegurarse de que las tablas existan (aunque el lifespan de FastAPI ya lo hace)
        # Base.metadata.create_all(bind=engine) 
        print(f"PROCESO_ANALYZER - INFO: Conexión a la base de datos establecida en el proceso hijo.")

        db = SessionLocal()
        try:
            # Cargar todos los resultados de análisis de la base de datos
            analysis_data = []
            results = db.query(CrawledPage).all()
            for page in results:
                # Solo incluir los datos relevantes para el análisis
                analysis_data.append({
                    "url": page.url,
                    "analysis_results": page.analysis_results
                })
            
            print(f"PROCESO_ANALYZER - INFO: Datos de {len(analysis_data)} páginas cargados de la DB.")

            # --- Lógica de generación de informe con OpenAI ---
            # Aquí es donde integrarías la llamada a la API de OpenAI
            # Ejemplo (necesitarías 'openai' instalado y configurado):
            # from openai import OpenAI
            # client = OpenAI(api_key=openai_api_key)
            # prompt = f"Genera un informe SEO detallado basado en los siguientes datos de análisis: {json.dumps(analysis_data, indent=2)}. Destaca los puntos clave y recomendaciones."
            # chat_completion = client.chat.completions.create(
            #     messages=[
            #         {"role": "user", "content": prompt}
            #     ],
            #     model="gpt-4o", # Puedes cambiar el modelo según tu preferencia
            #     temperature=0.7,
            #     max_tokens=2000
            # )
            # report_content = chat_completion.choices[0].message.content
            
            # --- Placeholder para la generación real del informe ---
            # Reemplaza esto con tu llamada real a la API de OpenAI
            report_content = f"INFORME SEO GENERADO POR IA:\n\n"
            report_content += f"Basado en {len(analysis_data)} páginas rastreadas.\n"
            report_content += f"Clave API usada (parcial): {openai_api_key[:5]}...{openai_api_key[-5:]}\n\n"
            report_content += "--- Datos de Análisis Cargados ---\n"
            for item in analysis_data[:3]: # Mostrar solo los primeros 3 para no saturar el informe de prueba
                report_content += f"URL: {item['url']}\n"
                report_content += f"Resultados Parciales: {json.dumps(item['analysis_results'], indent=2)[:200]}...\n\n"
            report_content += "\n--- Fin de Datos de Análisis ---\n"
            report_content += "\n[Aquí iría el informe detallado generado por la IA de OpenAI]"
            # --- FIN Placeholder ---

            print(f"PROCESO_ANALYZER - INFO: Informe generado exitosamente.")
            result_queue.put(report_content)

        except Exception as db_error:
            db.rollback() # Asegurarse de hacer rollback en caso de error de DB
            print(f"PROCESO_ANALYZER - ERROR: Fallo en la generación del informe: Error de base de datos al cargar resultados: {db_error}")
            result_queue.put({"error": f"Error de base de datos al cargar resultados: {db_error}"})
        finally:
            db.close() # Asegurarse de cerrar la sesión de DB

    except Exception as e:
        print(f"PROCESO_ANALYZER - ERROR: Error inesperado en _generate_report_in_process: {e}")
        import traceback
        traceback.print_exc()
        result_queue.put({"error": f"Error inesperado en el proceso de generación de informe: {e}"})