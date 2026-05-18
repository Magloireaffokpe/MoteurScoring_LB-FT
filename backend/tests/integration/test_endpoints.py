import pytest
from app.models.customers import Customer
from app.models.alerts import Alert


class TestCustomersEndpoints:
    """Tests d'intégration des endpoints clients."""

    def test_list_clients_authenticated(self, client, admin_headers, reference_data):
        response = client.get("/api/clients", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data

    def test_list_clients_no_auth(self, client):
        response = client.get("/api/clients")
        assert response.status_code == 401

    def test_list_clients_compliance(self, client, compliance_headers, reference_data):
        response = client.get("/api/clients", headers=compliance_headers)
        assert response.status_code == 200

    def test_create_client_admin(self, client, admin_headers, reference_data):
        response = client.post("/api/clients", headers=admin_headers, json={
            "nom": "SOGLO",
            "prenom": "Amélie",
            "phone": "+22965987654",
            "email": "amelie@test.bj",
            "profession_code": "AGRI_MARAICH",
            "profession_name": "Agricultrice maraîchère",
            "profession_risk": "LOW",
            "revenus_declares": 80000.00,
            "city": "Gogounou",
            "region": "Borgou",
            "zone_geo": reference_data["zone_urbaine"].id,
            "pays": reference_data["benin"].id,
        })
        assert response.status_code == 201
        data = response.json()
        assert data["nom"] == "SOGLO"
        assert data["prenom"] == "Amélie"

    def test_create_client_compliance_forbidden(self, client, compliance_headers, reference_data):
        """Seul l'admin peut créer un client."""
        response = client.post("/api/clients", headers=compliance_headers, json={
            "nom": "TEST",
            "prenom": "Forbidden",
        })
        assert response.status_code == 403

    def test_create_client_duplicate_phone(self, client, admin_headers, reference_data):
        client.post("/api/clients", headers=admin_headers, json={
            "nom": "PREMIER",
            "prenom": "Client",
            "phone": "+22900000099",
        })
        response = client.post("/api/clients", headers=admin_headers, json={
            "nom": "SECOND",
            "prenom": "Client",
            "phone": "+22900000099",
        })
        assert response.status_code == 422

    def test_get_client_by_id(self, client, admin_headers, db, reference_data):
        customer = Customer(
            nom="DETAIL",
            prenom="Test",
            pays=reference_data["benin"].id,
        )
        db.add(customer)
        db.commit()

        response = client.get(f"/api/clients/{customer.id}", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["nom"] == "DETAIL"

    def test_get_client_not_found(self, client, admin_headers):
        import uuid
        response = client.get(
            f"/api/clients/{uuid.uuid4()}",
            headers=admin_headers
        )
        assert response.status_code == 404

    def test_update_client(self, client, admin_headers, db, reference_data):
        customer = Customer(nom="UPDATE", prenom="Test")
        db.add(customer)
        db.commit()

        response = client.put(
            f"/api/clients/{customer.id}",
            headers=admin_headers,
            json={"city": "Cotonou", "region": "Littoral"}
        )
        assert response.status_code == 200
        assert response.json()["city"] == "Cotonou"

    def test_list_clients_search(self, client, admin_headers, db, reference_data):
        customer = Customer(nom="SEARCHABLE", prenom="Client")
        db.add(customer)
        db.commit()

        response = client.get(
            "/api/clients?search=SEARCHABLE",
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1

    def test_list_clients_pagination(self, client, admin_headers, db, reference_data):
        for i in range(5):
            db.add(Customer(nom=f"PAG{i}", prenom="Test"))
        db.commit()

        response = client.get(
            "/api/clients?skip=0&limit=2",
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) <= 2


class TestAlertsEndpoints:
    """Tests d'intégration des endpoints alertes."""

    def test_list_alerts_authenticated(self, client, compliance_headers, reference_data):
        response = client.get("/api/alerts", headers=compliance_headers)
        assert response.status_code == 200
        data = response.json()
        assert "items" in data

    def test_create_alert(self, client, admin_headers, db, reference_data):
        customer = Customer(nom="ALERT", prenom="Test")
        db.add(customer)
        db.commit()

        response = client.post("/api/alerts", headers=admin_headers, json={
            "client_id": str(customer.id),
            "type_alerte": "KYC_INCOMPLET",
            "statut": "OPEN",
            "sar_declare": False,
        })
        assert response.status_code == 201
        data = response.json()
        assert data["type_alerte"] == "KYC_INCOMPLET"
        assert data["statut"] == "OPEN"

    def test_update_alert_status(self, client, compliance_headers, db, reference_data):
        customer = Customer(nom="UPD", prenom="Alert")
        db.add(customer)
        db.flush()

        alert = Alert(
            client_id=customer.id,
            type_alerte="SCORE_ELEVE",
            statut="OPEN",
        )
        db.add(alert)
        db.commit()

        response = client.put(
            f"/api/alerts/{alert.id}",
            headers=compliance_headers,
            json={"statut": "UNDER_REVIEW", "decision": "En cours d'analyse"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["statut"] == "UNDER_REVIEW"

    def test_update_alert_sar(self, client, compliance_headers, db, reference_data):
        customer = Customer(nom="SAR", prenom="Test")
        db.add(customer)
        db.flush()

        alert = Alert(client_id=customer.id, type_alerte="SCORE_ELEVE")
        db.add(alert)
        db.commit()

        response = client.put(
            f"/api/alerts/{alert.id}",
            headers=compliance_headers,
            json={"sar_declare": True, "statut": "CLOSED"}
        )
        assert response.status_code == 200
        assert response.json()["sar_declare"] is True

    def test_get_customer_alerts(self, client, compliance_headers, db, reference_data):
        customer = Customer(nom="CUST", prenom="Alerts")
        db.add(customer)
        db.flush()

        for t in ["SCORE_ELEVE", "KYC_INCOMPLET"]:
            db.add(Alert(client_id=customer.id, type_alerte=t))
        db.commit()

        response = client.get(
            f"/api/customers/{customer.id}/alerts",
            headers=compliance_headers
        )
        assert response.status_code == 200
        assert response.json()["total"] == 2


class TestDashboardEndpoints:
    """Tests d'intégration du dashboard."""

    def test_dashboard_stats(self, client, compliance_headers, reference_data):
        response = client.get("/api/dashboard/stats", headers=compliance_headers)
        assert response.status_code == 200
        data = response.json()
        assert "total_clients" in data
        assert "open_alerts_count" in data
        assert "transactions_last_30d" in data

    def test_dashboard_alerts(self, client, compliance_headers, reference_data):
        response = client.get("/api/dashboard/alerts", headers=compliance_headers)
        assert response.status_code == 200
        assert "items" in response.json()

    def test_dashboard_pep(self, client, compliance_headers, db, reference_data):
        customer = Customer(nom="PEP", prenom="Dashboard", statut_pep=True)
        db.add(customer)
        db.commit()

        response = client.get("/api/dashboard/pep", headers=compliance_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1


class TestAdminEndpoints:
    """Tests d'intégration des endpoints admin."""

    def test_get_scoring_criteria_admin(self, client, admin_headers, reference_data):
        response = client.get("/api/admin/scoring-criteria", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 6

    def test_get_scoring_criteria_compliance_forbidden(self, client, compliance_headers, reference_data):
        response = client.get("/api/admin/scoring-criteria", headers=compliance_headers)
        assert response.status_code == 403

    def test_get_risk_thresholds(self, client, admin_headers, reference_data):
        response = client.get("/api/admin/risk-thresholds", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 3

    def test_get_audit_logs(self, client, admin_headers, reference_data):
        response = client.get("/api/admin/audit-logs", headers=admin_headers)
        assert response.status_code == 200
        assert "items" in response.json()

    def test_list_users_admin(self, client, admin_headers, reference_data):
        response = client.get("/api/admin/users", headers=admin_headers)
        assert response.status_code == 200
        assert "items" in response.json()