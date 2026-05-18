import pytest
from app.services.audit_service import log_action, ACTION_LOGIN, ACTION_VIEW_CUSTOMER
from app.services.alert_service import (
    create_alert, has_open_alert, create_score_alert_if_needed,
    ALERT_TYPE_SCORE_ELEVE, STATUS_OPEN, STATUS_CLOSED
)
from app.services.customer_service import compute_kyc_completion, determine_kyc_level
from app.models.customers import Customer
from app.models.audit_logs import AuditLog
from app.models.alerts import Alert


class TestAuditService:
    """Tests du service de journalisation."""

    def test_log_action_creates_entry(self, db, admin_user):
        log_action(db, str(admin_user.id), ACTION_LOGIN)
        db.commit()

        log = db.query(AuditLog).filter(
            AuditLog.user_id == admin_user.id,
            AuditLog.action == ACTION_LOGIN
        ).first()

        assert log is not None
        assert log.action == ACTION_LOGIN

    def test_log_action_with_client_id(self, db, admin_user, reference_data):
        customer = Customer(nom="LOG", prenom="Test")
        db.add(customer)
        db.flush()

        log_action(
            db, str(admin_user.id),
            ACTION_VIEW_CUSTOMER,
            client_id=str(customer.id)
        )
        db.commit()

        log = db.query(AuditLog).filter(
            AuditLog.action == ACTION_VIEW_CUSTOMER
        ).first()

        assert log is not None
        assert log.client_id == customer.id

    def test_log_action_with_resource_type(self, db, admin_user):
        """Signature Magloire — resource_type + resource_id."""
        customer = Customer(nom="RES", prenom="Test")
        db.add(customer)
        db.flush()

        log_action(
            db,
            user_id=str(admin_user.id),
            action="SCORING_CALCULATE",
            resource_type="customer",
            resource_id=str(customer.id),
        )
        db.commit()

        log = db.query(AuditLog).filter(
            AuditLog.action == "SCORING_CALCULATE"
        ).first()

        assert log is not None
        assert log.client_id == customer.id

    def test_log_action_never_raises(self, db):
        """L'audit ne doit jamais faire échouer l'opération principale."""
        # user_id invalide — ne doit pas lever d'exception
        try:
            log_action(db, "uuid-invalide", "TEST_ACTION")
        except Exception:
            pytest.fail("log_action ne doit jamais lever d'exception")


