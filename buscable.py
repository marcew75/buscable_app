import requests
import re
import time
import random
from bs4 import BeautifulSoup
import streamlit as st
import pandas as pd
from concurrent.futures import ThreadPoolExecutor

# Leer la API key desde secrets.toml
API_KEY = st.secrets["API_KEY"]

# Función para realizar la búsqueda con SerpAPI
def search_google(query, api_key, num_results=10):
    search_url = "https://serpapi.com/search"
    params = {
        'q': query,
        'engine': 'google',
        'api_key': api_key,
        'num': num_results,
    }
    
    try:
        response = requests.get(search_url, params=params, timeout=10)
        response.raise_for_status()
        results = response.json().get("organic_results", [])
        return [result["link"] for result in results]
    except requests.exceptions.RequestException as e:
        st.error(f"Error en la búsqueda: {e}")
        return []

# Función para extraer correos electrónicos de una página web
def extract_emails_from_html(html):
    email_regex = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    emails = re.findall(email_regex, html)
    # Filtrar correos no válidos
    return {email for email in emails if not email.endswith(('.jpg', '.jpeg', '.png', '.gif'))}

# Función para extraer el nombre del sitio web
def extract_site_name(html):
    soup = BeautifulSoup(html, "html.parser")
    title = soup.find('title')
    return title.get_text().strip() if title else "Desconocido"

# Función para procesar una URL
def process_url(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            emails = extract_emails_from_html(response.text)
            site_name = extract_site_name(response.text)
            return [(site_name, email) for email in emails]
    except Exception as e:
        print(f"Error procesando {url}: {e}")
    return []

# Función para obtener datos de múltiples URLs en paralelo
def scrape_emails_from_urls(urls):
    results = []
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(process_url, url) for url in urls]
        for future in futures:
            results.extend(future.result() or [])
    return results

# Interfaz de usuario con Streamlit
st.title("Web Scraping de Correos Electrónicos")
query = st.text_input("Consulta de Búsqueda")
num_results = st.number_input("Número de Resultados", min_value=1, max_value=100, value=10)

if st.button("Buscar"):
    if query:
        urls = search_google(query, API_KEY, num_results)
        if urls:
            scraped_data = scrape_emails_from_urls(urls)
            if scraped_data:
                df = pd.DataFrame(scraped_data, columns=['Nombre del Sitio', 'Correo Electrónico'])
                st.write(df)
                csv = df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="Descargar correos electrónicos como CSV",
                    data=csv,
                    file_name='emails.csv',
                    mime='text/csv',
                )
                st.success("Scraping completado con éxito.")
            else:
                st.warning("No se encontraron correos electrónicos.")
        else:
            st.error("No se pudieron obtener URLs.")
    else:
        st.warning("Por favor, ingresa una consulta de búsqueda.")
