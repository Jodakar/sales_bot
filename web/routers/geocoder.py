from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent.parent))
from bot.utils.geocoder import search_address, get_address_details

router = APIRouter()


class AddressRequest(BaseModel):
    query: str


@router.post("/search")
async def search_address_api(request: AddressRequest):
    """Поиск адреса по запросу"""
    if not request.query or len(request.query.strip()) < 3:
        return []
    
    suggestions = await search_address(request.query)
    return suggestions


@router.get("/details")
async def get_address_details_api(address: str):
    """Получение деталей адреса"""
    if not address or len(address.strip()) < 3:
        raise HTTPException(status_code=400, detail="Адрес не указан")
    
    details = await get_address_details(address)
    if not details:
        raise HTTPException(status_code=404, detail="Адрес не найден")
    
    return details