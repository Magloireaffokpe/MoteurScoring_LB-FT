from app.db.session import SessionLocal
from app.models.scores import Score
from app.models.alerts import Alert
from app.models.transactions import Transaction
from app.models.customer_docs import CustomerDoc
from app.models.customer_accounts import CustomerAccount
from app.models.customers import Customer
from app.models.pep_list import PepEntry
from app.models.audit_logs import AuditLog

db = SessionLocal()

try:
    # Ordre inverse des dépendances FK
    db.query(Score).delete()
    db.query(Alert).delete()
    db.query(AuditLog).delete()
    db.query(Transaction).delete()
    db.query(CustomerDoc).delete()
    db.query(CustomerAccount).delete()
    db.query(Customer).delete()
    db.query(PepEntry).delete()
    db.commit()
    print("✅ Données supprimées avec succès.")
except Exception as e:
    db.rollback()
    print(f"❌ Erreur : {e}")
finally:
    db.close()
