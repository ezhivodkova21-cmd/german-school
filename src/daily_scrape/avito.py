#!/usr/bin/env python3
"""
Сбор объявлений с avito.ru (вторичка на продажу + аренда, Тюмень).

Метод: страница поиска содержит <script type="mime/invalid"
data-mfe-state="true"> с полным JSON каталога
(loaderData.data.catalog.items). Пагинация через catalog.pager.next.

Тип продавца ЧАСТИЧНО виден прямо в списке (без захода в объявление):
поле item.iva.SecondLineStep[].payload.value содержит буквально текст
"Агентство" для агентских объявлений и отсутствует/пусто для большинства
частных объявлений. Сигнал не идеален — встречались единичные
противоречивые случаи (например явный бейдж "Собственник" в
BadgeBarStep при одновременно заполненном SecondLineStep="Агентство"),
поэтому это эвристика, а не гарантия, но для практической фильтрации
достаточно надёжна.

Важно про URL и сортировку:
- RENT_URL — категорийный URL с закодированным ID, поддерживает
  сортировку по дате (?s=104) и её можно использовать для ранней
  остановки пагинации (объявления идут строго по убыванию даты).
- SALE_URL — категории "продажа вторичного жилья" на Avito не
  существует как отдельного SEO-пути; рабочий вариант — это
  полнотекстовый поиск (?q=...). У него ДРУГАЯ реализация сортировки:
  добавление ?s=104 к этому конкретному URL стабильно даёт 403
  (проверено вживую) — вероятно, WAF считает такую комбинацию
  подозрительной для текстового поиска. Поэтому для SALE_URL сортировка
  не используется, объявления идут в порядке "по умолчанию"
  (не хронологическом), и since_hours для него работает только как
  пост-фильтр после сбора фиксированного числа страниц, а не как
  условие ранней остановки — часть свежих объявлений на большую
  глубину может быть пропущена.

Важно про блокировки: Avito агрессивно ограничивает частоту запросов
(429) и может выдать полную блокировку по IP ("Доступ ограничен:
проблема с IP", 403) при слишком частых обращениях. Скрипт делает
паузы между страницами и останавливается при ошибке, а не повторяет
бесконечно.
"""
import argparse
import csv
import json
import re
import sys
import time
import urllib.request
import urllib.error
import urllib.parse
from datetime import datetime, timedelta, timezone

BASE = "https://www.avito.ru"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
HEADERS = {
    "User-Agent": UA,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ru-RU,ru;q=0.9",
}

# Подтверждено живым тестом: категорийного URL для "продажа вторичного
# жилья" не существует, рабочий вариант — полнотекстовый поиск.
# НЕ поддерживает сортировку по дате (?s=104 -> 403), см. docstring выше.
SALE_URL = BASE + "/tyumen/kvartiry?q=" + urllib.parse.quote("продажа вторичной квартиры")
# Категорийный URL, поддерживает ?s=104 (сортировка по дате).
RENT_URL = BASE + "/tyumen/kvartiry/sdam/na_dlitelnyy_srok-ASgBAgICAkSSA8gQ8AeQUg"

SORTABLE_URLS = {RENT_URL}


def extract_mfe_state(html):
    marker = '<script type="mime/invalid" data-mfe-state="true">'
    idx = html.find(marker)
    if idx == -1:
        return None
    start = idx + len(marker)
    end = html.find("</script>", start)
    try:
        return json.loads(html[start:end])
    except json.JSONDecodeError:
        return None


def fetch(url, retries=3):
    delay = 8
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=25) as resp:
                return resp.read().decode("utf-8"), 200
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < retries - 1:
                print(f"    429, ждём {delay}с...", file=sys.stderr)
                time.sleep(delay)
                delay *= 2
                continue
            return None, e.code
        except Exception as e:
            print(f"  Ошибка запроса: {e}", file=sys.stderr)
            return None, 0
    return None, 429


def parse_title(title):
    title = title.replace("\xa0", " ")
    rooms = ""
    type_label = title
    m_rooms = re.match(r"(\d+)-к\.", title)
    if m_rooms:
        rooms = m_rooms.group(1)
        type_label = f"{rooms}-комнатная"
    elif "студия" in title.lower():
        rooms = "студия"
        type_label = "Студия"

    area = ""
    m_area = re.search(r"(\d+(?:[.,]\d+)?)\s*м", title)
    if m_area:
        area = m_area.group(1).replace(",", ".")

    floor = ""
    m_floor = re.search(r"(\d+)/(\d+)\s*эт", title)
    if m_floor:
        floor = f"{m_floor.group(1)}/{m_floor.group(2)}"

    return type_label, rooms, area, floor


def get_seller_type(item):
    """Эвристика на основе iva.SecondLineStep: агентства почти всегда
    показывают там текст "Агентство"; у частных объявлений это поле
    обычно пустое. Не идеально надёжно (см. docstring модуля), поэтому
    возвращаем "Вероятно собственник" вместо категоричного "Собственник"."""
    steps = item.get("iva", {}).get("SecondLineStep", [])
    for step in steps:
        val = step.get("payload", {}).get("value", "")
        if val:
            return val
    return "Вероятно собственник (нет метки агентства)"


