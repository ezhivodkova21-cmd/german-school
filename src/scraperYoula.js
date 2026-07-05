const puppeteer = require('puppeteer');
const fs = require('fs');
const path = require('path');

const USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36';

class YoulaScraper {
  constructor() {
    this.baseUrl = 'https://youla.ru';
    // Аренда квартир, длительная, Тюмень
    this.listingUrl = `${this.baseUrl}/tyumen/nedvijimost/arenda-kvartiri`;
    this.listings = [];
    this.rawResponses = [];
    this.browser = null;
  }

  async initBrowser() {
    this.browser = await puppeteer.launch({
      headless: true,
      args: ['--no-sandbox', '--disable-setuid-sandbox']
    });
  }

  async closeBrowser() {
    if (this.browser) await this.browser.close();
  }

  // Перехватить все JSON-ответы страницы — сама Юла подгружает объявления через
  // внутренний API (graphql / web-api) уже после отрисовки SPA-оболочки.
  async capturePageData(page) {
    const collected = [];

    page.on('response', async (response) => {
      try {
        const url = response.url();
        const contentType = response.headers()['content-type'] || '';
        if (!contentType.includes('application/json')) return;
        if (!/graphql|web-api|api\.youla|api-gw\.youla/i.test(url)) return;

        const body = await response.json().catch(() => null);
        if (body) {
          collected.push({ url, body });
        }
      } catch (e) {
        // Игнорируем ответы, которые не удалось прочитать (редиректы, пустые тела и т.п.)
      }
    });

    return collected;
  }

  // Рекурсивно найти в объекте массивы объектов, похожие на карточки объявлений
  // (эвристика: объект содержит одновременно поле с ценой и с заголовком/названием)
  findListingArrays(obj, found = [], seen = new WeakSet()) {
    if (!obj || typeof obj !== 'object') return found;
    if (seen.has(obj)) return found;
    seen.add(obj);

    if (Array.isArray(obj)) {
      const looksLikeListings = obj.length > 0 && obj.every(
        (item) => item && typeof item === 'object' &&
          ('price' in item || 'title' in item || 'name' in item)
      );
      if (looksLikeListings) {
        found.push(obj);
      }
      obj.forEach((item) => this.findListingArrays(item, found, seen));
    } else {
      Object.values(obj).forEach((value) => this.findListingArrays(value, found, seen));
    }

    return found;
  }

  extractField(obj, keys) {
    for (const key of keys) {
      if (obj[key] !== undefined && obj[key] !== null) return obj[key];
    }
    return '';
  }

  normalizeListing(raw) {
    try {
      const title = this.extractField(raw, ['title', 'name']);
      const priceRaw = this.extractField(raw, ['price', 'priceRub', 'price_rur']);
      const price = typeof priceRaw === 'object' ? this.extractField(priceRaw, ['value', 'amount']) : priceRaw;

      const address = this.extractField(raw, ['address', 'formattedAddress', 'location']);
      const addressText = typeof address === 'object' ? this.extractField(address, ['title', 'name', 'text']) : address;

      const seller = raw.owner || raw.user || raw.seller || {};
      const sellerName = this.extractField(seller, ['name', 'title']);
      const sellerType = this.extractField(seller, ['type', 'accountType', 'role']);

      const slug = this.extractField(raw, ['slug', 'id']);
      const link = slug ? `${this.baseUrl}/product/${slug}` : '';

      const attributes = raw.attributes || raw.params || {};
      const rooms = this.extractField(attributes, ['komnat_v_kvartire', 'rooms']);
      const floor = this.extractField(attributes, ['realty_etaj', 'floor']);
      const area = this.extractField(attributes, ['realty_obshaya_ploshad', 'area']);

      return {
        address: addressText || 'Не указан',
        area: parseFloat(area) || 0,
        title: title || '',
        price: parseInt(price) || 0,
        pricePerM2: 0,
        rooms: rooms || '',
        floor: floor || '',
        realEstateComplex: '',
        seller: sellerName || sellerType || 'Неизвестно',
        sellerListingsCount: '',
        publicationDate: this.extractField(raw, ['publishedDate', 'createdAt', 'date']),
        link: link,
        source: 'youla.ru',
        collectionDate: new Date().toISOString().split('T')[0],
        _raw: raw
      };
    } catch (e) {
      return null;
    }
  }

