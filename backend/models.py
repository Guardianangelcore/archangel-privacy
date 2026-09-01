# Copyright © 2026 Guardian Angel Sovereign Foundation (DAO). All Rights Reserved.
# This source code and its logic are the sole property of the Foundation.
# Unauthorized duplication, modification, or distribution is strictly prohibited.
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, timezone

class User(BaseModel):
    user_id: str
    email: str
    name: Optional[str] = None
    picture: Optional[str] = None
    did: str
    language: str = "en"
    angel_mode: bool = False
    fall_guard: bool = False
    inactivity_guard: bool = False
    inactivity_hours: int = 6
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class EmergencyProfile(BaseModel):
    user_id: str
    full_name: Optional[str] = ""
    blood_type: Optional[str] = ""
    allergies: Optional[str] = ""
    medications: Optional[str] = ""
    conditions: Optional[str] = ""
    emergency_contact_name: Optional[str] = ""
    emergency_contact_phone: Optional[str] = ""
    is_donor: bool = False
    donor_organs: Optional[str] = ""
    life_testament: Optional[str] = ""
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class Document(BaseModel):
    doc_id: str
    user_id: str
    title: str
    file_name: str
    content_type: str
    size: int
    storage_path: str
    hash: str
    translation: Optional[str] = None
    plain_language: Optional[str] = None
    extracted_text: Optional[str] = None
    uploaded_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class WaitlistItem(BaseModel):
    item_id: str
    user_id: str
    specialty: str
    clinic: str
    city: str
    current_date: str
    target_before: str
    priority: str = "normal"
    status: str = "hunting"
    last_check: Optional[datetime] = None
    found_slot: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class FallEvent(BaseModel):
    event_id: str
    user_id: str
    verified: bool
    cancelled: bool
    triggered_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

