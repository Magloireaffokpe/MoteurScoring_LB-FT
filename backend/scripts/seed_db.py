# scripts/seed_db.py
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.session import SessionLocal
from app.models.countries import Country
from app.models.risk_zones import RiskZone
from app.models.scoring_criteria import ScoringCriteria
from app.models.risk_thresholds import RiskThreshold
from app.models.user_roles import UserRole
from app.models.users import User
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def seed_countries(db):
    if db.query(Country).count() > 0:
        print("  [SKIP] countries déjà peuplée")
        return

    countries = [
        # Pays UEMOA
        Country(code_iso="BJ", name="Bénin",        is_uemoa=True,  is_border=False, is_fatf=False),
        Country(code_iso="SN", name="Sénégal",      is_uemoa=True,  is_border=False, is_fatf=False),
        Country(code_iso="ML", name="Mali",          is_uemoa=True,  is_border=False, is_fatf=True),
        Country(code_iso="BF", name="Burkina Faso", is_uemoa=True,  is_border=True,  is_fatf=True),
        Country(code_iso="CI", name="Côte d'Ivoire",is_uemoa=True,  is_border=False, is_fatf=False),
        Country(code_iso="TG", name="Togo",         is_uemoa=True,  is_border=True,  is_fatf=False),
        Country(code_iso="NE", name="Niger",        is_uemoa=True,  is_border=True,  is_fatf=False),
        Country(code_iso="GW", name="Guinée-Bissau",is_uemoa=True,  is_border=False, is_fatf=False),
        # Pays frontaliers hors UEMOA
        Country(code_iso="NG", name="Nigeria",      is_uemoa=False, is_border=True,  is_fatf=False),
        # Pays à risque FATF
        Country(code_iso="LY", name="Libye",        is_uemoa=False, is_border=False, is_fatf=True),
        Country(code_iso="IR", name="Iran",         is_uemoa=False, is_border=False, is_fatf=True),
        Country(code_iso="KP", name="Corée du Nord",is_uemoa=False, is_border=False, is_fatf=True),
        # Autres courants dans les transactions IMF
        Country(code_iso="GH", name="Ghana",        is_uemoa=False, is_border=False, is_fatf=False),
        Country(code_iso="FR", name="France",       is_uemoa=False, is_border=False, is_fatf=False),
        Country(code_iso="CN", name="Chine",        is_uemoa=False, is_border=False, is_fatf=False),
    ]
    db.add_all(countries)
    db.commit()
    print(f"  [OK] {len(countries)} pays insérés")


def seed_risk_zones(db):
    if db.query(RiskZone).count() > 0:
        print("  [SKIP] risk_zones déjà peuplée")
        return

    zones = [
        RiskZone(name="CAPITALE",      risk_level="FAIBLE",     source="BCEAO",
                 description="Zone urbaine centrale, infrastructure bancaire développée"),
        RiskZone(name="URBAINE",       risk_level="FAIBLE",     source="BCEAO",
                 description="Zone urbaine stable, accès aux services financiers"),
        RiskZone(name="SEMI_URBAINE",  risk_level="MOYEN",      source="GIABA",
                 description="Zone périphérique, traçabilité partielle des flux"),
        RiskZone(name="RURALE",        risk_level="MOYEN",      source="GIABA",
                 description="Zone rurale, faible bancarisation"),
        RiskZone(name="FRONTIERE",     risk_level="ELEVE",      source="FATF",
                 description="Zone frontalière à risque (Nigeria, Togo, Burkina)"),
        RiskZone(name="CONFLIT",       risk_level="TRES_ELEVE", source="FATF",
                 description="Zone de conflit actif ou sans infrastructure bancaire"),
    ]
    db.add_all(zones)
    db.commit()
    print(f"  [OK] {len(zones)} zones de risque insérées")


