#!/usr/bin/env python3
"""
MTProto Proxies Aggregator
Собирает прокси из нескольких источников и генерирует файлы в разных форматах.
"""

import requests
import re
from urllib.parse import urlparse, parse_qs

# ===== Константы =====
CHANNEL = 'mtp4tg'
UPSTREAM_URL = 'https://raw.githubusercontent.com/SoliSpirit/mtproto/master/all_proxies.txt'
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
TIMEOUT = 15  # Таймаут запросов в секундах


def is_valid_proxy(proxy):
    """
    Проверяет корректность данных прокси.
    
    Args:
        proxy (dict): Словарь с ключами 'server', 'port', 'secret'
    
    Returns:
        bool: True если прокси валиден, иначе False
    """
    server = proxy.get('server', '')
    port = proxy.get('port', '')
    secret = proxy.get('secret', '')
    
    # Проверка сервера (домен или IP)
    if not server or len(server) > 255:
        return False
    
    # Проверка порта (должен быть числом от 1 до 65535)
    try:
        port_num = int(port)
        if port_num < 1 or port_num > 65535:
            return False
    except (ValueError, TypeError):
        return False
    
    # Проверка secret (может быть разной длины, обычно начинается с ee)
    if not secret or len(secret) < 8 or len(secret) > 100:
        return False
    
    # Проверяем, что это hex или base64 строка
    try:
        int(secret, 16)  # Пробуем как hex
    except (ValueError, TypeError):
        # Если не hex, проверяем как base64 или просто валидная строка
        import re
        if not re.match(r'^[a-zA-Z0-9+/=]+$', secret):
            return False
    
    return True


def collect_from_mtp4tg():
    """
    Собирает прокси из Telegram-канала @mtp4tg.
    Использует dict для эффективной проверки дубликатов O(1).
    
    Returns:
        list: Список словарей с данными прокси
    """
    url = f'https://t.me/s/{CHANNEL}'
    print(f'📡 Парсим @{CHANNEL}...')
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        
        if response.status_code != 200:
            print(f' ⚠️ Статус код: {response.status_code}')
            return []
        
        html = response.text
        proxies = {}  # Используем dict вместо list для O(1) проверки дубликатов
        
        # Паттерн 1: Парсинг из форматированного текста
        # Ищем блоки вида: **Server:** `1.2.3.4` ... **Port:** `443` ... **Secret:** `abc123`
        pattern = re.compile(
            r'\*\*Server:\*\*\s*`([^<]+)`.*?'
            r'\*\*Port:\*\*\s*`([^<]+)`.*?'
            r'\*\*Secret:\*\*\s*`([^<]+)`',
            re.DOTALL
        )
        
        for server, port, secret in pattern.findall(html):
            server = server.strip()
            port = port.strip()
            secret = secret.strip()
            
            proxy = {
                'server': server,
                'port': port,
                'secret': secret,
                'source': f'@{CHANNEL}'
            }
            
            if is_valid_proxy(proxy):
                key = f"{server}:{port}:{secret}"
                if key not in proxies:
                    proxies[key] = proxy
        
        # Паттерн 2: Парсинг из прямых ссылок t.me/proxy?...
        href_pattern = re.compile(r'href="(https://t.me/proxy\?[^"]+)"')
        
        for href in href_pattern.findall(html):
            parsed = urlparse(href)
            params = parse_qs(parsed.query)
            
            if 'server' in params and 'port' in params and 'secret' in params:
                server = params['server'][0]
                port = params['port'][0]
                secret = params['secret'][0]
                
                proxy = {
                    'server': server,
                    'port': port,
                    'secret': secret,
                    'source': f'@{CHANNEL}'
                }
                
                if is_valid_proxy(proxy):
                    key = f"{server}:{port}:{secret}"
                    if key not in proxies:
                        proxies[key] = proxy
        
        proxy_list = list(proxies.values())
        print(f' ✅ Найдено: {len(proxy_list)} прокси')
        return proxy_list
    
    except requests.exceptions.Timeout:
        print(f' ❌ Таймаут при запросе к @{CHANNEL}')
        return []
    except requests.exceptions.RequestException as e:
        print(f' ❌ Ошибка сети: {e}')
        return []
    except Exception as e:
        print(f' ❌ Неизвестная ошибка: {e}')
        return []


