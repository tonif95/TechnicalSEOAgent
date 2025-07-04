import requests
from bs4 import BeautifulSoup
import os
import re
from urllib.parse import urlparse, urljoin
import json
import time # Importar para añadir un pequeño retraso entre solicitudes

# Directorio donde se guardarán los resultados
RESULTS_DIR = "resultados"

def create_results_directory():
    """Crea el directorio de resultados si no existe."""
    if not os.path.exists(RESULTS_DIR):
        os.makedirs(RESULTS_DIR)
        print(f"Directorio '{RESULTS_DIR}' creado.")

def get_html_and_parse(url, base_domain, processed_urls, max_pages_to_crawl):
    """
    Dada una URL, obtiene el código HTML y lo parsea usando BeautifulSoup.
    Guarda el HTML original y el HTML parseado/prettificado en la carpeta 'resultados'.

    Args:
        url (str): La URL de la página web a rastrear.
        base_domain (str): El dominio base para filtrar enlaces internos.
        processed_urls (set): Conjunto de URLs ya procesadas para evitar duplicados.
        max_pages_to_crawl (int): Número máximo de páginas a rastrear.
    Returns:
        tuple: (BeautifulSoup object, list of found internal links) o (None, None) si hay un error.
    """
    if url in processed_urls:
        print(f"Saltando URL ya procesada: {url}")
        return None, []
    if len(processed_urls) >= max_pages_to_crawl:
        print(f"Alcanzado el límite de {max_pages_to_crawl} páginas para rastrear.")
        return None, []

    processed_urls.add(url) # Añadir la URL al conjunto de procesadas

    try:
        print(f"\nIntentando obtener contenido de: {url}")
        response = requests.get(url, timeout=10) # Añadir timeout para evitar esperas infinitas
        response.raise_for_status()

        html_content = response.text
        print("Contenido HTML obtenido exitosamente.")

        # Limpiar el nombre de archivo de caracteres no válidos para usarlo en el nombre del archivo
        # Asegurarse de que el nombre del archivo sea único y descriptivo
        parsed_url_for_filename = re.sub(r'[^a-zA-Z0-9_.-]', '_', urlparse(url).netloc + urlparse(url).path).strip('_')
        filename_prefix = parsed_url_for_filename[:60] if len(parsed_url_for_filename) > 60 else parsed_url_for_filename
        
        # Construir rutas completas para los archivos dentro de la carpeta 'resultados'
        original_html_filename = os.path.join(RESULTS_DIR, f"{filename_prefix}_original.html")
        prettified_html_filename = os.path.join(RESULTS_DIR, f"{filename_prefix}_parsed_prettified.html")

        # 1. Guardar el HTML original
        with open(original_html_filename, 'w', encoding='utf-8') as f:
            f.write(html_content)
        print(f"HTML original guardado en: {original_html_filename}")

        # 2. Parsear el HTML con BeautifulSoup
        soup = BeautifulSoup(html_content, 'html.parser')
        print("HTML parseado con BeautifulSoup.")

        # 3. Guardar el HTML parseado (prettificado)
        with open(prettified_html_filename, 'w', encoding='utf-8') as f:
            f.write(soup.prettify())
        print(f"HTML parseado y prettificado guardado en: {prettified_html_filename}")

        found_internal_links = []
        for a_tag in soup.find_all('a', href=True):
            href = a_tag.get('href')
            full_url = urljoin(url, href)
            parsed_full_url = urlparse(full_url)
            
            # Filtra enlaces internos y URLs que no sean de archivo
            if parsed_full_url.netloc == base_domain and not parsed_full_url.path.lower().endswith(('.pdf', '.zip', '.rar', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.jpg', '.jpeg', '.png', '.gif', '.svg')):
                # Construye una URL limpia sin fragmentos
                clean_url = urljoin(full_url, parsed_full_url.path)
                if parsed_full_url.query:
                    clean_url += "?" + parsed_full_url.query
                
                found_internal_links.append(clean_url)

        print("Enlaces internos encontrados para rastreo posterior.")
        return soup, found_internal_links

    except requests.exceptions.RequestException as e:
        print(f"Error al obtener la URL {url}: {e}")
    except Exception as e:
        print(f"Ocurrió un error inesperado al procesar {url}: {e}")
    return None, []

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
        # Estos se actualizarán a las rutas completas en el main
        "html_saved_original": "",
        "html_saved_prettified": ""
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

    base_domain_current_page = urlparse(url).netloc # Usar el dominio de la página actual para los enlaces
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

    # Actualizar las rutas de los archivos guardados en el diccionario de resultados
    filename_prefix = re.sub(r'[^a-zA-Z0-9_.-]', '_', urlparse(url).netloc + urlparse(url).path).strip('_')
    filename_prefix = filename_prefix[:60] if len(filename_prefix) > 60 else filename_prefix
    analysis_results["html_saved_original"] = os.path.join(RESULTS_DIR, f"{filename_prefix}_original.html")
    analysis_results["html_saved_prettified"] = os.path.join(RESULTS_DIR, f"{filename_prefix}_parsed_prettified.html")

    return analysis_results


if __name__ == "__main__":
    create_results_directory() # Asegurarse de que la carpeta 'resultados' exista

    target_url = input("Por favor, introduce la URL principal que deseas rastrear (ej: https://www.python.org): ")
    MAX_PAGES = 20 # Límite de páginas a rastrear

    if target_url:
        parsed_target_url = urlparse(target_url)
        base_domain = parsed_target_url.netloc

        urls_to_crawl = [target_url] # Cola de URLs a rastrear, empieza con la principal
        processed_urls = set()       # Conjunto de URLs ya procesadas
        all_analysis_results = []    # Lista para almacenar todos los resultados

        while urls_to_crawl and len(processed_urls) < MAX_PAGES:
            current_url = urls_to_crawl.pop(0) # Obtener la siguiente URL de la cola

            soup, found_links = get_html_and_parse(current_url, base_domain, processed_urls, MAX_PAGES)
            
            if soup:
                analysis_results = analyze_html_content(current_url, soup)
                if analysis_results:
                    all_analysis_results.append(analysis_results)
                    print(f"Análisis completado para: {current_url}")

                # Añadir nuevos enlaces encontrados a la cola si no han sido procesados y son del mismo dominio
                for link in found_links:
                    if link not in processed_urls and urlparse(link).netloc == base_domain:
                        if len(processed_urls) < MAX_PAGES: # Comprobar el límite antes de añadir
                            urls_to_crawl.append(link)
                        else:
                            break # Salir si se alcanzó el límite

            time.sleep(1) # Pequeño retraso para no sobrecargar el servidor (ajustar si es necesario)

        # Guardar todos los resultados de todas las páginas en un único archivo JSON
        output_filename = os.path.join(RESULTS_DIR, "all_analysis_results.json")
        try:
            with open(output_filename, 'w', encoding='utf-8') as f:
                json.dump(all_analysis_results, f, indent=4, ensure_ascii=False)
            print(f"\nResultados de análisis de {len(all_analysis_results)} páginas guardados en '{output_filename}'.")
            print("Por favor, ejecuta 'python analyzer.py' para ver el resumen de la primera página o procesar todos los resultados.")
        except Exception as e:
            print(f"Error al guardar los resultados en JSON: {e}")
    else:
        print("No se proporcionó ninguna URL. Saliendo.")