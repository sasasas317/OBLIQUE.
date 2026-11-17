Задача: Обновить массив данных о товарах в текущем проекте. Теперь включаем репрезентативные позиции из категорий: Jewelry (Украшения), Bags/Wallets (Сумки/Кошельки) и Footwear (Обувь).

КРИТИЧЕСКИЕ ТРЕБОВАНИЯ:
1. СТИЛИСТИКА: Никаких изменений в CSS. Верстка прежняя.
2. ДАННЫЕ: Используй строго предоставленные ниже объекты.
3. ЛОГИКА: Убедись, что поле `category` (если оно есть в твоей схеме) заполняется корректно ("Jewelry", "Bag", "Footwear"). Если поля `category` нет, просто добавь его в объект, чтобы можно было фильтровать.

ДАТА ДЛЯ ИНТЕГРАЦИИ:

[
  // --- CHROME HEARTS (Акцент на Jewelry & Leather Goods) ---
  {
    "id": 1,
    "brand": "Chrome Hearts",
    "name": "Sterling Silver Cross Pendant Necklace",
    "price": 1200,
    "category": "Jewelry",
    "description": "Classic gothic cross pendant crafted in .925 sterling silver with a leather cord."
  },
  {
    "id": 2,
    "brand": "Chrome Hearts",
    "name": "Leather Glove Wallet",
    "price": 850,
    "category": "Accessories",
    "description": "Handmade leather wallet with signature fleur-de-lis hardware and glove-style stitching."
  },
  {
    "id": 3,
    "brand": "Chrome Hearts",
    "name": "Daggers Ring - Size 10",
    "price": 750,
    "category": "Jewelry",
    "description": "Heavyweight sterling silver ring featuring the iconic dagger motif."
  },

  // --- MAISON MARGIELA (Акцент на Avant-Garde & Footwear) ---
  {
    "id": 4,
    "brand": "Maison Margiela",
    "name": "Replica Sneakers",
    "price": 690,
    "category": "Footwear",
    "description": "Iconic low-top sneakers inspired by vintage basketball shoes, featuring distressed white leather and blue accents."
  },
  {
    "id": 5,
    "brand": "Maison Margiela",
    "name": "Tab Boots",
    "price": 1150,
    "category": "Footwear",
    "description": "Ankle boots with distinctive four-stitching detail across the toe box, made from smooth calfskin."
  },
  {
    "id": 6,
    "brand": "Maison Margiela",
    "name": "Glam Slam Puffer Bag",
    "price": 1450,
    "category": "Bags",
    "description": "Quilted nylon shoulder bag with oversized handle and hidden pocket, embodying deconstructed luxury."
  },

  // --- PRADA (Акцент на Minimalism & Tech Fabrics) ---
  {
    "id": 7,
    "brand": "Prada",
    "name": "Re-Nylon Shoulder Bag",
    "price": 1350,
    "category": "Bags",
    "description": "Lightweight shoulder bag crafted from regenerated nylon fabric with the iconic enameled metal triangle logo."
  },
  {
    "id": 8,
    "brand": "Prada",
    "name": "Saffiano Leather Tote",
    "price": 1800,
    "category": "Bags",
    "description": "Structured tote bag made from scratch-resistant Saffiano leather with gold-tone hardware."
  },
  {
    "id": 9,
    "brand": "Prada",
    "name": "Symbole Linea Rossa Sunglasses",
    "price": 450,
    "category": "Eyewear",
    "description": "Sporty acetate sunglasses with red accent details, part of the technical Linea Rossa collection."
  }
]

ИНСТРУКЦИЯ ПО ВЫПОЛНЕНИЮ:
1. Замени старый массив на этот новый (расширенный).
2. Если в компонентах карточек товаров есть логика отображения цены или названия, убедись, что они работают с этими данными без ошибок.
3. Поле `imageUrl` оставь заглушками (`/assets/[brand]/[slug].jpg`) с комментарием `// TODO: Add real image`.
4. Это учебный проект. Фокус на структуре данных и сохранении UI.