def collect_from_upstream():
    """
    Собирает проверенные прокси из SoliSpirit/mtproto.
    Поддерживает оба формата: tg://proxy и https://t.me/proxy
    
    Returns:
        list: Список словарей с данными прокси
    """
    print(f'📡 Загружаем upstream: SoliSpirit/mtproto...')
    
    try:
        response = requests.get(UPSTREAM_URL, headers=HEADERS, timeout=TIMEOUT)
        
        if response.status_code != 200:
            print(f' ⚠️ Статус код: {response.status_code}')
            return []
        
        proxies = []
        lines = response.text.strip().split('\n')
        
        print(f'  Всего строк в файле: {len(lines)}')
        
        for line in lines:
            line = line.strip()
            
            # Проверяем оба формата: tg:// и https://t.me/
            if line.startswith('tg://proxy?') or line.startswith('https://t.me/proxy?'):
                parsed = urlparse(line)
                params = parse_qs(parsed.query)
                
                if 'server' in params and 'port' in params and 'secret' in params:
                    proxy = {
                        'server': params['server'][0],
                        'port': params['port'][0],
                        'secret': params['secret'][0],
                        'source': 'SoliSpirit (verified)'
                    }
                    
                    if is_valid_proxy(proxy):
                        proxies.append(proxy)
        
        print(f' ✅ Загружено: {len(proxies)} проверенных прокси')
        
        # Показываем, сколько отфильтровано валидацией
        valid_count = len(proxies)
        total_count = len([l for l in lines if l.strip().startswith(('tg://proxy?', 'https://t.me/proxy?'))])
        if total_count > 0:
            filtered = total_count - valid_count
            if filtered > 0:
                print(f' ℹ️ Отфильтровано невалидных: {filtered}')
        
        return proxies
    
    except requests.exceptions.Timeout:
        print(f' ❌ Таймаут при загрузке upstream')
        return []
    except requests.exceptions.RequestException as e:
        print(f' ❌ Ошибка сети: {e}')
        return []
    except Exception as e:
        print(f' ❌ Неизвестная ошибка: {e}')
        import traceback
        traceback.print_exc()
        return []


def merge_proxies(proxies_list):
    """
    Объединяет списки прокси, удаляя дубликаты.
    Приоритет отдаётся прокси из SoliSpirit (verified).
    
    Args:
        proxies_list (list): Список всех прокси
    
    Returns:
        list: Список уникальных прокси
    """
    merged = {}
    
    for proxy in proxies_list:
        key = f"{proxy['server']}:{proxy['port']}:{proxy['secret']}"
        
        if key not in merged:
            merged[key] = proxy
        elif 'SoliSpirit' in proxy['source']:
            # Приоритет verified прокси
            merged[key] = proxy
    
    return list(merged.values())


