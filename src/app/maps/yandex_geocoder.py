import httpx
from typing import Optional, Dict, Any
from logger import get_logger
from config import settings

logger = get_logger(__name__)


class GeocodeResult:
    """Result from geocoding operation"""
    
    def __init__(
        self,
        formatted_address: str,
        address_raw: Optional[str] = None,
        region: Optional[str] = None,
        city: Optional[str] = None,
        street: Optional[str] = None,
        house: Optional[str] = None,
        geo_id: Optional[str] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None
    ):
        self.formatted_address = formatted_address
        self.address_raw = address_raw
        self.region = region
        self.city = city
        self.street = street
        self.house = house
        self.geo_id = geo_id
        self.latitude = latitude
        self.longitude = longitude


class YandexGeocoder:
    """Client for Yandex Geocoder API"""
    
    def __init__(self, api_key: str, base_url: str = "https://geocode-maps.yandex.ru/v1"):
        self.api_key = api_key
        self.base_url = base_url
        self.client = httpx.AsyncClient(
            timeout=10.0,
            headers={"Referer": "https://gembos.ru"}
        )
    
    async def geocode_address(self, address: str) -> Optional[GeocodeResult]:
        """Geocode an address string to get location and address components"""
        params = {
            "apikey": self.api_key,
            "geocode": address,
            "format": "json",
            "lang": "ru_RU",
            "results": 1
        }
        
        response = await self.client.get(self.base_url, params=params)
        response.raise_for_status()
        
        data = response.json()
        await logger.info(f"Geocoding response for '{address}'", extra={"data": data})
        
        return self._parse_geocoder_response(data)
    
    async def reverse_geocode(self, longitude: float, latitude: float) -> Optional[GeocodeResult]:
        """Reverse geocode coordinates to get address"""
        coords = f"{longitude},{latitude}"
        params = {
            "apikey": self.api_key,
            "geocode": coords,
            "format": "json",
            "lang": "ru_RU",
            "results": 1
        }
        
        response = await self.client.get(self.base_url, params=params)
        response.raise_for_status()
        
        data = response.json()
        await logger.info(f"Reverse geocoding response for ({longitude}, {latitude})", extra={"data": data})
        
        result = self._parse_geocoder_response(data)
        
        if result and not result.longitude:
            result.longitude = longitude
            result.latitude = latitude
        
        return result
    
    def _parse_geocoder_response(self, data: Dict[str, Any]) -> Optional[GeocodeResult]:
        """Parse Yandex Geocoder API response"""
        response = data.get("response", {})
        geo_object_collection = response.get("GeoObjectCollection", {})
        feature_members = geo_object_collection.get("featureMember", [])
        
        if not feature_members:
            return None
        
        geo_object = feature_members[0].get("GeoObject", {})
        
        meta_data_property = geo_object.get("metaDataProperty", {})
        geocoder_meta_data = meta_data_property.get("GeocoderMetaData", {})
        formatted_address = geocoder_meta_data.get("text", "")
        
        address_details = geocoder_meta_data.get("AddressDetails", {})
        country = address_details.get("Country", {})
        administrative_area = country.get("AdministrativeArea", {})
        
        region = administrative_area.get("AdministrativeAreaName", "")
        
        sub_admin_area = administrative_area.get("SubAdministrativeArea", {})
        locality = sub_admin_area.get("Locality", {})
        
        if not locality:
            locality = administrative_area.get("Locality", {})
        
        city = locality.get("LocalityName", "")
        
        thoroughfare = locality.get("Thoroughfare", {})
        street = thoroughfare.get("ThoroughfareName", "")
        premise = thoroughfare.get("Premise", {})
        house = premise.get("PremiseNumber", "")
        
        geo_id = geo_object.get("uri", "")
        
        point = geo_object.get("Point", {})
        pos = point.get("pos", "")
        
        longitude, latitude = None, None
        if pos:
            lon, lat = pos.split()
            longitude = float(lon)
            latitude = float(lat)
        
        return GeocodeResult(
            formatted_address=formatted_address,
            address_raw=formatted_address,
            region=region if region else None,
            city=city if city else None,
            street=street if street else None,
            house=house if house else None,
            geo_id=geo_id if geo_id else None,
            latitude=latitude,
            longitude=longitude
        )
    
    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()
    
    async def __aenter__(self):
        """Async context manager entry"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()


def create_geocoder(api_key: Optional[str] = None) -> YandexGeocoder:
    """
    Create a YandexGeocoder instance
    
    Args:
        api_key: Optional API key. If not provided, will use settings.yandex_map_api_key
        
    Returns:
        YandexGeocoder instance
    """
    if api_key is None:
        api_key = settings.yandex_map_api_key
    
    return YandexGeocoder(api_key)
