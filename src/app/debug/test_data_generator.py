"""Test data generator for Moscow audience"""

from typing import List, Dict, Any
import random


class TestDataGenerator:
    """Generator for test data oriented on Moscow audience"""

    # Moscow-based networks
    NETWORKS_DATA = [
        {
            "name": "Пятёрочка",
            "slug": "pyaterochka"
        },
        {
            "name": "Магнит",
            "slug": "magnit"
        },
        {
            "name": "Лента",
            "slug": "lenta"
        },
        {
            "name": "Перекрёсток",
            "slug": "perekrestok"
        },
        {
            "name": "Ашан",
            "slug": "auchan"
        }
    ]

    # Moscow districts and coordinates
    MOSCOW_DISTRICTS = [
        {"name": "Центральный", "lat": 55.7558, "lng": 37.6176},
        {"name": "Северный", "lat": 55.8500, "lng": 37.5500},
        {"name": "Северо-Восточный", "lat": 55.8500, "lng": 37.6500},
        {"name": "Восточный", "lat": 55.7500, "lng": 37.7500},
        {"name": "Юго-Восточный", "lat": 55.6500, "lng": 37.7500},
        {"name": "Южный", "lat": 55.6500, "lng": 37.6500},
        {"name": "Юго-Западный", "lat": 55.6500, "lng": 37.5500},
        {"name": "Западный", "lat": 55.7500, "lng": 37.5500},
        {"name": "Северо-Западный", "lat": 55.8500, "lng": 37.4500},
        {"name": "Зеленоградский", "lat": 55.9833, "lng": 37.1833}
    ]

    # Product categories for Russian market
    CATEGORIES_DATA = [
        # Main categories
        {"name": "Молочные продукты", "slug": "milk-products"},
        {"name": "Мясо и птица", "slug": "meat-poultry"},
        {"name": "Рыба и морепродукты", "slug": "fish-seafood"},
        {"name": "Овощи и фрукты", "slug": "vegetables-fruits"},
        {"name": "Хлеб и выпечка", "slug": "bread-bakery"},
        {"name": "Кондитерские изделия", "slug": "confectionery"},
        {"name": "Напитки", "slug": "beverages"},
        {"name": "Замороженные продукты", "slug": "frozen-foods"},
        {"name": "Консервы", "slug": "canned-goods"},
        {"name": "Крупы и макароны", "slug": "cereals-pasta"},
        {"name": "Специи и приправы", "slug": "spices-seasonings"},
        {"name": "Детское питание", "slug": "baby-food"},
        {"name": "Здоровое питание", "slug": "healthy-food"},
        {"name": "Алкоголь", "slug": "alcohol"},
        {"name": "Товары для дома", "slug": "household-goods"}
    ]

    # Subcategories
    SUBCATEGORIES_DATA = [
        # Молочные продукты
        {"name": "Молоко", "slug": "milk", "parent_slug": "milk-products"},
        {"name": "Сыр", "slug": "cheese", "parent_slug": "milk-products"},
        {"name": "Йогурт", "slug": "yogurt", "parent_slug": "milk-products"},
        {"name": "Творог", "slug": "cottage-cheese", "parent_slug": "milk-products"},
        {"name": "Сметана", "slug": "sour-cream", "parent_slug": "milk-products"},
        {"name": "Масло", "slug": "butter", "parent_slug": "milk-products"},
        
        # Мясо и птица
        {"name": "Говядина", "slug": "beef", "parent_slug": "meat-poultry"},
        {"name": "Свинина", "slug": "pork", "parent_slug": "meat-poultry"},
        {"name": "Курица", "slug": "chicken", "parent_slug": "meat-poultry"},
        {"name": "Индейка", "slug": "turkey", "parent_slug": "meat-poultry"},
        {"name": "Колбасы", "slug": "sausages", "parent_slug": "meat-poultry"},
        
        # Овощи и фрукты
        {"name": "Свежие овощи", "slug": "fresh-vegetables", "parent_slug": "vegetables-fruits"},
        {"name": "Свежие фрукты", "slug": "fresh-fruits", "parent_slug": "vegetables-fruits"},
        {"name": "Зелень", "slug": "greens", "parent_slug": "vegetables-fruits"},
        
        # Хлеб и выпечка
        {"name": "Хлеб", "slug": "bread", "parent_slug": "bread-bakery"},
        {"name": "Булочки", "slug": "buns", "parent_slug": "bread-bakery"},
        {"name": "Пироги", "slug": "pies", "parent_slug": "bread-bakery"},
        
        # Напитки
        {"name": "Соки", "slug": "juices", "parent_slug": "beverages"},
        {"name": "Газированные напитки", "slug": "soft-drinks", "parent_slug": "beverages"},
        {"name": "Чай", "slug": "tea", "parent_slug": "beverages"},
        {"name": "Кофе", "slug": "coffee", "parent_slug": "beverages"},
        {"name": "Минеральная вода", "slug": "mineral-water", "parent_slug": "beverages"}
    ]

    # Russian products
    PRODUCTS_DATA = [
        # Молочные продукты
        {"name": "Молоко Домик в деревне 3.2%", "description": "Свежее пастеризованное молоко", "article": "MILK001", "code": "123456", "category_slugs": ["milk"]},
        {"name": "Сыр Российский 45%", "description": "Твёрдый сыр российского производства", "article": "CHEESE001", "code": "123457", "category_slugs": ["cheese"]},
        {"name": "Йогурт Активия натуральный", "description": "Йогурт с пробиотиками", "article": "YOGURT001", "code": "123458", "category_slugs": ["yogurt"]},
        {"name": "Творог 9% жирности", "description": "Творог классический", "article": "COTTAGE001", "code": "123459", "category_slugs": ["cottage-cheese"]},
        {"name": "Сметана 20%", "description": "Сметана классическая", "article": "SOUR001", "code": "123460", "category_slugs": ["sour-cream"]},
        {"name": "Масло сливочное 82.5%", "description": "Сливочное масло высшего сорта", "article": "BUTTER001", "code": "123461", "category_slugs": ["butter"]},
        
        # Мясо и птица
        {"name": "Говядина вырезка", "description": "Свежая говяжья вырезка", "article": "BEEF001", "code": "123462", "category_slugs": ["beef"]},
        {"name": "Свинина корейка", "description": "Свежая свиная корейка", "article": "PORK001", "code": "123463", "category_slugs": ["pork"]},
        {"name": "Курица целая", "description": "Охлаждённая курица", "article": "CHICKEN001", "code": "123464", "category_slugs": ["chicken"]},
        {"name": "Колбаса Докторская", "description": "Варёная колбаса высшего сорта", "article": "SAUSAGE001", "code": "123465", "category_slugs": ["sausages"]},
        
        # Овощи и фрукты
        {"name": "Картофель молодой", "description": "Свежий молодой картофель", "article": "POTATO001", "code": "123466", "category_slugs": ["fresh-vegetables"]},
        {"name": "Помидоры черри", "description": "Свежие помидоры черри", "article": "TOMATO001", "code": "123467", "category_slugs": ["fresh-vegetables"]},
        {"name": "Яблоки Гренни Смит", "description": "Свежие зелёные яблоки", "article": "APPLE001", "code": "123468", "category_slugs": ["fresh-fruits"]},
        {"name": "Укроп свежий", "description": "Свежая зелень укропа", "article": "DILL001", "code": "123469", "category_slugs": ["greens"]},
        
        # Хлеб и выпечка
        {"name": "Хлеб Бородинский", "description": "Ржаной хлеб с тмином", "article": "BREAD001", "code": "123470", "category_slugs": ["bread"]},
        {"name": "Булочки с маком", "description": "Сдобные булочки с маком", "article": "BUNS001", "code": "123471", "category_slugs": ["buns"]},
        
        # Напитки
        {"name": "Сок яблочный 100%", "description": "Натуральный яблочный сок", "article": "JUICE001", "code": "123472", "category_slugs": ["juices"]},
        {"name": "Кока-Кола 0.5л", "description": "Газированный напиток", "article": "COLA001", "code": "123473", "category_slugs": ["soft-drinks"]},
        {"name": "Чай Липтон чёрный", "description": "Чёрный чай в пакетиках", "article": "TEA001", "code": "123474", "category_slugs": ["tea"]},
        {"name": "Кофе Нескафе Голд", "description": "Растворимый кофе", "article": "COFFEE001", "code": "123475", "category_slugs": ["coffee"]},
        {"name": "Вода Боржоми 0.5л", "description": "Минеральная вода", "article": "WATER001", "code": "123476", "category_slugs": ["mineral-water"]}
    ]

    @classmethod
    def get_networks_data(cls) -> List[Dict[str, str]]:
        """Get networks data"""
        return cls.NETWORKS_DATA.copy()

    @classmethod
    def get_categories_data(cls) -> List[Dict[str, str]]:
        """Get main categories data"""
        return cls.CATEGORIES_DATA.copy()

    @classmethod
    def get_subcategories_data(cls) -> List[Dict[str, str]]:
        """Get subcategories data"""
        return cls.SUBCATEGORIES_DATA.copy()

    @classmethod
    def get_products_data(cls) -> List[Dict[str, Any]]:
        """Get products data"""
        return cls.PRODUCTS_DATA.copy()

    @classmethod
    def get_shop_points_data(cls, network_count: int) -> List[Dict[str, Any]]:
        """Generate shop points data for given number of networks"""
        shop_points = []
        
        for network_idx in range(network_count):
            # Each network gets 2-5 shop points
            points_count = random.randint(2, 5)
            
            for point_idx in range(points_count):
                district = random.choice(cls.MOSCOW_DISTRICTS)
                # Add some random variation to coordinates
                lat = district["lat"] + random.uniform(-0.01, 0.01)
                lng = district["lng"] + random.uniform(-0.01, 0.01)
                
                shop_points.append({
                    "network_id": network_idx + 1,  # Will be updated with actual IDs
                    "latitude": round(lat, 6),
                    "longitude": round(lng, 6)
                })
        
        return shop_points

    @classmethod
    def get_random_products_for_network(cls, network_id: int, count: int = None) -> List[Dict[str, Any]]:
        """Get random products for a specific network"""
        if count is None:
            count = random.randint(5, 15)  # 5-15 products per network
        
        selected_products = random.sample(cls.PRODUCTS_DATA, min(count, len(cls.PRODUCTS_DATA)))
        
        # Add network_id to each product
        for product in selected_products:
            product["network_id"] = network_id
        
        return selected_products