class TestAlertService:
    """Tests du service de gestion des alertes."""

    def test_create_alert(self, db, reference_data):
        customer = Customer(nom="ALERT", prenom="Test")
        db.add(customer)
        db.flush()

        alert = create_alert(db, customer.id, ALERT_TYPE_SCORE_ELEVE)
        db.commit()

        assert alert is not None
        assert alert.type_alerte == ALERT_TYPE_SCORE_ELEVE
        assert alert.statut == STATUS_OPEN
        assert alert.sar_declare is False

    def test_has_open_alert_true(self, db, reference_data):
        customer = Customer(nom="HAS", prenom="Alert")
        db.add(customer)
        db.flush()

        create_alert(db, customer.id, ALERT_TYPE_SCORE_ELEVE)
        db.commit()

        assert has_open_alert(db, customer.id, ALERT_TYPE_SCORE_ELEVE) is True

    def test_has_open_alert_false(self, db, reference_data):
        customer = Customer(nom="NO", prenom="Alert")
        db.add(customer)
        db.flush()
        db.commit()

        assert has_open_alert(db, customer.id, ALERT_TYPE_SCORE_ELEVE) is False

    def test_has_open_alert_closed(self, db, reference_data):
        """Une alerte fermée ne compte pas comme ouverte."""
        customer = Customer(nom="CLOSED", prenom="Alert")
        db.add(customer)
        db.flush()

        alert = Alert(
            client_id=customer.id,
            type_alerte=ALERT_TYPE_SCORE_ELEVE,
            statut=STATUS_CLOSED,
        )
        db.add(alert)
        db.commit()

        assert has_open_alert(db, customer.id, ALERT_TYPE_SCORE_ELEVE) is False

    def test_create_score_alert_high_score(self, db, reference_data):
        customer = Customer(nom="HIGH", prenom="Score")
        db.add(customer)
        db.flush()

        alert = create_score_alert_if_needed(db, customer.id, global_score=75)
        db.commit()

        assert alert is not None
        assert alert.type_alerte == ALERT_TYPE_SCORE_ELEVE

    def test_create_score_alert_low_score(self, db, reference_data):
        """Pas d'alerte si score < 67."""
        customer = Customer(nom="LOW", prenom="Score")
        db.add(customer)
        db.flush()

        alert = create_score_alert_if_needed(db, customer.id, global_score=45)
        assert alert is None

    def test_create_score_alert_no_duplicate(self, db, reference_data):
        """skip_if_open=True — pas de doublon d'alerte."""
        customer = Customer(nom="DUP", prenom="Score")
        db.add(customer)
        db.flush()

        # Première alerte
        a1 = create_score_alert_if_needed(db, customer.id, global_score=80)
        db.commit()

        # Deuxième appel avec skip_if_open=True
        a2 = create_score_alert_if_needed(
            db, customer.id, global_score=80, skip_if_open=True
        )
        assert a2 is None

    def test_create_score_alert_boundary_67(self, db, reference_data):
        """Score exactement à 67 — doit créer une alerte."""
        customer = Customer(nom="BOUNDARY", prenom="Test")
        db.add(customer)
        db.flush()

        alert = create_score_alert_if_needed(db, customer.id, global_score=67)
        assert alert is not None

    def test_create_score_alert_boundary_66(self, db, reference_data):
        """Score à 66 — ne doit pas créer d'alerte."""
        customer = Customer(nom="BELOW", prenom="Boundary")
        db.add(customer)
        db.flush()

        alert = create_score_alert_if_needed(db, customer.id, global_score=66)
        assert alert is None


class TestCustomerService:
    """Tests du service KYC."""

    def test_kyc_completion_empty_customer(self, db):
   
        customer = Customer()  # Aucun champ rempli
        assert compute_kyc_completion(customer) == 0

    def test_kyc_completion_partial(self, db, reference_data):
        customer = Customer(
            nom="PARTIAL",
            prenom="KYC",
            phone="+22966000000",
            email="test@test.bj",
            profession_code="FONCTIONNAIRE",
            revenus_declares=200000,
        )
        completion = compute_kyc_completion(customer)
        assert 0 < completion < 100

    def test_kyc_completion_full(self, db, reference_data):
        customer = Customer(
            nom="FULL",
            prenom="KYC",
            date_naissance=None,
            phone="+22966000001",
            email="full@test.bj",
            profession_code="FONCTIONNAIRE",
            revenus_declares=200000,
            city="Cotonou",
            region="Littoral",
            zone_geo=reference_data["zone_urbaine"].id,
            pays=reference_data["benin"].id,
        )
        completion = compute_kyc_completion(customer)
        assert completion > 50

    def test_determine_kyc_level_low(self):
        assert determine_kyc_level(0)  == "LOW"
        assert determine_kyc_level(39) == "LOW"

    def test_determine_kyc_level_medium(self):
        assert determine_kyc_level(40) == "MEDIUM"
        assert determine_kyc_level(79) == "MEDIUM"

    def test_determine_kyc_level_high(self):
        assert determine_kyc_level(80)  == "HIGH"
        assert determine_kyc_level(100) == "HIGH"

    def test_kyc_level_boundaries(self):
        """Tests aux frontières des niveaux KYC."""
        assert determine_kyc_level(39) == "LOW"
        assert determine_kyc_level(40) == "MEDIUM"
        assert determine_kyc_level(79) == "MEDIUM"
        assert determine_kyc_level(80) == "HIGH"