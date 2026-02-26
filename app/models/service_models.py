from __future__ import annotations

from typing import List, Optional, Dict, Any

from pydantic import BaseModel, Field


class MenuItem(BaseModel):
    id: Optional[str] = None
    name: str
    description: Optional[str] = None
    price: Optional[float] = None
    currency: Optional[str] = None


class MenuCategory(BaseModel):
    name: str
    items: List[MenuItem] = Field(default_factory=list)


class MenuResponse(BaseModel):
    output: Optional[str] = None
    categories: Optional[List[MenuCategory]] = None


class OrderItem(BaseModel):
    id: Optional[str] = None
    name: str
    quantity: int = Field(default=1, ge=1)
    price: Optional[float] = None
    currency: Optional[str] = None


class OrderResponse(BaseModel):
    order_id: str
    status: str
    eta_minutes: Optional[int] = None
    total_amount: Optional[float] = None
    currency: Optional[str] = None
    extra: Dict[str, Any] = Field(default_factory=dict)


class RecommendationItem(BaseModel):
    id: Optional[str] = None
    name: str
    price: Optional[float] = None
    currency: Optional[str] = None
    reason: Optional[str] = None


class RecommendResponse(BaseModel):
    recommendations: List[RecommendationItem] = Field(default_factory=list)


class TrackingResponse(BaseModel):
    order_id: str
    status: str
    eta_minutes: Optional[int] = None


class UserPreferences(BaseModel):
    dietary: List[str] = Field(default_factory=list)
    spice_level: Optional[str] = None
    allergies: List[str] = Field(default_factory=list)


class OrderHistorySummary(BaseModel):
    total_orders: Optional[int] = None
    favorite_items: List[str] = Field(default_factory=list)
    avg_spend: Optional[float] = None


class UserProfileResponse(BaseModel):
    preferences: Optional[UserPreferences] = None
    order_history_summary: Optional[OrderHistorySummary] = None


class SavePreferencesResponse(BaseModel):
    success: bool = True
