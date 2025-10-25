import asyncio
import httpx
from typing import List, Dict, Any
from app.sellers.schemas import SellerCreate
from app.shop_points.schemas import ShopPointCreate
from app.products.schemas import ProductCreate
from app.product_categories.schemas import ProductCategoryCreate
from app.inventory.schemas import ProductEntryCreate


class DebugDataInitializer:
    """Class for initializing test data through HTTP requests"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.client = httpx.AsyncClient()
        self.created_data = {
            "sellers": [],
            "shop_points": [],
            "categories": [],
            "products": [],
            "inventory_entries": []
        }
    
    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()
    
    async def clear_all_data(self) -> Dict[str, Any]:
        """Clear all data from the database"""
        cleared_entities = {
            "products": 0,
            "shop_points": 0,
            "sellers": 0,
            "categories": 0,
            "inventory_entries": 0
        }
        
        try:
            # Clear products first (due to foreign key constraints)
            products_response = await self.client.get(f"{self.base_url}/products/")
            if products_response.is_success:
                products = products_response.json()
                for product in products:
                    await self.client.delete(f"{self.base_url}/products/{product['id']}")
                cleared_entities["products"] = len(products)
            
            # Clear shop points
            shop_points_response = await self.client.get(f"{self.base_url}/shop-points/")
            if shop_points_response.is_success:
                shop_points = shop_points_response.json()
                for shop_point in shop_points:
                    await self.client.delete(f"{self.base_url}/shop-points/{shop_point['id']}")
                cleared_entities["shop_points"] = len(shop_points)
            
            # Clear sellers
            sellers_response = await self.client.get(f"{self.base_url}/sellers/")
            if sellers_response.is_success:
                sellers = sellers_response.json()
                for seller in sellers:
                    await self.client.delete(f"{self.base_url}/sellers/{seller['id']}")
                cleared_entities["sellers"] = len(sellers)
            
            # Clear categories
            categories_response = await self.client.get(f"{self.base_url}/product-categories/")
            if categories_response.is_success:
                categories = categories_response.json()
                for category in categories:
                    await self.client.delete(f"{self.base_url}/product-categories/{category['id']}")
                cleared_entities["categories"] = len(categories)
            
            return cleared_entities
            
        except Exception as e:
            raise Exception(f"Failed to clear database: {str(e)}")
    
    async def get_or_create_sellers(self) -> List[Dict[str, Any]]:
        """Get existing sellers or create test sellers"""
        sellers_data = [
            {
                "email": "pyaterochka@example.com",
                "phone": "+79001234567",
                "full_name": "ООО Пятёрочка",
                "short_name": "Пятёрочка",
                "inn": "1234567890",
                "org_type": 1,
                "ogrn": "1234567890123",
                "master_id": 1,
                "status": 1,
                "verification_level": 2,
                "registration_doc_url": "https://example.com/docs/pyaterochka.pdf"
            },
            {
                "email": "magnit@example.com",
                "phone": "+79001234568",
                "full_name": "ООО Магнит",
                "short_name": "Магнит",
                "inn": "1234567891",
                "org_type": 1,
                "ogrn": "1234567890124",
                "master_id": 2,
                "status": 1,
                "verification_level": 2,
                "registration_doc_url": "https://example.com/docs/magnit.pdf"
            },
            {
                "email": "lenta@example.com",
                "phone": "+79001234569",
                "full_name": "ООО Лента",
                "short_name": "Лента",
                "inn": "1234567892",
                "org_type": 1,
                "ogrn": "1234567890125",
                "master_id": 3,
                "status": 1,
                "verification_level": 2,
                "registration_doc_url": "https://example.com/docs/lenta.pdf"
            }
        ]
        
        # First, try to get existing sellers
        try:
            response = await self.client.get(f"{self.base_url}/sellers/")
            if response.is_success:
                try:
                    existing_sellers = response.json()
                    print(f"📡 Found {len(existing_sellers)} existing sellers")
                    
                    # Check if we have all required sellers
                    existing_emails = {seller['email'] for seller in existing_sellers}
                    required_emails = {seller['email'] for seller in sellers_data}
                    
                    if required_emails.issubset(existing_emails):
                        print("✅ All required sellers already exist")
                        self.created_data["sellers"] = existing_sellers
                        return existing_sellers
                    else:
                        print("⚠️ Some sellers missing, will create missing ones")
                except Exception as json_error:
                    print(f"⚠️ Failed to parse sellers JSON: {json_error}")
                    print(f"Response text: {response.text}")
            else:
                print(f"⚠️ Failed to fetch sellers: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"⚠️ Could not fetch existing sellers: {e}")
        
        # Create missing sellers
        created_sellers = []
        for seller_data in sellers_data:
            try:
                # Try to create seller
                response = await self.client.post(
                    f"{self.base_url}/sellers/",
                    json=seller_data
                )
                if response.is_success:
                    seller = response.json()
                    created_sellers.append(seller)
                    self.created_data["sellers"].append(seller)
                    print(f"✅ Created seller: {seller['full_name']} (ID: {seller['id']})")
                elif response.status_code == 400 and ("UNIQUE constraint" in response.text or "already exists" in response.text):
                    # Seller already exists, try to find it
                    print(f"⚠️ Seller {seller_data['full_name']} already exists, fetching...")
                    try:
                        # Try to get by email
                        email_response = await self.client.get(f"{self.base_url}/sellers/email/{seller_data['email']}")
                        if email_response.is_success:
                            seller = email_response.json()
                            created_sellers.append(seller)
                            self.created_data["sellers"].append(seller)
                            print(f"✅ Found existing seller: {seller['full_name']} (ID: {seller['id']})")
                        else:
                            print(f"❌ Failed to fetch seller by email: {email_response.status_code} - {email_response.text}")
                    except Exception as e:
                        print(f"❌ Could not fetch existing seller {seller_data['full_name']}: {e}")
                else:
                    print(f"❌ Failed to create seller {seller_data['full_name']}: {response.status_code} - {response.text}")
            except Exception as e:
                print(f"❌ Error with seller {seller_data['full_name']}: {e}")
        
        return created_sellers
    
    async def get_or_create_categories(self) -> List[Dict[str, Any]]:
        """Get existing categories or create test product categories"""
        categories_data = [
            {"name": "Молочные продукты", "slug": "dairy-products"},
            {"name": "Хлебобулочные изделия", "slug": "bakery"},
            {"name": "Мясо и птица", "slug": "meat-poultry"},
            {"name": "Овощи и фрукты", "slug": "vegetables-fruits"},
            {"name": "Напитки", "slug": "beverages"},
            {"name": "Кондитерские изделия", "slug": "confectionery"},
            {"name": "Замороженные продукты", "slug": "frozen-foods"},
            {"name": "Крупы и макароны", "slug": "cereals-pasta"}
        ]
        
        # First, try to get existing categories
        try:
            response = await self.client.get(f"{self.base_url}/product-categories/")
            if response.is_success:
                try:
                    existing_categories = response.json()
                    print(f"📂 Found {len(existing_categories)} existing categories")
                    
                    # Check if we have all required categories
                    existing_slugs = {cat['slug'] for cat in existing_categories}
                    required_slugs = {cat['slug'] for cat in categories_data}
                    
                    if required_slugs.issubset(existing_slugs):
                        print("✅ All required categories already exist")
                        self.created_data["categories"] = existing_categories
                        return existing_categories
                    else:
                        print("⚠️ Some categories missing, will create missing ones")
                except Exception as json_error:
                    print(f"⚠️ Failed to parse categories JSON: {json_error}")
                    print(f"Response text: {response.text}")
            else:
                print(f"⚠️ Failed to fetch categories: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"⚠️ Could not fetch existing categories: {e}")
        
        # Create missing categories
        created_categories = []
        for category_data in categories_data:
            try:
                # Try to create category
                response = await self.client.post(
                    f"{self.base_url}/product-categories/",
                    json=category_data
                )
                if response.is_success:
                    category = response.json()
                    created_categories.append(category)
                    self.created_data["categories"].append(category)
                    print(f"✅ Created category: {category['name']} (ID: {category['id']})")
                elif response.status_code == 400 and ("UNIQUE constraint" in response.text or "already exists" in response.text):
                    # Category already exists, try to find it
                    print(f"⚠️ Category {category_data['name']} already exists, fetching...")
                    try:
                        # Try to get by slug
                        slug_response = await self.client.get(f"{self.base_url}/product-categories/slug/{category_data['slug']}")
                        if slug_response.is_success:
                            category = slug_response.json()
                            created_categories.append(category)
                            self.created_data["categories"].append(category)
                            print(f"✅ Found existing category: {category['name']} (ID: {category['id']})")
                        else:
                            print(f"❌ Failed to fetch category by slug: {slug_response.status_code} - {slug_response.text}")
                    except Exception as e:
                        print(f"❌ Could not fetch existing category {category_data['name']}: {e}")
                else:
                    print(f"❌ Failed to create category {category_data['name']}: {response.text}")
            except Exception as e:
                print(f"❌ Error with category {category_data['name']}: {e}")
        
        return created_categories
    
    async def get_or_create_shop_points(self, sellers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Get existing shop points or create test shop points for each seller"""
        if not sellers or len(sellers) < 3:
            print("❌ Not enough sellers to create shop points")
            return []
        
        # First, try to get existing shop points
        try:
            response = await self.client.get(f"{self.base_url}/shop-points/")
            if response.is_success:
                try:
                    existing_shop_points = response.json()
                    print(f"🏪 Found {len(existing_shop_points)} existing shop points")
                    
                    # Check if we have shop points for all sellers
                    seller_ids = {seller['id'] for seller in sellers}
                    existing_seller_ids = {sp['seller_id'] for sp in existing_shop_points}
                    
                    if seller_ids.issubset(existing_seller_ids):
                        print("✅ All sellers have shop points")
                        self.created_data["shop_points"] = existing_shop_points
                        return existing_shop_points
                    else:
                        print("⚠️ Some sellers missing shop points, will create missing ones")
                except Exception as json_error:
                    print(f"⚠️ Failed to parse shop points JSON: {json_error}")
                    print(f"Response text: {response.text}")
            else:
                print(f"⚠️ Failed to fetch shop points: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"⚠️ Could not fetch existing shop points: {e}")
        
        # Create shop points for each seller
        shop_points_data = [
            # Пятёрочка
            {"seller_id": sellers[0]["id"], "latitude": 55.7558, "longitude": 37.6176},
            {"seller_id": sellers[0]["id"], "latitude": 55.7658, "longitude": 37.6276},
            {"seller_id": sellers[0]["id"], "latitude": 55.7458, "longitude": 37.6076},
            
            # Магнит
            {"seller_id": sellers[1]["id"], "latitude": 55.7558, "longitude": 37.6176},
            {"seller_id": sellers[1]["id"], "latitude": 55.7658, "longitude": 37.6276},
            
            # Лента
            {"seller_id": sellers[2]["id"], "latitude": 55.7558, "longitude": 37.6176},
            {"seller_id": sellers[2]["id"], "latitude": 55.7658, "longitude": 37.6276},
            {"seller_id": sellers[2]["id"], "latitude": 55.7458, "longitude": 37.6076},
        ]
        
        created_shop_points = []
        for shop_point_data in shop_points_data:
            try:
                response = await self.client.post(
                    f"{self.base_url}/shop-points/",
                    json=shop_point_data
                )
                if response.is_success:
                    shop_point = response.json()
                    created_shop_points.append(shop_point)
                    self.created_data["shop_points"].append(shop_point)
                    print(f"✅ Created shop point for network {shop_point_data['network_id']} (ID: {shop_point['id']})")
                else:
                    print(f"❌ Failed to create shop point: {response.text}")
            except Exception as e:
                print(f"❌ Error creating shop point: {e}")
        
        return created_shop_points
    
    async def get_or_create_products(self, sellers: List[Dict[str, Any]], categories: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Get existing products or create test products"""
        if not sellers or len(sellers) < 3 or not categories or len(categories) < 6:
            print("❌ Not enough sellers or categories to create products")
            return []
        
        # First, try to get existing products
        try:
            response = await self.client.get(f"{self.base_url}/products/")
            if response.is_success:
                try:
                    existing_products = response.json()
                    print(f"🛍️ Found {len(existing_products)} existing products")
                    
                    # Check if we have products for all sellers
                    seller_ids = {seller['id'] for seller in sellers}
                    existing_seller_ids = {prod['seller_id'] for prod in existing_products}
                    
                    if seller_ids.issubset(existing_seller_ids):
                        print("✅ All sellers have products")
                        self.created_data["products"] = existing_products
                        return existing_products
                    else:
                        print("⚠️ Some sellers missing products, will create missing ones")
                except Exception as json_error:
                    print(f"⚠️ Failed to parse products JSON: {json_error}")
                    print(f"Response text: {response.text}")
            else:
                print(f"⚠️ Failed to fetch products: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"⚠️ Could not fetch existing products: {e}")
        
        # Create products
        products_data = [
            # Молочные продукты
            {
                "name": "Молоко Домик в деревне 3.2%",
                "description": "Свежее пастеризованное молоко",
                "article": "MILK001",
                "code": "1234567890123",
                "seller_id": sellers[0]["id"],
                "category_ids": [categories[0]["id"]]
            },
            {
                "name": "Кефир Простоквашино 2.5%",
                "description": "Натуральный кефир",
                "article": "KEFIR001",
                "code": "1234567890124",
                "seller_id": sellers[1]["id"],
                "category_ids": [categories[0]["id"]]
            },
            {
                "name": "Сыр Российский 45%",
                "description": "Твёрдый сыр российского производства",
                "article": "CHEESE001",
                "code": "1234567890125",
                "seller_id": sellers[2]["id"],
                "category_ids": [categories[0]["id"]]
            },
            
            # Хлебобулочные изделия
            {
                "name": "Хлеб Бородинский",
                "description": "Ржаной хлеб с кориандром",
                "article": "BREAD001",
                "code": "1234567890126",
                "seller_id": sellers[0]["id"],
                "category_ids": [categories[1]["id"]]
            },
            {
                "name": "Булочки с маком",
                "description": "Сдобные булочки с маковой начинкой",
                "article": "BUN001",
                "code": "1234567890127",
                "seller_id": sellers[1]["id"],
                "category_ids": [categories[1]["id"]]
            },
            
            # Мясо и птица
            {
                "name": "Курица охлаждённая",
                "description": "Свежая курица без костей",
                "article": "CHICKEN001",
                "code": "1234567890128",
                "seller_id": sellers[2]["id"],
                "category_ids": [categories[2]["id"]]
            },
            {
                "name": "Говядина вырезка",
                "description": "Премиальная говяжья вырезка",
                "article": "BEEF001",
                "code": "1234567890129",
                "seller_id": sellers[2]["id"],
                "category_ids": [categories[2]["id"]]
            },
            
            # Овощи и фрукты
            {
                "name": "Помидоры черри",
                "description": "Сладкие помидоры черри",
                "article": "TOMATO001",
                "code": "1234567890130",
                "seller_id": sellers[0]["id"],
                "category_ids": [categories[3]["id"]]
            },
            {
                "name": "Яблоки Гренни Смит",
                "description": "Зелёные кисло-сладкие яблоки",
                "article": "APPLE001",
                "code": "1234567890131",
                "seller_id": sellers[1]["id"],
                "category_ids": [categories[3]["id"]]
            },
            
            # Напитки
            {
                "name": "Сок апельсиновый 1л",
                "description": "100% апельсиновый сок",
                "article": "JUICE001",
                "code": "1234567890132",
                "seller_id": sellers[2]["id"],
                "category_ids": [categories[4]["id"]]
            },
            {
                "name": "Вода минеральная 0.5л",
                "description": "Природная минеральная вода",
                "article": "WATER001",
                "code": "1234567890133",
                "seller_id": sellers[2]["id"],
                "category_ids": [categories[4]["id"]]
            },
            
            # Кондитерские изделия
            {
                "name": "Шоколад молочный",
                "description": "Молочный шоколад с орехами",
                "article": "CHOCOLATE001",
                "code": "1234567890134",
                "seller_id": sellers[2]["id"],
                "category_ids": [categories[5]["id"]]
            },
            {
                "name": "Печенье овсяное",
                "description": "Домашнее овсяное печенье",
                "article": "COOKIE001",
                "code": "1234567890135",
                "seller_id": sellers[0]["id"],
                "category_ids": [categories[5]["id"]]
            }
        ]
        
        created_products = []
        for product_data in products_data:
            try:
                response = await self.client.post(
                    f"{self.base_url}/products/",
                    json=product_data
                )
                if response.is_success:
                    product = response.json()
                    created_products.append(product)
                    self.created_data["products"].append(product)
                    print(f"✅ Created product: {product['name']} (ID: {product['id']})")
                else:
                    print(f"❌ Failed to create product {product_data['name']}: {response.text}")
            except Exception as e:
                print(f"❌ Error creating product {product_data['name']}: {e}")
        
        return created_products
    
    async def get_or_create_inventory_entries(self, products: List[Dict[str, Any]], shop_points: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Get existing inventory entries or create test inventory entries"""
        if not products or not shop_points:
            print("❌ Not enough products or shop points to create inventory entries")
            return []
        
        # First, try to get existing inventory entries
        try:
            response = await self.client.get(f"{self.base_url}/inventory/")
            if response.is_success:
                try:
                    existing_entries = response.json()
                    print(f"📦 Found {len(existing_entries)} existing inventory entries")
                    
                    # Check if we have entries for all products
                    product_ids = {prod['id'] for prod in products}
                    existing_product_ids = {entry['product_id'] for entry in existing_entries}
                    
                    if product_ids.issubset(existing_product_ids):
                        print("✅ All products have inventory entries")
                        self.created_data["inventory_entries"] = existing_entries
                        return existing_entries
                    else:
                        print("⚠️ Some products missing inventory entries, will create missing ones")
                except Exception as json_error:
                    print(f"⚠️ Failed to parse inventory entries JSON: {json_error}")
                    print(f"Response text: {response.text}")
            else:
                print(f"⚠️ Failed to fetch inventory entries: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"⚠️ Could not fetch existing inventory entries: {e}")
        
        # Create inventory entries
        from datetime import datetime, timedelta
        import random
        
        inventory_entries_data = []
        
        # Create inventory entries for each product in different shop points
        for product in products:
            # Select 2-3 random shop points for each product
            selected_shop_points = random.sample(shop_points, min(3, len(shop_points)))
            
            for shop_point in selected_shop_points:
                # Random expiration date (1-30 days from now)
                expires_date = datetime.now() + timedelta(days=random.randint(1, 30))
                
                entry_data = {
                    "product_id": product["id"],
                    "shop_id": shop_point["id"],
                    "expires_date": expires_date.isoformat(),
                    "original_cost": round(random.uniform(50, 500), 2),
                    "current_cost": round(random.uniform(30, 400), 2),
                    "count": random.randint(1, 100)
                }
                inventory_entries_data.append(entry_data)
        
        created_entries = []
        for entry_data in inventory_entries_data:
            try:
                response = await self.client.post(
                    f"{self.base_url}/inventory/",
                    json=entry_data
                )
                if response.is_success:
                    entry = response.json()
                    created_entries.append(entry)
                    self.created_data["inventory_entries"].append(entry)
                    print(f"✅ Created inventory entry for product {entry_data['product_id']} in shop {entry_data['shop_id']}")
                else:
                    print(f"❌ Failed to create inventory entry: {response.text}")
            except Exception as e:
                print(f"❌ Error creating inventory entry: {e}")
        
        return created_entries
    
    async def initialize_all_data(self):
        """Initialize all test data"""
        print("🚀 Starting test data initialization...")
        
        try:
            # Get or create sellers
            print("\n📡 Getting or creating sellers...")
            sellers = await self.get_or_create_sellers()
            
            if not sellers:
                print("❌ Failed to get or create sellers. Stopping initialization.")
                return None
            
            # Get or create categories
            print("\n📂 Getting or creating product categories...")
            categories = await self.get_or_create_categories()
            
            if not categories:
                print("❌ Failed to get or create categories. Stopping initialization.")
                return None
            
            # Get or create shop points
            print("\n🏪 Getting or creating shop points...")
            shop_points = await self.get_or_create_shop_points(sellers)
            
            if not shop_points:
                print("❌ Failed to get or create shop points. Stopping initialization.")
                return None
            
            # Get or create products
            print("\n🛍️ Getting or creating products...")
            products = await self.get_or_create_products(sellers, categories)
            
            if not products:
                print("❌ Failed to get or create products. Stopping initialization.")
                return None
            
            # Get or create inventory entries
            print("\n📦 Getting or creating inventory entries...")
            inventory_entries = await self.get_or_create_inventory_entries(products, shop_points)
            
            print(f"\n✅ Test data initialization completed!")
            print(f"📊 Summary:")
            print(f"   - Sellers: {len(sellers)}")
            print(f"   - Categories: {len(categories)}")
            print(f"   - Shop points: {len(shop_points)}")
            print(f"   - Products: {len(products)}")
            print(f"   - Inventory entries: {len(inventory_entries)}")
            
            return self.created_data
            
        except Exception as e:
            print(f"❌ Error during initialization: {e}")
            raise
        finally:
            await self.close()
    
    def print_created_data_summary(self):
        """Print summary of created data"""
        print("\n📋 Created Data Summary:")
        for data_type, items in self.created_data.items():
            print(f"   {data_type.replace('_', ' ').title()}: {len(items)}")
            for item in items[:3]:  # Show first 3 items
                if 'name' in item:
                    print(f"     - {item['name']} (ID: {item['id']})")
                elif 'id' in item:
                    print(f"     - ID: {item['id']}")
            if len(items) > 3:
                print(f"     ... and {len(items) - 3} more")


async def main():
    """Main function to run the initialization"""
    initializer = DebugDataInitializer()
    try:
        await initializer.initialize_all_data()
        initializer.print_created_data_summary()
    except Exception as e:
        print(f"❌ Initialization failed: {e}")


if __name__ == "__main__":
    asyncio.run(main())
