import pytest
from uuid import UUID
from datetime import date
from app.models.customers import Customer
from app.models.customer_docs import CustomerDoc
from app.models.customer_accounts import CustomerAccount
from app.models.transactions import Transaction
from app.models.alerts import Alert
from app.models.scores import Score
from app.models.pep_list import PepEntry


class TestCustomerModel:
    """Tests du modèle Customer."""

    def test_create_customer_minimal(self, db, reference_data):
        customer = Customer(
            nom="SOGLO",
            prenom="Amélie",
            pays=reference_data["benin"].id,
            zone_geo=reference_data["zone_urbaine"].id,
        )
        db.add(customer)
        db.commit()
        db.refresh(customer)

        assert customer.id is not None
        assert isinstance(customer.id, UUID)
        assert customer.nom == "SOGLO"
        assert customer.prenom == "Amélie"
        assert customer.status == "ACTIVE"
        assert customer.statut_pep is False
        assert customer.kyc_level == "LOW"
        assert customer.kyc_completion == 0

    def test_create_customer_full(self, db, reference_data):
        customer = Customer(
            nom="BIAOU",
            prenom="Koffi",
            date_naissance=date(1985, 3, 15),
            phone="+22966123456",
            email="koffi@test.bj",
            profession_code="COMMER_TRANSFR",
            profession_name="Commerçant transfrontalier",
            profession_risk="HIGH",
            revenus_declares=500000.00,
            city="Malanville",
            region="Alibori",
            zone_geo=reference_data["zone_frontiere"].id,
            pays=reference_data["benin"].id,
            statut_pep=False,
            kyc_level="MEDIUM",
            kyc_completion=65,
        )
        db.add(customer)
        db.commit()
        db.refresh(customer)

        assert customer.profession_code == "COMMER_TRANSFR"
        assert float(customer.revenus_declares) == 500000.00
        assert customer.kyc_level == "MEDIUM"

    def test_customer_pep(self, db, reference_data):
        customer = Customer(
            nom="OUEDRAOGO",
            prenom="Fatima",
            statut_pep=True,
            pays=reference_data["benin"].id,
        )
        db.add(customer)
        db.commit()
        db.refresh(customer)

        assert customer.statut_pep is True

    def test_customer_repr(self, db, reference_data):
        customer = Customer(nom="TEST", prenom="Client")
        assert "TEST" in repr(customer)
        assert "Client" in repr(customer)

    def test_customer_unique_phone(self, db, reference_data):
        from sqlalchemy.exc import IntegrityError
        c1 = Customer(nom="A", prenom="A", phone="+22900000001")
        c2 = Customer(nom="B", prenom="B", phone="+22900000001")
        db.add(c1)
        db.commit()
        db.add(c2)
        with pytest.raises(IntegrityError):
            db.commit()


class TestCustomerDocModel:
    """Tests du modèle CustomerDoc."""

    def test_create_document(self, db, reference_data):
        customer = Customer(nom="DOC", prenom="Test")
        db.add(customer)
        db.flush()

        doc = CustomerDoc(
            client_id=customer.id,
            type_doc="CNI",
            numero="BJ123456",
            date_expiration=date(2030, 12, 31),
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)

        assert doc.id is not None
        assert doc.type_doc == "CNI"
        assert doc.valide is True

    def test_document_cascade_delete(self, db, reference_data):
        from app.models.customer_docs import CustomerDoc
        customer = Customer(nom="CASCADE", prenom="Test")
        db.add(customer)
        db.flush()

        doc = CustomerDoc(client_id=customer.id, type_doc="PASSEPORT")
        db.add(doc)
        db.commit()

        doc_id = doc.id
        db.delete(customer)
        db.commit()

        deleted = db.query(CustomerDoc).filter(CustomerDoc.id == doc_id).first()
        assert deleted is None


class TestAlertModel:
    """Tests du modèle Alert."""

    def test_create_alert(self, db, reference_data):
        customer = Customer(nom="ALERT", prenom="Test")
        db.add(customer)
        db.flush()

        alert = Alert(
            client_id=customer.id,
            type_alerte="SCORE_ELEVE",
            statut="OPEN",
            sar_declare=False,
        )
        db.add(alert)
        db.commit()
        db.refresh(alert)

        assert alert.id is not None
        assert alert.statut == "OPEN"
        assert alert.sar_declare is False

    def test_alert_default_statut(self, db, reference_data):
        customer = Customer(nom="DEF", prenom="Alert")
        db.add(customer)
        db.flush()

        alert = Alert(client_id=customer.id, type_alerte="KYC_INCOMPLET")
        db.add(alert)
        db.commit()
        db.refresh(alert)

        assert alert.statut == "OPEN"
        assert alert.sar_declare is False


class TestScoreModel:
    """Tests du modèle Score."""

    def test_create_score(self, db, reference_data):
        customer = Customer(nom="SCORE", prenom="Test")
        db.add(customer)
        db.flush()

        score = Score(
            client_id=customer.id,
            score_global=49,
            detail_json={"C1": 9.0, "C2": 15.0, "C3": 16.25, "C4": 5.5, "C5": 0.0, "C6": 4.0},
            categorie="MOYEN",
            is_current=True,
            calcule_par="AUTOMATED",
        )
        db.add(score)
        db.commit()
        db.refresh(score)

        assert score.id is not None
        assert score.score_global == 49
        assert score.categorie == "MOYEN"
        assert score.is_current is True
        assert score.detail_json["C1"] == 9.0

    def test_score_detail_json_complete(self, db, reference_data):
        customer = Customer(nom="JSON", prenom="Test")
        db.add(customer)
        db.flush()

        detail = {"C1": 9.0, "C2": 15.0, "C3": 16.25, "C4": 5.5, "C5": 0.0, "C6": 4.0}
        score = Score(
            client_id=customer.id,
            score_global=sum(detail.values()),
            detail_json=detail,
            categorie="MOYEN",
        )
        db.add(score)
        db.commit()
        db.refresh(score)

        for key in ["C1", "C2", "C3", "C4", "C5", "C6"]:
            assert key in score.detail_json


class TestPepEntryModel:
    """Tests du modèle PepEntry."""

    def test_create_pep_entry(self, db, reference_data):
        pep = PepEntry(
            nom="TALON",
            prenom="Patrice",
            fonction="Président de la République",
            pays=reference_data["benin"].id,
            source="CENTIF",
            active=True,
        )
        db.add(pep)
        db.commit()
        db.refresh(pep)

        assert pep.id is not None
        assert pep.nom == "TALON"
        assert pep.active is True

    def test_pep_inactive(self, db, reference_data):
        pep = PepEntry(
            nom="ANCIEN",
            prenom="Ministre",
            fonction="Ex-Ministre",
            active=False,
        )
        db.add(pep)
        db.commit()
        db.refresh(pep)

        assert pep.active is False