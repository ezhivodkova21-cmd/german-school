#!/usr/bin/env node

require('dotenv').config();
const fs = require('fs');
const path = require('path');
const AvitoScraperPuppeteer = require('./scraperPuppeteer');
const GoogleSheetsUploader = require('./googleSheets');

async function main() {
  console.log('╔════════════════════════════════════════════════════╗');
  console.log('║   Avito Apartment Scraper (Browser) - Tyumen      ║');
  console.log('╚════════════════════════════════════════════════════╝\n');

  // Проверка зависимостей
  try {
    require('puppeteer');
    require('jsdom');
  } catch (error) {
    console.error('❌ Требуемые зависимости не установлены.');
    console.log('\nДля использования режима браузера установите:');
    console.log('  npm install puppeteer jsdom\n');
    process.exit(1);
  }

  // Этап 1: Сбор данных с Avito
  console.log('📍 Этап 1: Сбор данных с Avito.ru (браузерный режим)\n');

  const scraper = new AvitoScraperPuppeteer();
  let apartments = [];

  try {
    apartments = await scraper.scrape(3);

    if (apartments.length === 0) {
      console.warn('\n⚠️  Объявления не найдены.');
    } else {
      scraper.saveToJSON('apartments_browser.json');
      scraper.saveToCSV('apartments_browser.csv');

      console.log('\n✓ Данные сохранены локально:');
      console.log('  - apartments_browser.json');
      console.log('  - apartments_browser.csv');
    }
  } catch (error) {
    console.error('\n❌ Критическая ошибка при сборе данных:', error.message);
    process.exit(1);
  }

  // Этап 2: Загрузка в Google Sheets (если задана конфигурация)
  console.log('\n\n📊 Этап 2: Загрузка в Google Sheets\n');

  const spreadsheetId = process.env.GOOGLE_SPREADSHEET_ID;
  const credentialsPath = process.env.GOOGLE_CREDENTIALS_PATH || './credentials.json';

  if (!spreadsheetId) {
    console.warn('⚠️  GOOGLE_SPREADSHEET_ID не установлен в .env');
    console.log('\nДля загрузки в Google Sheets создайте файл .env');
  } else if (!fs.existsSync(credentialsPath)) {
    console.warn(`⚠️  Файл с учетными данными не найден: ${credentialsPath}`);
  } else if (apartments.length > 0) {
    const uploader = new GoogleSheetsUploader(credentialsPath);
    const uploadSuccess = await uploader.upload(spreadsheetId, apartments, 'Квартиры Тюмень');

    if (uploadSuccess) {
      console.log('\n✓ Все данные загружены в Google Sheets!');
    }
  }

  // Итоговая статистика
  console.log('\n\n╔════════════════════════════════════════════════════╗');
  console.log('║                    Результаты                     ║');
  console.log('╚════════════════════════════════════════════════════╝\n');

  if (apartments.length > 0) {
    const stats = {
      всего: apartments.length,
      сНаценой: apartments.filter(a => a.price > 0).length,
      сПлощадью: apartments.filter(a => a.area > 0).length,
      среднецена: Math.round(
        apartments.filter(a => a.price > 0).reduce((sum, a) => sum + a.price, 0) /
        apartments.filter(a => a.price > 0).length
      ),
      среднецнаМ2: Math.round(
        apartments.filter(a => a.pricePerM2 > 0).reduce((sum, a) => sum + a.pricePerM2, 0) /
        apartments.filter(a => a.pricePerM2 > 0).length
      )
    };

    console.log(`📊 Статистика:`);
    console.log(`   Всего объявлений: ${stats.всего}`);
    console.log(`   С ценой: ${stats.сНаценой}`);
    console.log(`   С площадью: ${stats.сПлощадью}`);
    console.log(`   Средняя цена: ${stats.среднецена.toLocaleString('ru-RU')} руб.`);
    console.log(`   Средняя цена/м²: ${stats.среднецнаМ2.toLocaleString('ru-RU')} руб.`);

    console.log(`\n📁 Данные доступны в:`);
    console.log(`   - apartments_browser.json`);
    console.log(`   - apartments_browser.csv`);

    if (spreadsheetId) {
      console.log(`\n📎 Google Spreadsheet:`);
      console.log(`   https://docs.google.com/spreadsheets/d/${spreadsheetId}`);
    }
  } else {
    console.log('❌ Данные не собраны.');
  }

  console.log('\n');
}

main().catch(error => {
  console.error('Критическая ошибка:', error);
  process.exit(1);
});
