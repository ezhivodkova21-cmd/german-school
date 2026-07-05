#!/usr/bin/env node

require('dotenv').config();
const fs = require('fs');
const path = require('path');
const AvitoScraper = require('./scraper');
const GoogleSheetsUploader = require('./googleSheets');

async function main() {
  console.log('╔════════════════════════════════════════════════════╗');
  console.log('║    Avito Apartment Scraper - Tyumen Edition       ║');
  console.log('╚════════════════════════════════════════════════════╝\n');

  // Этап 1: Сбор данных с Avito
  console.log('📍 Этап 1: Сбор данных с Avito.ru\n');

  const scraper = new AvitoScraper();
  let apartments = [];

  try {
    apartments = await scraper.scrape(3); // Собрать первые 3 страницы (примерно 60-90 объявлений)

    if (apartments.length === 0) {
      console.warn('\n⚠️  Объявления не найдены. Это может быть из-за:');
      console.warn('   - Защиты сайта от автоматического доступа');
      console.warn('   - Изменения структуры HTML');
      console.warn('\n   Решение: Используйте Puppeteer или API услуги парсинга');
    } else {
      // Сохранить локально
      scraper.saveToJSON('apartments.json');
      scraper.saveToCSV('apartments.csv');

      console.log('\n✓ Данные сохранены локально:');
      console.log('  - apartments.json');
      console.log('  - apartments.csv');
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
    console.log('\nДля загрузки в Google Sheets:');
    console.log('1. Создайте сервис-аккаунт в Google Cloud');
    console.log('2. Скачайте JSON с учетными данными');
    console.log('3. Создайте/откройте Google Spreadsheet');
    console.log('4. Поделитесь доступом с email сервис-аккаунта');
    console.log('5. Установите переменные окружения в .env:');
    console.log('   GOOGLE_SPREADSHEET_ID=ваш_id');
    console.log('   GOOGLE_CREDENTIALS_PATH=путь/к/credentials.json\n');
  } else if (!fs.existsSync(credentialsPath)) {
    console.warn(`⚠️  Файл с учетными данными не найден: ${credentialsPath}`);
    console.log('Пожалуйста, скачайте credentials.json из Google Cloud\n');
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
    console.log(`   - apartments.json`);
    console.log(`   - apartments.csv`);

    if (spreadsheetId) {
      console.log(`\n📎 Google Spreadsheet:`);
      console.log(`   https://docs.google.com/spreadsheets/d/${spreadsheetId}`);
    }
  } else {
    console.log('❌ Данные не собраны.');
    console.log('\nРекомендации:');
    console.log('1. Проверьте подключение к интернету');
    console.log('2. Убедитесь, что сайт доступен');
    console.log('3. Попробуйте использовать Puppeteer для браузерной эмуляции');
    console.log('4. Рассмотрите использование API услуги парсинга');
  }

  console.log('\n');
}

main().catch(error => {
  console.error('Критическая ошибка:', error);
  process.exit(1);
});