def generate_files(proxies):
    """
    Генерирует файлы all_proxies.txt, all_proxies.md, all_proxies.html
    
    Args:
        proxies (list): Список прокси
    """
    # Считаем статистику
    stats = {}
    for p in proxies:
        stats[p['source']] = stats.get(p['source'], 0) + 1
    
    print(f'\n📊 Статистика:')
    for source, count in stats.items():
        print(f'  {source}: {count}')
    print(f'  Всего уникальных: {len(proxies)}')
    
    # ===== Генерация TXT =====
    txt_lines = [
        f"tg://proxy?server={p['server']}&port={p['port']}&secret={p['secret']}"
        for p in proxies
    ]
    
    with open('all_proxies.txt', 'w', encoding='utf-8') as f:
        f.write('\n'.join(txt_lines))
    
    # ===== Генерация Markdown =====
    md = [
        '# 🌐 MTProto Proxies\n\n',
        f'**Всего прокси:** {len(proxies)}\n\n',
        '**Источники:**\n'
    ]
    
    for source, count in stats.items():
        md.append(f'- {source}: {count}\n')
    
    md.append('\n---\n\n')
    md.append('| # | Сервер | Порт | Источник | Ссылка |\n')
    md.append('|---|--------|------|----------|--------|\n')
    
    for i, p in enumerate(proxies, 1):
        tme = f"https://t.me/proxy?server={p['server']}&port={p['port']}&secret={p['secret']}"
        md.append(f"| {i} | `{p['server']}` | `{p['port']}` | {p['source']} | [Open]({tme}) |\n")
    
    with open('all_proxies.md', 'w', encoding='utf-8') as f:
        f.write(''.join(md))
    
    # ===== Генерация HTML =====
    html = [
        '<!DOCTYPE html>\n',
        '<html lang="ru">\n',
        '<head>\n',
        '  <meta charset="UTF-8">\n',
        '  <meta name="viewport" content="width=device-width, initial-scale=1.0">\n',
        '  <title>MTProto Proxies</title>\n',
        '  <style>\n',
        '    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; ',
        'max-width: 800px; margin: 0 auto; padding: 20px; background: #f5f5f5; }\n',
        '    h1 { color: #333; }\n',
        '    .stats { background: #fff; padding: 15px; border-radius: 8px; margin-bottom: 20px; }\n',
        '    .proxy-btn { display: block; width: 100%; padding: 12px; margin: 8px 0; ',
        'background: #0088cc; color: white; text-decoration: none; border-radius: 6px; ',
        'text-align: center; transition: background 0.2s; }\n',
        '    .proxy-btn:hover { background: #006aa3; }\n',
        '    .verified { background: #28a745; }\n',
        '    .verified:hover { background: #218838; }\n',
        '  </style>\n',
        '</head>\n',
        '<body>\n',
        '  <h1>🌐 MTProto Proxies</h1>\n'
    ]
    
    html.append(f'  <div class="stats">\n')
    html.append(f'    <strong>Всего:</strong> {len(proxies)} прокси<br>\n')
    html.append(f'    <h3>📊 Статистика:</h3>\n')
    
    for source, count in stats.items():
        if 'SoliSpirit' in source:
            html.append(f'    ✓ {source}: {count}<br>\n')
        else:
            html.append(f'    {source}: {count}<br>\n')
    
    html.append(f'  </div>\n')
    
    for p in proxies:
        tg = f"tg://proxy?server={p['server']}&port={p['port']}&secret={p['secret']}"
        label = f"🔌 {p['server']}:{p['port']}"
        css_class = 'proxy-btn verified' if 'SoliSpirit' in p['source'] else 'proxy-btn'
        
        if 'SoliSpirit' in p['source']:
            label += ' ✓'
        
        html.append(f'  <a href="{tg}" class="{css_class}">{label}</a>\n')
    
    html.append('</body>\n</html>')
    
    with open('all_proxies.html', 'w', encoding='utf-8') as f:
        f.write(''.join(html))
    
    print(f'\n📁 Создано: all_proxies.txt, all_proxies.md, all_proxies.html')


def main():
    """Основная функция запуска агрегатора."""
    print('🚀 Запуск агрегатора MTProto прокси\n')
    
    mtp4tg_proxies = collect_from_mtp4tg()
    upstream_proxies = collect_from_upstream()
    
    all_proxies = mtp4tg_proxies + upstream_proxies
    merged = merge_proxies(all_proxies)
    
    if not merged:
        print('\n❌ Прокси не найдены! Файлы не будут обновлены.')
        return
    
    generate_files(merged)
    print('\n✅ Готово!')


if __name__ == '__main__':
    main()