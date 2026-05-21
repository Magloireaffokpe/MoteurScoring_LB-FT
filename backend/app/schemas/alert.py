from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from uuid import UUID


#schema de création d'une alerte 

class AlertCreate(BaseModel):
    client_id:UUID
    type_alerte: str
    statut : str = "OPEN" # OPEN, UNDER_REVIEW, CLOSED
    decision : Optional[str] = None
    sar_declare: bool = False


class AlertUpdate(BaseModel):
    statut : Optional[str] = None # OPEN, UNDER_REVIEW, CLOSED
    decision : Optional[str] = None
    sar_declare: Optional[bool] = None



class AlertResponse(BaseModel):
    id:UUID
    client_id:UUID
    type_alerte: str
    statut : str
    decision : Optional[str] 
    sar_declare:bool 
    date_creation: Optional[datetime]
    date_cloture: Optional[datetime]
    clos_par: Optional[UUID]

    model_config = {"from_attributes": True}