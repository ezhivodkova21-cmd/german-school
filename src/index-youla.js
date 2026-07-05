#!/usr/bin/env node

require('dotenv').config();
const fs = require('fs');
const YoulaScraper = require('./scraperYoula');
const GoogleSheetsUploader = require('./googleSheets');

async function main() {
  console.log('╔════════════════════════════════════════════════════╗');
  console.log('║   Youla Rental Scraper - Тюмень (аренда квартир)  ║');
  console.log('╚════════════════════════════════════════════════════╝\n');

  const scraper = new YoulaScraper();
  let listings = [];

  try {
    listings = await scraper.scrape(8);

    if (listings.length > 0) {
      scraper.saveToJSON('youla_apartments.json');
      scraper.saveToCSV('youla_apartments.csv');
      console.log('\n✓ Данные сохранены локально:');
      console.log('  - youla_apartments.json');
      console.log('  - youla_apartments.csv');
    }
  } catch (error) {
    console.error('\n❌ Критическая ошибка при сборе данных:', error.message);
    process.exit(1);
  }

  // Загрузка в Google Sheets (если настроено)
  const spreadsheetId = process.env.GOOGLE_SPREADSHEET_ID;
  const credentialsPath = process.env.GOOGLE_CREDENTIALS_PATH || './credentials.json';

  if (spreadsheetId && fs.existsSync(credentialsPath) && listings.length > 0) {
    const uploader = new GoogleSheetsUploader(credentialsPath);
    await uploader.upload(spreadsheetId, listings, 'Аренда Тюмень (Youla)');
  } else if (listings.length > 0) {
    console.log('\nℹ️  Для загрузки в Google Sheets настройте .env (см. README_SCRAPER.md)');
  }

  console.log(`\nИтого собрано объявлений: ${listings.length}`);
}

main().catch((error) => {
  console.error('Критическая ошибка:', error);
  process.exit(1);
});