def normalize(item, source_label="Avito"):
    title = item.get("title", "")
    type_label, rooms, area, floor = parse_title(title)
    address = item.get("geo", {}).get("formattedAddress", "") or \
        item.get("addressDetailed", {}).get("locationName", "Не указан")
    price = item.get("priceDetailed", {}).get("value", "")
    price_per_m2 = ""
    try:
        if price and area:
            price_per_m2 = round(float(price) / float(area))
    except (ValueError, ZeroDivisionError):
        pass
    url_path = item.get("urlPath", "")
    link = f"{BASE}{url_path.split('?')[0]}" if url_path.startswith("/") else url_path
    ts = item.get("allowTimeStamp")
    pub_date = datetime.fromtimestamp(ts / 1000).strftime("%d.%m.%Y") if ts else ""

    return {
        "Адрес": address,
        "Площадь (м²)": area,
        "Тип": type_label,
        "Цена (руб.)": price,
        "Цена за м² (руб.)": price_per_m2,
        "Комнат": rooms,
        "Этаж": floor,
        "ЖК/Комплекс": "",
        "Кто разместил": get_seller_type(item),
        "Объявлений у продавца": "нет данных (не показано в списке)",
        "Дата публикации": pub_date,
        "Ссылка": link,
        "Источник": source_label,
        "Дата сбора": datetime.now(timezone.utc).strftime("%d.%m.%Y"),
        "_id": item.get("id"),
        "_ts": ts or 0,
    }


def scrape(start_url, max_pages=30, delay=6, stop_before_month=None, stop_before_year=None,
           since_hours=None):
    """stop_before_year/month: остановиться, как только объявления на
    странице становятся старше этой даты (для ограничения глубины
    сбора, например только май-июль 2026).

    since_hours: если задано, останавливает пагинацию и фильтрует
    результат строго по объявлениям новее этого числа часов (например
    24 для "за последние сутки")."""
    cutoff_ts = (datetime.now().timestamp() - since_hours * 3600) * 1000 if since_hours else None
    sortable = start_url in SORTABLE_URLS
    sep = "&" if "?" in start_url else "?"
    url = f"{start_url}{sep}cd=1" + ("&s=104" if sortable else "")
    all_items = {}
    page = 1
    while url and page <= max_pages:
        print(f"Страница {page}...")
        html, code = fetch(url)
        if not html:
            print(f"  Остановка: HTTP {code}", file=sys.stderr)
            break
        state = extract_mfe_state(html)
        if not state:
            print("  Не удалось извлечь state, остановка", file=sys.stderr)
            break
        loader_data = state.get("loaderData", {}).get("data", {})
        if loader_data.get("redirected"):
            print(f"  URL редиректит на {loader_data.get('url')} — вероятно, неверная ссылка на категорию. Остановка.", file=sys.stderr)
            break
        if "catalog" not in loader_data:
            print(f"  Нет ключа 'catalog' в ответе (ключи: {list(loader_data.keys())}) — структура страницы неожиданная. Остановка.", file=sys.stderr)
            break
        catalog = loader_data["catalog"]
        items = [it for it in catalog.get("items", []) if it.get("type") == "item"]
        if not items:
            print("  Нет объявлений, остановка")
            break
        for it in items:
            all_items[it["id"]] = it

        oldest_ts = min(it.get("allowTimeStamp", 0) for it in items)
        oldest_dt = datetime.fromtimestamp(oldest_ts / 1000)
        print(f"  -> {len(items)} объявлений, старейшее на странице: {oldest_dt.strftime('%Y-%m-%d')}"
              + ("" if sortable else " (порядок не хронологический, старейшее не значит конец)"))
        if sortable:
            if stop_before_year and (oldest_dt.year, oldest_dt.month) < (stop_before_year, stop_before_month):
                print("  Достигли нижней границы дат, останавливаемся.")
                break
            if cutoff_ts and oldest_ts < cutoff_ts:
                print("  Достигли границы 'since_hours', останавливаемся.")
                break

        pager = catalog.get("pager", {})
        next_path = pager.get("next")
        if not next_path:
            break
        url = BASE + next_path if next_path.startswith("/") else next_path
        page += 1
        time.sleep(delay)

    rows = [normalize(it) for it in all_items.values()]
    if cutoff_ts:
        rows = [r for r in rows if r["_ts"] >= cutoff_ts]
    rows.sort(key=lambda r: r["_ts"], reverse=True)
    for r in rows:
        del r["_id"]
        del r["_ts"]
    return rows


def save_csv(rows, path):
    if not rows:
        print(f"Нет данных для {path}")
        return
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"Сохранено {len(rows)} строк в {path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--deal", choices=["sale", "rent"], required=True)
    parser.add_argument("--max-pages", type=int, default=15)
    parser.add_argument("--min-year", type=int, default=None)
    parser.add_argument("--min-month", type=int, default=None)
    parser.add_argument("--since-hours", type=float, default=None,
                        help="Только объявления новее N часов (например 24 для 'за сутки')")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    start_url = SALE_URL if args.deal == "sale" else RENT_URL
    rows = scrape(start_url, max_pages=args.max_pages,
                  stop_before_year=args.min_year, stop_before_month=args.min_month,
                  since_hours=args.since_hours)
    save_csv(rows, args.out)
