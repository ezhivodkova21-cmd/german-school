#!/usr/bin/env python3
"""
Ежедневный сбор объявлений (вторичка на продажу + аренда) по Тюмени.

Запускает Яндекс.Недвижимость и Avito (проверенные HTTP-методы без
браузера). ЦИАН и Юла требуют дополнительных шагов (см. README.md в
этой директории) и не входят в этот скрипт напрямую.

Использование:
    python3 run_daily.py --out-dir /path/to/output
"""
import argparse
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import yandex_realty
import avito


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--owner-only", action="store_true",
                        help="Только объявления от собственников (где эта информация доступна)")
    parser.add_argument("--since-hours", type=float, default=24,
                        help="Только объявления, опубликованные не позже N часов назад (по умолчанию 24 — 'за сутки')")
    args = parser.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)
    date_tag = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    print(f"=== Яндекс.Недвижимость: продажа (вторичка), за последние {args.since_hours} ч. ===")
    rows = yandex_realty.scrape("tyumen", "kupit/kvartira/vtorichniy-rynok",
                                 max_pages=40, owner_only=args.owner_only,
                                 since_hours=args.since_hours)
    yandex_realty.save_csv(rows, os.path.join(args.out_dir, f"yandex_sale_{date_tag}.csv"))

    print(f"\n=== Яндекс.Недвижимость: аренда, за последние {args.since_hours} ч. ===")
    rows = yandex_realty.scrape("tyumen", "snyat/kvartira",
                                 max_pages=40, owner_only=args.owner_only,
                                 since_hours=args.since_hours)
    yandex_realty.save_csv(rows, os.path.join(args.out_dir, f"yandex_rent_{date_tag}.csv"))

    print(f"\n=== Avito: продажа (вторичка), за последние {args.since_hours} ч. ===")
    rows = avito.scrape(avito.SALE_URL, max_pages=20, since_hours=args.since_hours)
    avito.save_csv(rows, os.path.join(args.out_dir, f"avito_sale_{date_tag}.csv"))

    print(f"\n=== Avito: аренда, за последние {args.since_hours} ч. ===")
    rows = avito.scrape(avito.RENT_URL, max_pages=20, since_hours=args.since_hours)
    avito.save_csv(rows, os.path.join(args.out_dir, f"avito_rent_{date_tag}.csv"))

    print(f"\nГотово. Файлы сохранены в {args.out_dir}")
    print("ЦИАН и Юла требуют отдельного запуска (см. README.md)")


if __name__ == "__main__":
    main()
