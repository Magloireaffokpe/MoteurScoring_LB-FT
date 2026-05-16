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

    class Config:
        from_attributes = True