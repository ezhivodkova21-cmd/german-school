const { GoogleSpreadsheet } = require('google-spreadsheet');
const fs = require('fs');
const path = require('path');

class GoogleSheetsUploader {
  constructor(credentialsPath) {
    this.credentialsPath = credentialsPath;
    this.doc = null;
  }

  // Инициализация подключения к Google Sheets
  async initialize(spreadsheetId) {
    try {
      if (!fs.existsSync(this.credentialsPath)) {
        throw new Error(`Файл с учетными данными не найден: ${this.credentialsPath}`);
      }

      const credentials = JSON.parse(fs.readFileSync(this.credentialsPath, 'utf-8'));

      this.doc = new GoogleSpreadsheet(spreadsheetId);

      await this.doc.useServiceAccountAuth(credentials);
      await this.doc.loadInfo();

      console.log('✓ Подключение к Google Sheets установлено');
      console.log(`✓ Название документа: ${this.doc.title}`);

      return true;
    } catch (error) {
      console.error('Ошибка подключения к Google Sheets:', error.message);
      return false;
    }
  }

  // Создать новый лист
  async createSheet(title) {
    try {
      const sheet = await this.doc.addSheet({ title, headerValues: [] });
      console.log(`✓ Создан лист: ${title}`);
      return sheet;
    } catch (error) {
      console.error('Ошибка при создании листа:', error.message);
      return null;
    }
  }

  // Добавить заголовки к листу
  async addHeaders(sheet) {
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

    await sheet.setHeaderRow(headers);
    console.log('✓ Заголовки добавлены');
  }

  // Загрузить данные в Google Sheets
  async uploadData(sheet, apartments) {
    try {
      const rows = apartments.map(apt => [
        apt.address,
        apt.area || '',
        apt.title,
        apt.price,
        apt.pricePerM2,
        apt.rooms || '',
        apt.floor || '',
        apt.realEstateComplex || '',
        apt.seller,
        apt.sellerListingsCount || '',
        apt.publicationDate,
        apt.link,
        apt.source,
        apt.collectionDate
      ]);

      // Добавить строки пакетами по 100
      const batchSize = 100;
      for (let i = 0; i < rows.length; i += batchSize) {
        const batch = rows.slice(i, i + batchSize);
        await sheet.addRows(batch);
        console.log(`✓ Загружено ${Math.min(i + batchSize, rows.length)} из ${rows.length} строк`);
      }

      console.log(`✓ Все ${rows.length} объявлений загружены в Google Sheets`);
      return true;
    } catch (error) {
      console.error('Ошибка при загрузке данных:', error.message);
      return false;
    }
  }

  // Основной метод загрузки
  async upload(spreadsheetId, apartments, sheetTitle = 'Квартиры') {
    console.log('\n📊 Начало загрузки данных в Google Sheets...');

    // Инициализация
    const initialized = await this.initialize(spreadsheetId);
    if (!initialized) {
      return false;
    }

    try {
      // Найти или создать лист
      let sheet = this.doc.sheetsByTitle[sheetTitle];

      if (!sheet) {
        sheet = await this.createSheet(sheetTitle);
        if (!sheet) {
          return false;
        }
      }

      // Очистить старые данные если нужно
      if (sheet.rowCount > 1) {
        console.log('Очистка старых данных...');
        await sheet.clear();
      }

      // Добавить заголовки
      await this.addHeaders(sheet);

      // Загрузить данные
      const success = await this.uploadData(sheet, apartments);

      if (success) {
        console.log(`\n✓ Данные успешно загружены!`);
        console.log(`📎 Ссылка на документ: https://docs.google.com/spreadsheets/d/${spreadsheetId}`);
      }

      return success;
    } catch (error) {
      console.error('Критическая ошибка при загрузке:', error.message);
      return false;
    }
  }
}

module.exports = GoogleSheetsUploader;