def seed_scoring_criteria(db):
    if db.query(ScoringCriteria).count() > 0:
        print("  [SKIP] scoring_criteria déjà peuplée")
        return

    criteria = [
        ScoringCriteria(code="C1", weight=20.00, name="Profil professionnel",
                        description="Évaluation du risque lié à la profession et au secteur d'activité du client"),
        ScoringCriteria(code="C2", weight=20.00, name="Zone géographique",
                        description="Risque lié à la localisation du client (frontières, zones FATF)"),
        ScoringCriteria(code="C3", weight=25.00, name="Historique transactionnel",
                        description="Analyse des patterns de transactions (pics, fréquence, smurfing)"),
        ScoringCriteria(code="C4", weight=10.00, name="Ancienneté et fidélité",
                        description="Durée de la relation client avec l'IMF"),
        ScoringCriteria(code="C5", weight=15.00, name="Statut PEP",
                        description="Personne Politiquement Exposée — vigilance renforcée GIABA"),
        ScoringCriteria(code="C6", weight=10.00, name="Cohérence KYC",
                        description="Complétude et cohérence du dossier Know Your Customer"),
    ]
    db.add_all(criteria)
    db.commit()

    # Vérification somme des poids = 100%
    total = sum(c.weight for c in criteria)
    print(f"  [OK] {len(criteria)} critères insérés — somme des poids : {total}%")


def seed_risk_thresholds(db):
    if db.query(RiskThreshold).count() > 0:
        print("  [SKIP] risk_thresholds déjà peuplée")
        return

    thresholds = [
        RiskThreshold(
            category="FAIBLE",
            score_min=0,
            score_max=33,
            action="Vigilance standard. Révision annuelle du score. "
                   "Conservation du dossier KYC à jour."
        ),
        RiskThreshold(
            category="MOYEN",
            score_min=34,
            score_max=66,
            action="Vigilance renforcée. Révision semestrielle obligatoire. "
                   "Collecte de justificatifs supplémentaires. Entretien client recommandé."
        ),
        RiskThreshold(
            category="ELEVE",
            score_min=67,
            score_max=100,
            action="Vigilance maximale. Déclaration de Soupçon (SAR) à la CENTIF obligatoire. "
                   "Gel possible des opérations. Escalade hiérarchique immédiate. "
                   "Révision trimestrielle."
        ),
    ]
    db.add_all(thresholds)
    db.commit()
    print(f"  [OK] {len(thresholds)} seuils de risque insérés")


def seed_user_roles(db):
    if db.query(UserRole).count() > 0:
        print("  [SKIP] user_roles déjà peuplée")
        return

    roles = [
        UserRole(
            name="compliance_officer",
            permissions={
                "can_read_clients": True,
                "can_rescore": True,
                "can_export": True,
                "can_manage_alerts": True,
                "can_manage_users": False,
                "can_configure": False,
            }
        ),
        UserRole(
            name="admin",
            permissions={
                "can_read_clients": True,
                "can_create_clients": True,
                "can_rescore": True,
                "can_export": True,
                "can_manage_alerts": True,
                "can_manage_users": True,
                "can_configure": True,
            }
        ),
    ]
    db.add_all(roles)
    db.commit()
    print(f"  [OK] {len(roles)} rôles insérés")


def seed_admin_user(db):
    if db.query(User).filter(User.login == "admin").first():
        print("  [SKIP] utilisateur admin existe déjà")
        return

    admin_role = db.query(UserRole).filter(UserRole.name == "admin").first()
    if not admin_role:
        print("  [ERREUR] rôle admin introuvable — lance seed_user_roles d'abord")
        return

    admin = User(
        login="admin",
        password_hash=pwd_context.hash("admin1234"),
        role_id=admin_role.id,
        is_active=True,
    )
    db.add(admin)
    db.commit()
    print("  [OK] utilisateur admin créé (login: admin / password: admin1234)")
    print("  [!]  Change ce mot de passe en production !")


def main():
    print("\n🌱 Démarrage du seed RiskGuard...\n")
    db = SessionLocal()
    try:
        print("→ Pays...")
        seed_countries(db)

        print("→ Zones de risque...")
        seed_risk_zones(db)

        print("→ Critères de scoring...")
        seed_scoring_criteria(db)

        print("→ Seuils de risque...")
        seed_risk_thresholds(db)

        print("→ Rôles utilisateurs...")
        seed_user_roles(db)

        print("→ Utilisateur admin...")
        seed_admin_user(db)

        print("\n✅ Seed terminé avec succès !\n")
    except Exception as e:
        db.rollback()
        print(f"\n❌ Erreur durant le seed : {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()