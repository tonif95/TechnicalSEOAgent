import requests
from bs4 import BeautifulSoup
import os
import re
from urllib.parse import urlparse, urljoin
import json
import time
import sys # Se mantiene para la configuración de PYTHONPATH, pero no para argumentos de línea de comandos

# --- NUEVAS IMPORTACIONES PARA SQLAlchemy y PostgreSQL ---
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import func # Para CURRENT_TIMESTAMP
# --- FIN NUEVAS IMPORTACIONES ---

# Configuración de PYTHONPATH para asegurar que se puedan importar módulos locales
# Esto es importante para que FastAPI pueda encontrar los módulos correctamente en Render
project_root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root_dir not in sys.path:
    sys.path.insert(0, project_root_dir)

# --- Configuración de SQLAlchemy ---
DATABASE_URL = os.getenv("DATABASE_URL")

# Ajuste para Render: si la URL de la DB empieza con 'postgres://', cámbiala a 'postgresql://'
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Crear el motor de la base de datos
engine = create_engine(DATABASE_URL)

# Crear una clase base para los modelos declarativos
Base = declarative_base()

# Definir el modelo de la tabla crawled_pages
class CrawledPage(Base):
    __tablename__ = 'crawled_pages'

    id = Column(Integer, primary_key=True, autoincrement=True)
    url = Column(String, unique=True, nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    original_html = Column(Text)
    prettified_html = Column(Text)
    analysis_results = Column(JSON) # JSON type para PostgreSQL

    def __repr__(self):
        return f"<CrawledPage(url='{self.url}')>"

# Crear una sesión de base de datos
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def setup_database():
    """Configura la base de datos PostgreSQL y crea la tabla si no existe."""
    print("Intentando configurar la base de datos PostgreSQL...")
    try:
        Base.metadata.create_all(bind=engine)
        print("Tabla 'crawled_pages' verificada/creada en PostgreSQL.")
    except Exception as e:
        print(f"ERROR: No se pudo conectar o crear la tabla en PostgreSQL: {e}")
        raise # Propagar el error para que el lifespan lo capture (en master.py)

def save_to_database(url, original_html, prettified_html, analysis_results):
    """Guarda el HTML original, el HTML prettificado y los resultados del análisis en la base de datos."""
    db = SessionLocal()
    try:
        # Buscar si la URL ya existe
        existing_page = db.query(CrawledPage).filter(CrawledPage.url == url).first()

        if existing_page:
            # Actualizar página existente
            existing_page.timestamp = func.now()
            existing_page.original_html = original_html
            existing_page.prettified_html = prettified_html
            existing_page.analysis_results = analysis_results
            print(f"Datos de {url} actualizados exitosamente en la base de datos.")
        else:
            # Crear nueva página
            new_page = CrawledPage(
                url=url,
                original_html=original_html,
                prettified_html=prettified_html,
                analysis_results=analysis_results
            )
            db.add(new_page)
            print(f"Datos de {url} guardados exitosamente en la base de datos.")
        
        db.commit()
        db.refresh(existing_page if existing_page else new_page) # Refrescar para obtener el estado actual
    except Exception as e:
        db.rollback()
        print(f"Error al guardar los datos de {url} en la base de datos: {e}")
        raise # Re-lanzar la excepción para que el llamador pueda manejarla
    finally:
        db.close()

def get_html_and_parse(url, base_domain):
    """
    Dada una URL, obtiene el código HTML y lo parsea usando BeautifulSoup.
    Retorna el objeto BeautifulSoup, el HTML original, el HTML prettificado y una lista de enlaces internos.
    """
    try:
        print(f"\nIntentando obtener contenido de: {url}")
        response = requests.get(url, timeout=10)
        response.raise_for_status()

        html_content = response.text
        print("Contenido HTML obtenido exitosamente.")

        soup = BeautifulSoup(html_content, 'html.parser')
        prettified_html_content = soup.prettify()
        print("HTML parseado y prettificado.")

        found_internal_links = []
        for a_tag in soup.find_all('a', href=True):
            href = a_tag.get('href')
            full_url = urljoin(url, href)
            parsed_full_url = urlparse(full_url)
            
            # Filtra enlaces a otros dominios y a tipos de archivos específicos
            if parsed_full_url.netloc == base_domain and not parsed_full_url.path.lower().endswith(('.pdf', '.zip', '.rar', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.jpg', '.jpeg', '.png', '.gif', '.svg')):
                clean_url = urljoin(full_url, parsed_full_url.path)
                if parsed_full_url.query:
                    clean_url += "?" + parsed_full_url.query
                
                found_internal_links.append(clean_url)

        print(f"Se encontraron {len(found_internal_links)} enlaces internos para posible rastreo posterior.")
        return soup, html_content, prettified_html_content, found_internal_links

    except requests.exceptions.RequestException as e:
        print(f"Error al obtener la URL {url}: {e}")
    except Exception as e:
        print(f"Ocurrió un error inesperado al procesar {url}: {e}")
    return None, None, None, []

def analyze_html_content(url, parsed_soup_object):
    """
    Realiza el análisis SEO y técnico del contenido HTML.
    Retorna un diccionario con los resultados del análisis.
    """
    if not parsed_soup_object:
        print("\nNo se pudo parsear el contenido HTML. No se realizará el análisis detallado.")
        return None

    print(f"\n--- Iniciando análisis detallado del HTML para: {url} ---")

    analysis_results = {
        "url": url,
        "http_status": None,
        "final_url_after_redirects": None,
        "title": None,
        "meta_description": None,
        "meta_robots": None,
        "viewport": None,
        "canonical_url": None,
        "hreflang_tags": [],
        "h1_tags": [],
        "h2_tags": [],
        "h3_h6_tags": [],
        "internal_links_count": 0,
        "external_links_count": 0,
        "image_count": 0,
        "images_without_alt": 0,
        "lazy_loaded_images_count": 0,
        "javascript_usage_indicators": {
            "inline_scripts": 0,
            "external_scripts": 0,
            "noscript_tag_present": False
        },
        "structured_data_scripts": [],
        "wai_aria_attributes_found": 0,
        "mobile_friendly_meta_tags": False,
        "sitemap_links": [],
        "robots_txt_status": None,
        "robots_txt_content": None,
    }

    try:
        response_info = requests.get(url, allow_redirects=True, timeout=10)
        analysis_results["http_status"] = response_info.status_code
        analysis_results["final_url_after_redirects"] = response_info.url
        print(f"Estado HTTP y URL final obtenidos: {response_info.status_code}, {response_info.url}")
    except requests.exceptions.RequestException as e:
        print(f"Error al obtener información HTTP para {url}: {e}")
        analysis_results["http_status"] = "Error de red"
        analysis_results["final_url_after_redirects"] = url

    title_tag = parsed_soup_object.find('title')
    if title_tag:
        analysis_results["title"] = title_tag.get_text(strip=True)

    for meta in parsed_soup_object.find_all('meta'):
        name = meta.get('name', '').lower()
        content = meta.get('content')

        if name == 'description':
            analysis_results["meta_description"] = content
        elif name == 'robots':
            analysis_results["meta_robots"] = content
        elif name == 'viewport':
            analysis_results["viewport"] = content
            if content and 'width=device-width' in content and 'initial-scale' in content:
                analysis_results["mobile_friendly_meta_tags"] = True

    canonical_link = parsed_soup_object.find('link', rel='canonical')
    if canonical_link and canonical_link.get('href'):
        analysis_results["canonical_url"] = canonical_link.get('href')

    for link in parsed_soup_object.find_all('link', rel='alternate'):
        if link.get('hreflang') and link.get('href'):
            analysis_results["hreflang_tags"].append({
                "hreflang": link.get('hreflang'),
                "href": link.get('href')
            })

    for h1 in parsed_soup_object.find_all('h1'):
        analysis_results["h1_tags"].append(h1.get_text(strip=True))
    for h2 in parsed_soup_object.find_all('h2'):
        analysis_results["h2_tags"].append(h2.get_text(strip=True))
    for hn in parsed_soup_object.find_all(['h3', 'h4', 'h5', 'h6']):
        analysis_results["h3_h6_tags"].append({hn.name: hn.get_text(strip=True)})

    base_domain_current_page = urlparse(url).netloc
    for a_tag in parsed_soup_object.find_all('a', href=True):
        href = a_tag.get('href')
        if href:
            full_url = urljoin(url, href)
            parsed_href_domain = urlparse(full_url).netloc
            if parsed_href_domain == base_domain_current_page:
                analysis_results["internal_links_count"] += 1
            else:
                analysis_results["external_links_count"] += 1

    for img in parsed_soup_object.find_all('img'):
        analysis_results["image_count"] += 1
        if not img.get('alt'):
            analysis_results["images_without_alt"] += 1
        if img.get('loading') == 'lazy' or any(attr in img.attrs for attr in ['data-src', 'data-srcset']):
            analysis_results["lazy_loaded_images_count"] += 1

    for script in parsed_soup_object.find_all('script'):
        if script.get('src'):
            analysis_results["javascript_usage_indicators"]["external_scripts"] += 1
        else:
            analysis_results["javascript_usage_indicators"]["inline_scripts"] += 1
    if parsed_soup_object.find('noscript'):
        analysis_results["javascript_usage_indicators"]["noscript_tag_present"] = True

    for script in parsed_soup_object.find_all('script', type='application/ld+json'):
        try:
            json_data = json.loads(script.get_text(strip=True))
            analysis_results["structured_data_scripts"].append({"type": "JSON-LD", "content_preview": str(json_data)[:200] + "..."})
        except json.JSONDecodeError:
            analysis_results["structured_data_scripts"].append({"type": "JSON-LD", "error": "Invalid JSON-LD format"})

    for tag in parsed_soup_object.find_all(True):
        for attr in tag.attrs:
            if attr.startswith('aria-'):
                analysis_results["wai_aria_attributes_found"] += 1
                break

    parsed_url_obj = urlparse(url)
    base_url_for_robots = f"{parsed_url_obj.scheme}://{parsed_url_obj.netloc}"
    robots_txt_url = urljoin(base_url_for_robots, '/robots.txt')
    
    try:
        robots_response = requests.get(robots_txt_url, timeout=5)
        analysis_results["robots_txt_status"] = robots_response.status_code
        if robots_response.status_code == 200:
            analysis_results["robots_txt_content"] = robots_response.text
            for line in robots_response.text.splitlines():
                if line.lower().startswith('sitemap:'):
                    sitemap_link = line[len('sitemap:'):].strip()
                    analysis_results["sitemap_links"].append(sitemap_link)
        else:
            print(f"robots.txt no encontrado o error: {robots_response.status_code}")
    except requests.exceptions.RequestException as e:
        analysis_results["robots_txt_status"] = f"Error: {e}"
        print(f"Error al obtener robots.txt: {e}")
    
    # Se ha eliminado la adición incondicional de /sitemap.xml por defecto
    # Si la lógica de sitemap.xml debe ser diferente, se manejará en master.py o en un módulo específico de sitemap.

    return analysis_results

# El bloque if __name__ == "__main__": se elimina por completo
# ya que es solo para pruebas locales y la lógica de ejecución principal
# y el control del número de URLs se manejan en master.py (o un equivalente)
# cuando la aplicación se despliega en producción con Uvicorn/FastAPI.