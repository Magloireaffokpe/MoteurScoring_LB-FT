import uuid
from sqlalchemy import Boolean, Column, String, Date, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.base import Base


class PepEntry(Base):
    __tablename__ = "pep_list"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pays = Column(Integer, ForeignKey("countries.id"), nullable=True)

    nom = Column(String(100), nullable=False,index=True)
    prenom = Column(String(100), nullable=False)
    fonction = Column(String(200), nullable=True)
    date_debut = Column(Date, nullable=True)
    date_fin = Column(Date, nullable=True)       # NULL = toujours en fonction
    source = Column(String(100), nullable=True)  # 'GIABA', 'CENTIF', 'ONU'
    active = Column(Boolean, nullable=False, default=True, server_default="true")

    country = relationship("Country", foreign_keys=[pays])

    def __repr__(self):
        return f"<PepEntry {self.prenom} {self.nom} — {self.fonction}>"


from sqlalchemy import event
from datetime import date

@event.listens_for(PepEntry, "before_insert")
@event.listens_for(PepEntry, "before_update")
def compute_active_pep(mapper, connection, target):
    """Calcul automatique du statut active de la PEP."""
    if target.date_fin is not None or target.date_debut is not None:
        today = date.today()
        is_active = True
        if target.date_fin and target.date_fin < today:
            is_active = False
        if target.date_debut and target.date_debut > today:
            is_active = False
        target.active = is_active