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
    score_id: Optional[UUID] = None
    beneficiaire_nom: Optional[str] = None
    tx_ids: Optional[list[UUID]] = None


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
    score_id: Optional[UUID] = None
    beneficiaire_nom: Optional[str] = None
    tx_ids: Optional[list[UUID]] = None

    model_config = {"from_attributes": True}


class BeneficiaireGroupement(BaseModel):
    """Groupe d'alertes partageant le même bénéficiaire suspect."""
    beneficiaire_nom: str
    nb_clients: int
    nb_transactions: int
    montant_total: float
    premiere_alerte: Optional[datetime] = None
    derniere_alerte: Optional[datetime] = None