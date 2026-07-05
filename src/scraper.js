const axios = require('axios');
const cheerio = require('cheerio');
const fs = require('fs');
const path = require('path');

// User-Agent для имитации браузера
const USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36';

class AvitoScraper {
  constructor() {
    this.baseUrl = 'https://www.avito.ru';
    this.apartments = [];
    this.headers = {
      'User-Agent': USER_AGENT,
      'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
      'Accept-Language': 'ru-RU,ru;q=0.9',
      'Accept-Encoding': 'gzip, deflate',
      'DNT': '1',
      'Connection': 'keep-alive',
      'Upgrade-Insecure-Requests': '1'
    };
  }

  // Получить список страниц объявлений
  async fetchSearchPage(pageNum = 1) {
    try {
      // URL для поиска вторичных квартир в Тюмени
      const url = `${this.baseUrl}/tyumen/kvartiry/prodam?p=${pageNum}`;

      console.log(`Получение страницы ${pageNum}: ${url}`);

      const response = await axios.get(url, {
        headers: this.headers,
        timeout: 10000
      });

      return response.data;
    } catch (error) {
      console.error(`Ошибка при получении страницы ${pageNum}:`, error.message);
      return null;
    }
  }

  // Парсить данные объявления
  parseApartment($, item) {
    try {
      // Основная ссылка и заголовок
      const titleElement = $(item).find('[itemprop="name"]');
      const title = titleElement.text().trim();
      const link = titleElement.attr('href');
      const fullLink = link ? `${this.baseUrl}${link}` : '';

      // Цена
      const priceText = $(item).find('[itemprop="price"]').attr('content') || '';
      const price = parseInt(priceText) || 0;

      // Адрес
      const address = $(item).find('[itemprop="address"]').text().trim();

      // Описание (часто содержит параметры)
      const description = $(item).find('[itemprop="description"]').text().trim();

      // Информация о продавце
      const sellerSection = $(item).find('.iva-item-sellerInfo');
      const sellerName = sellerSection.find('.iva-item-sellerName').text().trim();
      const sellerType = sellerSection.find('.iva-item-sellerType').text().trim();

      // Дата публикации
      const dateText = $(item).find('.iva-item-dateCreated').text().trim();

      return {
        address: address || 'Не указан',
        title: title,
        description: description,
        price: price,
        pricePerM2: 0, // Будет рассчитано если есть площадь
        rooms: this.extractRooms(description),
        floor: this.extractFloor(description),
        area: this.extractArea(description),
        realEstateComplex: this.extractRealEstateComplex(description),
        seller: sellerName || sellerType || 'Неизвестно',
        sellerListingsCount: 0, // Требует дополнительного запроса
        publicationDate: dateText,
        link: fullLink,
        source: 'avito.ru',
        collectionDate: new Date().toISOString().split('T')[0]
      };
    } catch (error) {
      console.error('Ошибка при парсировании объявления:', error.message);
      return null;
    }
  }

  // Извлечь количество комнат
  extractRooms(text) {
    const match = text.match(/(\d+)\s*-?к(омн|вартир)?/i);
    return match ? match[1] : 0;
  }

  // Извлечь этаж
  extractFloor(text) {
    const match = text.match(/(\d+)[–\-\/]?\d*\s*этаж/i);
    return match ? match[1] : 0;
  }

  // Извлечь площадь
  extractArea(text) {
    const match = text.match(/(\d+(?:[.,]\d+)?)\s*м²?/i);
    return match ? parseFloat(match[1].replace(',', '.')) : 0;
  }

  // Извлечь название ЖК
  extractRealEstateComplex(text) {
    const match = text.match(/ЖК\s+"?([^",]+)/i);
    return match ? match[1].trim() : '';
  }

  // Главная функция парсирования
  async scrape(maxPages = 5) {
    console.log('Начало сбора данных с Avito...');
    console.log(`Город: Тюмень, Максимум страниц: ${maxPages}`);

    for (let page = 1; page <= maxPages; page++) {
      const html = await this.fetchSearchPage(page);

      if (!html) {
        console.log(`Не удалось получить страницу ${page}, остановка скрейпинга`);
        break;
      }

      const $ = cheerio.load(html);
      const items = $('[data-marker="catalog-serp"] .iva-item-root');

      console.log(`Страница ${page}: найдено ${items.length} объявлений`);

      items.each((index, item) => {
        const apartment = this.parseApartment($, item);
        if (apartment && apartment.price > 0) {
          // Рассчитать цену за м²
          if (apartment.area > 0) {
            apartment.pricePerM2 = Math.round(apartment.price / apartment.area);
          }
          this.apartments.push(apartment);
        }
      });

      // Небольшая задержка между запросами
      await this.sleep(2000);
    }

    console.log(`Всего собрано объявлений: ${this.apartments.length}`);
    return this.apartments;
  }

  sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  // Сохранить данные в JSON
  saveToJSON(filename = 'apartments.json') {
    const filepath = path.join(__dirname, '..', filename);
    fs.writeFileSync(filepath, JSON.stringify(this.apartments, null, 2), 'utf-8');
    console.log(`Данные сохранены в ${filepath}`);
  }

  // Сохранить данные в CSV
  saveToCSV(filename = 'apartments.csv') {
    const filepath = path.join(__dirname, '..', filename);

    if (this.apartments.length === 0) {
      console.log('Нет данных для сохранения');
      return;
    }

    const headers = [
      'Адрес',
      'Площадь (м²)',
      'Тип',
      'Цена (руб.)',
      'Цена за м² (руб.)',
      'Комнат',
      'Этаж',
      'ЖК/Комплекс',
      'Кто разместил',
      'Объявлений у продавца',
      'Дата публикации',
      'Ссылка',
      'Источник',
      'Дата сбора'
    ];

    const rows = this.apartments.map(apt => [
      apt.address,
      apt.area || '',
      apt.title,
      apt.price,
      apt.pricePerM2,
      apt.rooms,
      apt.floor,
      apt.realEstateComplex,
      apt.seller,
      apt.sellerListingsCount,
      apt.publicationDate,
      apt.link,
      apt.source,
      apt.collectionDate
    ]);

    let csv = headers.map(h => `"${h}"`).join(',') + '\n';
    csv += rows.map(row => row.map(cell => `"${String(cell).replace(/"/g, '""')}"`).join(',')).join('\n');

    fs.writeFileSync(filepath, csv, 'utf-8');
    console.log(`Данные сохранены в ${filepath}`);
  }
}

// Запуск скрейпера
async function main() {
  const scraper = new AvitoScraper();

  try {
    const apartments = await scraper.scrape(3); // Собрать первые 3 страницы
    scraper.saveToJSON('apartments.json');
    scraper.saveToCSV('apartments.csv');

    console.log('\nПримеры собранных данных:');
    apartments.slice(0, 2).forEach((apt, i) => {
      console.log(`\nОбъявление ${i + 1}:`);
      console.log(`  Адрес: ${apt.address}`);
      console.log(`  Площадь: ${apt.area} м²`);
      console.log(`  Цена: ${apt.price} руб.`);
      console.log(`  Комнат: ${apt.rooms}`);
    });
  } catch (error) {
    console.error('Критическая ошибка:', error);
  }
}

// Экспорт для использования как модуля
module.exports = AvitoScraper;

// Запуск если вызван напрямую
if (require.main === module) {
  main();
}
