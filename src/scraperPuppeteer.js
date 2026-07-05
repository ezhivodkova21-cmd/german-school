const puppeteer = require('puppeteer');
const fs = require('fs');
const path = require('path');

class AvitoScraperPuppeteer {
  constructor() {
    this.baseUrl = 'https://www.avito.ru';
    this.apartments = [];
    this.browser = null;
  }

  // Инициализировать браузер
  async initBrowser() {
    try {
      this.browser = await puppeteer.launch({
        headless: true,
        args: [
          '--no-sandbox',
          '--disable-setuid-sandbox',
          '--disable-blink-features=AutomationControlled'
        ]
      });
      console.log('✓ Браузер инициализирован');
      return true;
    } catch (error) {
      console.error('Ошибка при инициализации браузера:', error.message);
      return false;
    }
  }

  // Закрыть браузер
  async closeBrowser() {
    if (this.browser) {
      await this.browser.close();
      console.log('✓ Браузер закрыт');
    }
  }

  // Получить страницу объявлений
  async fetchSearchPage(pageNum = 1) {
    const page = await this.browser.newPage();

    try {
      const url = `${this.baseUrl}/tyumen/kvartiry/prodam?p=${pageNum}`;

      console.log(`Получение страницы ${pageNum}: ${url}`);

      // Установить User-Agent
      await page.setUserAgent(
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
      );

      // Перейти на страницу
      await page.goto(url, {
        waitUntil: 'networkidle2',
        timeout: 30000
      });

      // Дождаться загрузки объявлений
      await page.waitForSelector('[data-marker="catalog-serp"]', { timeout: 10000 }).catch(() => {
        console.warn('Селектор каталога не найден, продолжаем...');
      });

      // Прокрутить страницу для загрузки всех элементов
      await page.evaluate(() => {
        window.scrollBy(0, window.innerHeight);
      });

      // Получить HTML
      const html = await page.content();

      await page.close();
      return html;
    } catch (error) {
      console.error(`Ошибка при получении страницы ${pageNum}:`, error.message);
      await page.close();
      return null;
    }
  }

  // Парсить данные объявления
  parseApartment(item) {
    try {
      // Извлечь атрибуты из JSON-LD если доступны
      const titleElement = item.querySelector('[itemprop="name"]');
      const title = titleElement ? titleElement.textContent.trim() : '';
      const link = titleElement ? titleElement.getAttribute('href') : '';
      const fullLink = link ? `${this.baseUrl}${link}` : '';

      // Цена
      const priceContent = item.querySelector('[itemprop="price"]');
      const price = priceContent ? parseInt(priceContent.getAttribute('content')) || 0 : 0;

      // Адрес
      const addressElement = item.querySelector('[itemprop="address"]');
      const address = addressElement ? addressElement.textContent.trim() : 'Не указан';

      // Описание
      const descriptionElement = item.querySelector('[itemprop="description"]');
      const description = descriptionElement ? descriptionElement.textContent.trim() : '';

      // Информация о продавце
      const sellerSection = item.querySelector('.iva-item-sellerInfo');
      const sellerNameElement = sellerSection ? sellerSection.querySelector('.iva-item-sellerName') : null;
      const sellerName = sellerNameElement ? sellerNameElement.textContent.trim() : 'Неизвестно';

      // Дата публикации
      const dateElement = item.querySelector('.iva-item-dateCreated');
      const dateText = dateElement ? dateElement.textContent.trim() : '';

      return {
        address: address || 'Не указан',
        title: title,
        description: description,
        price: price,
        pricePerM2: 0,
        rooms: this.extractRooms(description + ' ' + title),
        floor: this.extractFloor(description + ' ' + title),
        area: this.extractArea(description + ' ' + title),
        realEstateComplex: this.extractRealEstateComplex(description + ' ' + title),
        seller: sellerName,
        sellerListingsCount: 0,
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
    return match ? parseInt(match[1]) : 0;
  }

  // Извлечь этаж
  extractFloor(text) {
    const match = text.match(/(\d+)[–\-\/]?\d*\s*этаж/i);
    return match ? parseInt(match[1]) : 0;
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

  // Парсить HTML и извлечь объявления
  async parseHTML(html) {
    return new Promise((resolve, reject) => {
      try {
        const { JSDOM } = require('jsdom');
        const dom = new JSDOM(html);
        const document = dom.window.document;

        const items = document.querySelectorAll('[data-marker="catalog-serp"] .iva-item-root');
        const apartments = [];

        items.forEach((item) => {
          const apartment = this.parseApartment(item);
          if (apartment && apartment.price > 0) {
            if (apartment.area > 0) {
              apartment.pricePerM2 = Math.round(apartment.price / apartment.area);
            }
            apartments.push(apartment);
          }
        });

        resolve(apartments);
      } catch (error) {
        console.error('Ошибка при парсировании HTML:', error.message);
        reject(error);
      }
    });
  }

  // Главная функция скрейпинга
  async scrape(maxPages = 5) {
    console.log('Начало сбора данных с Avito (Puppeteer)...');
    console.log(`Город: Тюмень, Максимум страниц: ${maxPages}`);

    // Инициализировать браузер
    const initialized = await this.initBrowser();
    if (!initialized) {
      return [];
    }

    try {
      for (let page = 1; page <= maxPages; page++) {
        const html = await this.fetchSearchPage(page);

        if (!html) {
          console.log(`Не удалось получить страницу ${page}, остановка скрейпинга`);
          break;
        }

        // Парсить HTML
        const pageApartments = await this.parseHTML(html);
        console.log(`Страница ${page}: найдено ${pageApartments.length} объявлений`);

        this.apartments.push(...pageApartments);

        // Задержка между запросами
        if (page < maxPages) {
          await this.sleep(2000);
        }
      }

      console.log(`Всего собрано объявлений: ${this.apartments.length}`);
      return this.apartments;
    } finally {
      await this.closeBrowser();
    }
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

module.exports = AvitoScraperPuppeteer;
