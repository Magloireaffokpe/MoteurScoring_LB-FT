from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from uuid import UUID


class TransactionResponse(BaseModel):
    id: UUID
    compte_id: UUID
    montant: float
    devise: Optional[str]
    type_op: Optional[str]
    date_op: Optional[datetime]
    canal: Optional[str]
    origine: Optional[str]
    destination: Optional[str]
    origine_pays_id: Optional[int]
    destination_pays_id: Optional[int]

    model_config = {"from_attributes": True}


class TransactionCreateResponse(TransactionResponse):
    new_score_global: Optional[int] = None
    new_score_category: Optional[str] = None


class TransactionCreate(BaseModel):
    compte_id: UUID
    montant: float
    devise: str = "XOF"
    type_op: str
    canal: str = "GUICHET"
    origine: Optional[str] = None
    destination: Optional[str] = None
    origine_pays_id: Optional[int] = None
    destination_pays_id: Optional[int] = None
