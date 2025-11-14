# Debug Module

This module provides functionality for initializing the application with test data for all domains except offers.

## Features

- **Sequential Independent Steps**: Each initialization step is independent and can be run multiple times safely
- **HTTP-based Initialization**: All data creation goes through HTTP API calls
- **Moscow-oriented Test Data**: Test data is specifically designed for Moscow audience
- **Idempotent Operations**: Can be run multiple times without creating duplicates

## Available Endpoints

### Initialize All Data
```
POST /debug/init-test-data
```
Initializes all test data in sequence:
1. Product categories (main categories and subcategories)
2. Networks (Russian retail chains)
3. Shop points (distributed across Moscow districts)
4. Products (Russian market products)

### Individual Steps

#### Initialize Categories Only
```
POST /debug/init-categories
```
Creates product categories and subcategories.

#### Initialize Networks Only
```
POST /debug/init-networks
```
Creates retail networks (Пятёрочка, Магнит, Лента, etc.).

#### Initialize Shop Points Only
```
POST /debug/init-shop-points
```
Creates shop points for existing networks across Moscow districts.

#### Initialize Products Only
```
POST /debug/init-products
```
Creates products for existing networks with proper category assignments.

### Status Check
```
GET /debug/status
```
Returns current status of initialized data.

## Test Data

### Networks
- Пятёрочка
- Магнит
- Лента
- Перекрёсток
- Ашан

### Product Categories
Main categories include:
- Молочные продукты
- Мясо и птица
- Рыба и морепродукты
- Овощи и фрукты
- Хлеб и выпечка
- Кондитерские изделия
- Напитки
- И другие...

Each main category has relevant subcategories.

### Shop Points
Shop points are distributed across Moscow districts:
- Центральный
- Северный
- Северо-Восточный
- Восточный
- Юго-Восточный
- Южный
- Юго-Западный
- Западный
- Северо-Западный
- Зеленоградский

### Products
Products include typical Russian market items:
- Молочные продукты (молоко, сыр, йогурт, творог, сметана, масло)
- Мясо и птица (говядина, свинина, курица, колбасы)
- Овощи и фрукты (картофель, помидоры, яблоки, зелень)
- Хлеб и выпечка (бородинский хлеб, булочки)
- Напитки (соки, газированные напитки, чай, кофе, вода)

## Usage Examples

### Initialize Everything
```bash
curl -X POST http://localhost:8000/debug/init-test-data
```

### Initialize Step by Step
```bash
# Step 1: Categories
curl -X POST http://localhost:8000/debug/init-categories

# Step 2: Networks
curl -X POST http://localhost:8000/debug/init-networks

# Step 3: Shop Points
curl -X POST http://localhost:8000/debug/init-shop-points

# Step 4: Products
curl -X POST http://localhost:8000/debug/init-products
```

### Check Status
```bash
curl -X GET http://localhost:8000/debug/status
```

## Safety Features

- **Duplicate Prevention**: Checks for existing data before creating new records
- **Error Handling**: Continues processing even if individual items fail
- **Idempotent**: Can be run multiple times safely
- **Independent Steps**: Each step can be run independently
- **HTTP-based**: All operations go through the API, ensuring consistency

## Notes

- All operations are designed to be safe for production environments
- Test data is realistic and appropriate for Moscow market
- The system handles existing data gracefully
- Each step can be run independently without affecting others
