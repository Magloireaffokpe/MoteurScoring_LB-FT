"""
Script de backfill : calcule le solde courant de chaque compte
à partir de l'historique des transactions et met à jour solde_moyen.

Règle :
  DEPOT          → solde += montant
  RETRAIT        → solde -= montant
  VIREMENT       → solde -= montant
  PAIEMENT       → solde -= montant

Usage : python3 -m scripts.backfill_solde   (depuis backend/)
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.session import SessionLocal
from sqlalchemy import text

db = SessionLocal()

try:
    # Une seule requête SQL : UPDATE avec sous-requête agrégée
    sql = text("""
        UPDATE customer_accounts AS ca
        SET solde_moyen = COALESCE((
            SELECT SUM(
                CASE WHEN t.type_op = 'DEPOT' THEN t.montant ELSE -t.montant END
            )
            FROM transactions AS t
            WHERE t.compte_id = ca.id
        ), 0)
    """)

    db.execute(sql)
    db.commit()

    total = db.execute(text("SELECT COUNT(*) FROM customer_accounts")).scalar()
    print(f"✅ Backfill terminé : {total} comptes mis à jour.")

except Exception as e:
    db.rollback()
    print(f"❌ Erreur : {e}")
finally:
    db.close()
