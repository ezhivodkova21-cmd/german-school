#!/usr/bin/env python3
"""
Сбор объявлений с realty.yandex.ru (вторичка на продажу + аренда, Тюмень).

Метод: страница поиска содержит window.INITIAL_STATE с полным списком
объявлений (search.offers.entities). Пагинация: первая страница без
параметра page, далее ?page=1,2,3... Сортировка по дате: sort=DATE_DESC.
"""
import argparse
import csv
import json
import sys
import time
import urllib.request
from datetime import datetime, timezone

BASE = "https://realty.yandex.ru"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
HEADERS = {
    "User-Agent": UA,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ru-RU,ru;q=0.9",
}

SELLER_MAP = {"OWNER": "Собственник", "AGENCY": "Агентство", "PRIVATE_AGENT": "Частный агент"}


def extract_state(html):
    marker = "window.INITIAL_STATE = "
    idx = html.find(marker)
    if idx == -1:
        return None
    start = idx + len(marker)
    depth = 0
    in_string = False
    escape = False
    end = start
    for i in range(start, len(html)):
        c = html[i]
        if escape:
            escape = False
            continue
        if c == "\\":
            escape = True
            continue
        if c == '"':
            in_string = not in_string
            continue
        if not in_string:
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    end = i
                    break
    try:
        return json.loads(html[start:end + 1])
    except json.JSONDecodeError:
        return None


def fetch(url, retries=3, delay=5):
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=25) as resp:
                return resp.read().decode("utf-8")
        except Exception as e:
            if attempt == retries - 1:
                print(f"  Ошибка запроса ({url[:80]}...): {e}", file=sys.stderr)
                return None
            time.sleep(delay)
    return None


def rooms_label(offer):
    key = offer.get("roomsTotalKey")
    total = offer.get("roomsTotal")
    if key == "studio":
        return "Студия", "студия"
    if total:
        return f"{total}-комнатная", str(total)
    return "Не указано", ""


def normalize(offer, source_label="Яндекс.Недвижимость"):
    location = offer.get("location", {})
    address = location.get("address") or location.get("geocoderAddress") or "Не указан"
    area = offer.get("area", {}).get("value", "")
    type_label, rooms = rooms_label(offer)
    price_obj = offer.get("price", {})
    price = price_obj.get("value", "")
    price_per_m2 = price_obj.get("valuePerPart", "")
    floor = offer.get("floorsOffered", [""])[0] if offer.get("floorsOffered") else ""
    floors_total = offer.get("floorsTotal", "")
    floor_str = f"{floor}/{floors_total}" if floor and floors_total else ""
    site_name = offer.get("building", {}).get("siteName", "")
    author_cat = offer.get("author", {}).get("category")
    seller = SELLER_MAP.get(author_cat, author_cat or "Не указано")
    url = offer.get("url", "")
    link = f"https:{url}" if url.startswith("//") else url
    creation = offer.get("creationDate", "")
    pub_date = ""
    if creation:
        try:
            pub_date = datetime.strptime(creation[:10], "%Y-%m-%d").strftime("%d.%m.%Y")
        except ValueError:
            pass

    return {
        "Адрес": address,
        "Площадь (м²)": area,
        "Тип": type_label,
        "Цена (руб.)": price,
        "Цена за м² (руб.)": price_per_m2,
        "Комнат": rooms,
        "Этаж": floor_str,
        "ЖК/Комплекс": site_name,
        "Кто разместил": seller,
        "Объявлений у продавца": "нет данных (сайт не показывает)",
        "Дата публикации": pub_date,
        "Ссылка": link,
        "Источник": source_label,
        "Дата сбора": datetime.now(timezone.utc).strftime("%d.%m.%Y"),
        "_offer_id": offer.get("offerId"),
        "_creation_raw": creation,
    }


def scrape(city_slug, deal_path, max_pages=30, owner_only=False, delay=2):
    """deal_path: 'kupit/kvartira' для продажи, 'snyat/kvartira' для аренды."""
    all_offers = {}
    page = 0
    while page <= max_pages:
        if page == 0:
            url = f"{BASE}/{city_slug}/{deal_path}/?sort=DATE_DESC"
        else:
            url = f"{BASE}/{city_slug}/{deal_path}/?sort=DATE_DESC&page={page}"

        html = fetch(url)
        if not html:
            break
        state = extract_state(html)
        if not state:
            print(f"  Не удалось извлечь state на странице {page}", file=sys.stderr)
            break
        entities = state.get("search", {}).get("offers", {}).get("entities", [])
        if not entities:
            print(f"  Пустая страница {page}, остановка")
            break
        for e in entities:
            oid = e.get("offerId")
            if oid:
                all_offers[oid] = e
        page += 1
        time.sleep(delay)

    rows = [normalize(o) for o in all_offers.values()]
    if owner_only:
        rows = [r for r in rows if r["Кто разместил"] == "Собственник"]
    rows.sort(key=lambda r: r["_creation_raw"], reverse=True)
    for r in rows:
        del r["_offer_id"]
        del r["_creation_raw"]
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
    parser.add_argument("--city", default="tyumen")
    parser.add_argument("--deal", choices=["sale", "rent"], required=True)
    parser.add_argument("--max-pages", type=int, default=30)
    parser.add_argument("--owner-only", action="store_true")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    deal_path = "kupit/kvartira/vtorichniy-rynok" if args.deal == "sale" else "snyat/kvartira"
    rows = scrape(args.city, deal_path, max_pages=args.max_pages, owner_only=args.owner_only)
    save_csv(rows, args.out)
