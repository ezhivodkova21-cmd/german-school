#!/usr/bin/env python3
"""
Сбор объявлений с avito.ru (вторичка на продажу + аренда, Тюмень).

Метод: страница поиска содержит <script type="mime/invalid"
data-mfe-state="true"> с полным JSON каталога
(loaderData.data.catalog.items). Пагинация через catalog.pager.next.
Сортировка по дате: s=104.

Важно: Avito агрессивно ограничивает частоту запросов (429) и может
выдать полную блокировку по IP ("Доступ ограничен: проблема с IP",
403) при слишком частых обращениях. Скрипт делает паузы между
страницами и останавливается при ошибке, а не повторяет бесконечно.

Тип продавца (Риелтор/Собственник/Агентство) НЕ виден на странице
списка — только на странице конкретного объявления. Проверка типа
продавца для каждого объявления кратно увеличивает число запросов и
риск блокировки, поэтому по умолчанию отключена (--check-seller
включает её для ограниченного числа объявлений через --seller-limit).
"""
import argparse
import csv
import json
import re
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, timedelta, timezone

BASE = "https://www.avito.ru"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
HEADERS = {
    "User-Agent": UA,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ru-RU,ru;q=0.9",
}

SALE_URL = BASE + "/tyumen/kvartiry/prodam/vtorichniy_rynok-ASgBAgICAkSSA8gQ8AeQUg"
RENT_URL = BASE + "/tyumen/kvartiry/sdam/na_dlitelnyy_srok-ASgBAgICAkSSA8gQ8AeQUg"


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
        "Кто разместил": "нет данных (не показано в списке)",
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
    all_items = {}
    url = f"{start_url}?cd=1&s=104"
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
        catalog = state["loaderData"]["data"]["catalog"]
        items = [it for it in catalog.get("items", []) if it.get("type") == "item"]
        if not items:
            print("  Нет объявлений, остановка")
            break
        for it in items:
            all_items[it["id"]] = it

        oldest_ts = min(it.get("allowTimeStamp", 0) for it in items)
        oldest_dt = datetime.fromtimestamp(oldest_ts / 1000)
        print(f"  -> {len(items)} объявлений, старейшее: {oldest_dt.strftime('%Y-%m-%d')}")
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