  async scrape(maxScrolls = 8) {
    console.log('Начало сбора данных с Youla (аренда квартир, Тюмень)...');
    console.log(`URL: ${this.listingUrl}`);

    await this.initBrowser();
    const page = await this.browser.newPage();
    await page.setUserAgent(USER_AGENT);

    const collected = await this.capturePageData(page);

    try {
      await page.goto(this.listingUrl, { waitUntil: 'networkidle2', timeout: 30000 });
      await this.sleep(3000);

      // Прокрутка страницы вниз для подгрузки объявлений (бесконечная лента)
      for (let i = 0; i < maxScrolls; i++) {
        await page.evaluate(() => window.scrollBy(0, window.innerHeight * 2));
        await this.sleep(1500);
        console.log(`Прокрутка ${i + 1}/${maxScrolls}, перехвачено ответов: ${collected.length}`);
      }

      // Сохранить сырые данные для диагностики
      const rawPath = path.join(__dirname, '..', 'youla_raw_capture.json');
      fs.writeFileSync(rawPath, JSON.stringify(collected, null, 2), 'utf-8');
      console.log(`\n✓ Сырые перехваченные ответы сохранены в ${rawPath} (для диагностики структуры)`);

      // Попытаться извлечь объявления из перехваченных ответов
      const allArrays = [];
      collected.forEach(({ body }) => {
        this.findListingArrays(body, allArrays);
      });

      const seenIds = new Set();
      allArrays.flat().forEach((raw) => {
        const id = raw.id || raw.slug || JSON.stringify(raw).slice(0, 50);
        if (seenIds.has(id)) return;
        seenIds.add(id);

        const listing = this.normalizeListing(raw);
        if (listing && (listing.price > 0 || listing.title)) {
          this.listings.push(listing);
        }
      });

      console.log(`\nВсего найдено потенциальных объявлений: ${this.listings.length}`);

      if (this.listings.length === 0) {
        console.log('\n⚠️  Автоматическое извлечение не нашло объявлений.');
        console.log('Структура API могла отличаться от ожидаемой.');
        console.log(`Проверьте файл youla_raw_capture.json — там сырые данные всех`);
        console.log('перехваченных сетевых ответов страницы. Пришлите фрагмент,');
        console.log('и мы поправим normalizeListing()/findListingArrays() под реальную структуру.');
      }
    } catch (error) {
      console.error('Ошибка при сборе данных:', error.message);
    } finally {
      await this.closeBrowser();
    }

    return this.listings;
  }

  sleep(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }

  saveToJSON(filename = 'youla_apartments.json') {
    const filepath = path.join(__dirname, '..', filename);
    const clean = this.listings.map(({ _raw, ...rest }) => rest);
    fs.writeFileSync(filepath, JSON.stringify(clean, null, 2), 'utf-8');
    console.log(`Данные сохранены в ${filepath}`);
  }

  saveToCSV(filename = 'youla_apartments.csv') {
    const filepath = path.join(__dirname, '..', filename);

    if (this.listings.length === 0) {
      console.log('Нет данных для сохранения в CSV');
      return;
    }

    const headers = [
      'Адрес', 'Площадь (м²)', 'Тип', 'Цена (руб.)', 'Цена за м² (руб.)',
      'Комнат', 'Этаж', 'ЖК/Комплекс', 'Кто разместил', 'Объявлений у продавца',
      'Дата публикации', 'Ссылка', 'Источник', 'Дата сбора'
    ];

    const rows = this.listings.map((l) => [
      l.address, l.area || '', l.title, l.price, l.pricePerM2,
      l.rooms, l.floor, l.realEstateComplex, l.seller, l.sellerListingsCount,
      l.publicationDate, l.link, l.source, l.collectionDate
    ]);

    let csv = headers.map((h) => `"${h}"`).join(',') + '\n';
    csv += rows.map((row) => row.map((cell) => `"${String(cell).replace(/"/g, '""')}"`).join(',')).join('\n');

    fs.writeFileSync(filepath, csv, 'utf-8');
    console.log(`Данные сохранены в ${filepath}`);
  }
}

module.exports = YoulaScraper;

if (require.main === module) {
  (async () => {
    const scraper = new YoulaScraper();
    await scraper.scrape(8);
    scraper.saveToJSON();
    scraper.saveToCSV();
  })();
}
