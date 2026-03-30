"""
Модуль для работы с геокодером (OpenStreetMap Nominatim)
"""

import httpx


async def search_address(query: str):
    """
    Поиск адреса через OpenStreetMap Nominatim
    Возвращает список с детальными адресами
    """
    if len(query.strip()) < 3:
        return []
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://nominatim.openstreetmap.org/search",
                params={
                    "q": query,
                    "format": "json",
                    "limit": 5,
                    "addressdetails": 1,
                    "countrycodes": "ru"
                },
                headers={"User-Agent": "TimoFey BackOffice/1.0"},
                timeout=5.0
            )
            
            if response.status_code != 200:
                return []
            
            data = response.json()
            suggestions = []
            for item in data:
                address = item.get("address", {})
                
                # Формируем красивый адрес
                postal_code = address.get("postcode", "")
                city = address.get("city") or address.get("town") or address.get("village") or address.get("municipality", "")
                district = address.get("suburb") or address.get("city_district", "")
                street = address.get("road", "")
                house = address.get("house_number", "")
                
                # Собираем части адреса
                parts = []
                if postal_code:
                    parts.append(postal_code)
                if city:
                    parts.append(city)
                if district:
                    parts.append(district)
                if street:
                    parts.append(f"ул. {street}" if not street.startswith("ул.") else street)
                if house:
                    parts.append(f"д. {house}")
                
                full_address = ", ".join(parts) if parts else item.get("display_name", "")
                
                suggestions.append({
                    "full_address": full_address,
                    "postal_code": postal_code,
                    "city": city,
                    "street": street,
                    "house": house,
                    "raw_address": item.get("display_name", "")
                })
            
            return suggestions
    except Exception as e:
        print(f"Ошибка геокодирования: {e}")
        return []


async def get_address_details(address: str):
    """
    Получение детальной информации об адресе
    """
    if len(address.strip()) < 3:
        return None
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://nominatim.openstreetmap.org/search",
                params={
                    "q": address,
                    "format": "json",
                    "limit": 1,
                    "addressdetails": 1,
                    "countrycodes": "ru"
                },
                headers={"User-Agent": "TimoFey BackOffice/1.0"},
                timeout=5.0
            )
            
            if response.status_code != 200:
                return None
            
            data = response.json()
            if not data:
                return None
            
            item = data[0]
            address_details = item.get("address", {})
            
            return {
                "full_address": item.get("display_name", ""),
                "postal_code": address_details.get("postcode", ""),
                "city": address_details.get("city") or address_details.get("town") or address_details.get("village", ""),
                "street": address_details.get("road", ""),
                "house": address_details.get("house_number", "")
            }
    except Exception as e:
        print(f"Ошибка получения деталей адреса: {e}")
        return None