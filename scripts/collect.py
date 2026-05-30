#!/usr/bin/env python3
import requests
import re
from urllib.parse import urlparse, parse_qs

CHANNEL = 'mtp4tg'
UPSTREAM_URL = 'https://raw.githubusercontent.com/SoliSpirit/mtproto/master/all_proxies.txt'
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

def collect_from_mtp4tg():
    url = f'https://t.me/s/{CHANNEL}'
    print(f'📡 Парсим @{CHANNEL}...')
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        if response.status_code != 200: return []
        html = response.text
        proxies = []
        pattern = re.compile(r'<b>Server:</b>\s*<code>([^<]+)</code>.*?<b>Port:</b>\s*<code>([^<]+)</code>.*?<b>Secret:</b>\s*<code>([^<]+)</code>', re.DOTALL)
        for server, port, secret in pattern.findall(html):
            proxies.append({'server': server, 'port': port, 'secret': secret, 'source': f'@{CHANNEL}'})
        href_pattern = re.compile(r'href="(https://t\.me/proxy\?[^"]+)"')
        for href in href_pattern.findall(html):
            parsed = urlparse(href)
            params = parse_qs(parsed.query)
            if 'server' in params and 'port' in params and 'secret' in params:
                proxy = {'server': params['server'][0], 'port': params['port'][0], 'secret': params['secret'][0], 'source': f'@{CHANNEL}'}
                if proxy not in proxies: proxies.append(proxy)
        print(f'   ✅ Найдено: {len(proxies)} прокси')
        return proxies
    except Exception as e:
        print(f'   ❌ Ошибка: {e}')
        return []

def collect_from_upstream():
    print(f'📡 Загружаем upstream: SoliSpirit/mtproto...')
    try:
        response = requests.get(UPSTREAM_URL, headers=HEADERS, timeout=15)
        if response.status_code != 200: return []
        proxies = []
        for line in response.text.strip().split('\n'):
            if line.startswith('tg://proxy?'):
                parsed = urlparse(line)
                params = parse_qs(parsed.query)
                if 'server' in params and 'port' in params and 'secret' in params:
                    proxies.append({'server': params['server'][0], 'port': params['port'][0], 'secret': params['secret'][0], 'source': 'SoliSpirit (verified)'})
        print(f'   ✅ Загружено: {len(proxies)} проверенных прокси')
        return proxies
    except Exception as e:
        print(f'   ❌ Ошибка: {e}')
        return []

def merge_proxies(proxies_list):
    merged = {}
    for proxy in proxies_list:
        key = f"{proxy['server']}:{proxy['port']}:{proxy['secret']}"
        if key not in merged: merged[key] = proxy
        elif 'SoliSpirit' in proxy['source']: merged[key] = proxy
    return list(merged.values())

def generate_files(proxies):
    stats = {}
    for p in proxies: stats[p['source']] = stats.get(p['source'], 0) + 1
    print(f'\n📊 Статистика:')
    for source, count in stats.items(): print(f'   {source}: {count}')
    print(f'   Всего уникальных: {len(proxies)}')
    
    txt_lines = [f"tg://proxy?server={p['server']}&port={p['port']}&secret={p['secret']}" for p in proxies]
    with open('all_proxies.txt', 'w', encoding='utf-8') as f: f.write('\n'.join(txt_lines))
    
    md = ['# 🌐 MTProto Proxies\n', f'**Всего прокси:** {len(proxies)}\n\n**Источники:**\n']
    for source, count in stats.items(): md.append(f'- {source}: {count}\n')
    md.append('\n---\n\n| # | Сервер | Порт | Источник | Ссылка |\n|---|--------|------|----------|--------|\n')
    for i, p in enumerate(proxies, 1):
        tme = f"https://t.me/proxy?server={p['server']}&port={p['port']}&secret={p['secret']}"
        md.append(f"| {i} | `{p['server']}` | `{p['port']}` | {p['source']} | [Open]({tme}) |\n")
    with open('all_proxies.md', 'w', encoding='utf-8') as f: f.write(''.join(md))
    
    html = ['<!DOCTYPE html>\n<html>\n<head>\n<meta charset="UTF-8">\n<title>MTProto Proxies</title>\n<style>\nbody{font-family:Arial,sans-serif;max-width:800px;margin:50px auto;padding:20px;}.proxy-btn{display:block;margin:10px 0;padding:12px 20px;background:#0088cc;color:white;text-decoration:none;border-radius:8px;font-size:14px;}.proxy-btn:hover{background:#006699;}.stats{background:#f5f5f5;padding:15px;border-radius:8px;margin-bottom:20px;}.verified{color:#28a745;font-weight:bold;}\n</style>\n</head>\n<body>\n<h1>🌐 MTProto Proxies</h1>\n']
    html.append(f'<p><strong>Всего:</strong> {len(proxies)} прокси</p>\n<div class="stats"><h3>📊 Статистика:</h3><ul>\n')
    for source, count in stats.items():
        if 'SoliSpirit' in source: html.append(f'<li><span class="verified">✓ {source}</span>: {count}</li>\n')
        else: html.append(f'<li>{source}: {count}</li>\n')
    html.append('</ul></div>\n')
    for p in proxies:
        tg = f"tg://proxy?server={p['server']}&port={p['port']}&secret={p['secret']}"
        label = f"🔌 {p['server']}:{p['port']}"
        if 'SoliSpirit' in p['source']: label += ' ✓'
        html.append(f'<a href="{tg}" class="proxy-btn">{label}</a>\n')
    html.append('</body>\n</html>')
    with open('all_proxies.html', 'w', encoding='utf-8') as f: f.write(''.join(html))
    print(f'\n📁 Создано: all_proxies.txt, all_proxies.md, all_proxies.html')

def main():
    print('🚀 Запуск агрегатора MTProto прокси\n')
    mtp4tg_proxies = collect_from_mtp4tg()
    upstream_proxies = collect_from_upstream()
    all_proxies = mtp4tg_proxies + upstream_proxies
    merged = merge_proxies(all_proxies)
    generate_files(merged)
    print('\n✅ Готово!')

if __name__ == '__main__':
    main()
