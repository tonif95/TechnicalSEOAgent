import requests
from bs4 import BeautifulSoup
import os
import re
from urllib.parse import urlparse, urljoin
import json
import time
import sys
# import sqlite3 # Ya no necesitamos sqlite3 directamente

# --- NUEVAS IMPORTACIONES PARA SQLAlchemy y PostgreSQL ---
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import func # Para CURRENT_TIMESTAMP
# --- FIN NUEVAS IMPORTACIONES ---

# Configuración de PYTHONPATH para asegurar que se puedan importar módulos locales
project_root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root_dir not in sys.path:
    sys.path.insert(0, project_root_dir)

# Nombre de la base de datos SQLite (ya no se usa directamente, pero se mantiene la referencia)
# DB_NAME = "crawler_results.db" # Esta constante ya no es relevante para PostgreSQL

# --- Configuración de SQLAlchemy ---
# La URL de la base de datos se obtendrá de una variable de entorno en master.py
DATABASE_URL = os.getenv("DATABASE_URL") # Esto se leerá desde el entorno de Render

# Ajuste para Render: si la URL de la DB empieza con 'postgres://', cámbiala a 'postgresql://'
# Esto es un requisito común de SQLAlchemy para URLs de Render/Heroku
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
        raise # Propagar el error para que el lifespan lo capture

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

def get_html_and_parse(url, base_domain): # Eliminados processed_urls y max_pages_to_crawl
    """
    Dada una URL, obtiene el código HTML y lo parsea usando BeautifulSoup.
    Retorna el objeto BeautifulSoup, el HTML original, el HTML prettificado y una lista de enlaces internos.
    """
    # Las comprobaciones de processed_urls y max_pages_to_crawl se manejan en main.py
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
            
            if parsed_full_url.netloc == base_domain and not parsed_full_url.path.lower().endswith(('.pdf', '.zip', '.rar', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.jpg', '.jpeg', '.png', '.gif', '.svg')):
                clean_url = urljoin(full_url, parsed_full_url.path)
                if parsed_full_url.query:
                    clean_url += "?" + parsed_full_url.query
                
                found_internal_links.append(clean_url)

        print("Enlaces internos encontrados para rastreo posterior.")
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

    print("\n--- ¡Iniciando análisis detallado del HTML! ---")

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
            if 'width=device-width' in content and 'initial-scale' in content:
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
    
    default_sitemap_xml = urljoin(base_url_for_robots, '/sitemap.xml')
    if default_sitemap_xml not in analysis_results["sitemap_links"]:
        analysis_results["sitemap_links"].append(default_sitemap_xml + " (Default check)")

    return analysis_results


# El bloque if __name__ == "__main__": no es relevante para la ejecución de FastAPI en Render
# ya que Uvicorn lo ejecuta directamente. Solo es para pruebas locales de crawler.py
if __name__ == "__main__":
    # setup_database() # Esto se llama desde lifespan en master.py

    if len(sys.argv) > 1:
        target_url = sys.argv[1]
    else:
        print("Error: No se proporcionó ninguna URL. Uso: python crawler.py <URL>")
        sys.exit(1)

    MAX_PAGES = 20

    parsed_target_url = urlparse(target_url)
    base_domain = parsed_target_url.netloc

    urls_to_crawl = [target_url]
    processed_urls = set()
    
    while urls_to_crawl and len(processed_urls) < MAX_PAGES:
        current_url = urls_to_crawl.pop(0)

        # Aquí necesitas pasar la sesión de la base de datos si quieres interactuar
        # con ella en este bloque de prueba.
        # Para el propósito de este ejemplo, asumimos que save_to_database
        # maneja su propia sesión.
        soup, original_html_content, prettified_html_content, found_links = \
            get_html_and_parse(current_url, base_domain) # Eliminados processed_urls y MAX_PAGES
        
        if soup:
            analysis_results = analyze_html_content(current_url, soup)
            if analysis_results:
                # Guardar en la base de datos
                # save_to_database(current_url, original_html_content, prettified_html_content, analysis_results)
                print(f"Análisis y guardado en DB completado para: {current_url} (simulado para pruebas locales)")

            for link in found_links:
                if link not in processed_urls and urlparse(link).netloc == base_domain:
                    if len(processed_urls) < MAX_PAGES:
                        urls_to_crawl.append(link)
                    else:
                        break

        time.sleep(1)

    print("\nRastreo completado. Todos los resultados han sido guardados en la base de datos (simulado para pruebas locales).")
    # print(f"Puedes inspeccionar la base de datos '{DB_NAME}' usando una herramienta de SQLite.")