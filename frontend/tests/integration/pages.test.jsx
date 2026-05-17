// tests/integration/pages.test.jsx
// Tests d'intégration des pages principales
// Mock des services API pour éviter les appels réseau réels

import {
  render,
  screen,
  within,
  fireEvent,
  waitFor,
} from "@testing-library/react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { Toaster } from "react-hot-toast";

// ── Mocks des services ─────────────────────────────────────────────
vi.mock("../../src/services/authService", () => ({
  authService: {
    login: vi.fn(),
    me: vi.fn(),
  },
}));

vi.mock("../../src/services/dashboardService", () => ({
  dashboardService: {
    stats: vi.fn(),
    recentAlerts: vi.fn(),
    pepClients: vi.fn(),
  },
}));

vi.mock("../../src/services/customerService", () => ({
  customerService: {
    list: vi.fn(),
    get: vi.fn(),
    create: vi.fn(),
    getScores: vi.fn(),
    getAlerts: vi.fn(),
  },
  referentialService: {
    countries: vi.fn(),
    riskZones: vi.fn(),
  },
}));

vi.mock("../../src/services/scoringService", () => ({
  scoringService: {
    score: vi.fn(),
    rescore: vi.fn(),
    getById: vi.fn(),
  },
}));

vi.mock("../../src/services/alertService", () => ({
  alertService: {
    list: vi.fn(),
    update: vi.fn(),
    create: vi.fn(),
  },
}));

vi.mock("../../src/services/exportService", () => ({
  exportService: {
    customerPdf: vi.fn(),
    transactionsCsv: vi.fn(),
    sarPdf: vi.fn(),
  },
}));

vi.mock("../../src/services/adminService", () => ({
  adminService: {
    getCriteria: vi.fn(),
    updateCriteria: vi.fn(),
    getThresholds: vi.fn(),
    updateThreshold: vi.fn(),
    importPep: vi.fn(),
    addPep: vi.fn(),
    getUsers: vi.fn(),
    getAuditLogs: vi.fn(),
  },
}));

// ── Imports après mocks ────────────────────────────────────────────
import { AuthProvider } from "../../src/context/AuthContext";
import { AppProvider } from "../../src/context/AppContext";
import { authService } from "../../src/services/authService";
import { dashboardService } from "../../src/services/dashboardService";
import {
  customerService,
  referentialService,
} from "../../src/services/customerService";
import { scoringService } from "../../src/services/scoringService";
import { alertService } from "../../src/services/alertService";
import { adminService } from "../../src/services/adminService";

import LoginPage from "../../src/pages/LoginPage";
import DashboardPage from "../../src/pages/DashboardPage";
import ClientsListPage from "../../src/pages/ClientsListPage";
import AddClientPage from "../../src/pages/AddClientPage";
import AlertsPage from "../../src/pages/AlertsPage";
import AdminPage from "../../src/pages/AdminPage";

import {
  MOCK_COUNTRIES,
  MOCK_RISK_ZONES,
  MOCK_CRITERIA,
  MOCK_THRESHOLDS,
} from "../../src/utils/constants";

/* ── Helper : wrapper avec contextes ─────────────────────────────── */
function renderWithProviders(
  ui,
  { initialEntries = ["/"], session = null } = {},
) {
  if (session) {
    localStorage.setItem("rg_session", JSON.stringify(session));
  } else {
    localStorage.removeItem("rg_session");
  }

  return render(
    <MemoryRouter initialEntries={initialEntries}>
      <AuthProvider>
        <AppProvider>
          {ui}
          <Toaster />
        </AppProvider>
      </AuthProvider>
    </MemoryRouter>,
  );
}

const ADMIN_SESSION = {
  user: { id: "usr-1", role: "admin", login: "admin" },
  token: "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.mock",
};

const COMPLIANCE_SESSION = {
  user: { id: "usr-2", role: "compliance_officer", login: "agent_01" },
  token: "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.mock2",
};

/* ── Données mock ─────────────────────────────────────────────────── */
const MOCK_STATS = {
  total_clients: 500,
  clients_by_risk_category: { FAIBLE: 200, MOYEN: 200, ÉLEVÉ: 100 },
  open_alerts_count: 12,
  transactions_last_30d: { count: 2450, total_amount: 125_000_000 },
};

const MOCK_CLIENTS = {
  items: [
    {
      id: "c1",
      nom: "BIAOU",
      prenom: "Koffi",
      score: 48,
      risk_category: "MOYEN",
      statut_pep: false,
      date_creation: "2024-01-15T10:00:00Z",
    },
    {
      id: "c2",
      nom: "SOGLO",
      prenom: "Amélie",
      score: 12,
      risk_category: "FAIBLE",
      statut_pep: false,
      date_creation: "2022-06-01T08:00:00Z",
    },
    {
      id: "c3",
      nom: "OUEDRAOGO",
      prenom: "Fatima",
      score: 74,
      risk_category: "ÉLEVÉ",
      statut_pep: true,
      date_creation: "2026-03-10T14:00:00Z",
    },
  ],
  total: 3,
};

const MOCK_ALERTS_DATA = {
  items: [
    {
      id: "a1",
      customer_id: "c3",
      customer_name: "Fatima OUEDRAOGO",
      alert_type: "SCORE_ELEVE",
      risk_level: "HIGH",
      status: "OPEN",
      created_at: "2026-05-01T08:00:00Z",
      sar_filed: false,
    },
    {
      id: "a2",
      customer_id: "c1",
      customer_name: "Koffi BIAOU",
      alert_type: "KYC_INCOMPLET",
      risk_level: "MEDIUM",
      status: "UNDER_REVIEW",
      created_at: "2026-04-28T10:00:00Z",
      sar_filed: false,
    },
  ],
  total: 2,
};

// ════════════════════════════════════════════════════════════════════
// LoginPage
// ════════════════════════════════════════════════════════════════════
describe("LoginPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("affiche le titre RiskGuard", () => {
    renderWithProviders(<LoginPage />);
    const hasTitle = screen.queryAllByAltText("RiskGuard").length > 0 || screen.queryAllByText(/RiskGuard/i).length > 0;
    expect(hasTitle).toBe(true);
  });

  it("affiche les champs login et mot de passe", () => {
    renderWithProviders(<LoginPage />);
    expect(screen.getByPlaceholderText("agent_01")).toBeInTheDocument();
    expect(screen.getByPlaceholderText("••••••••")).toBeInTheDocument();
  });

  it("affiche le bouton Se connecter", () => {
    renderWithProviders(<LoginPage />);
    expect(
      screen.getByRole("button", { name: /Se connecter/i }),
    ).toBeInTheDocument();
  });

  it("affiche une erreur si les champs sont vides", async () => {
    renderWithProviders(<LoginPage />);
    fireEvent.click(screen.getByRole("button", { name: /Se connecter/i }));
    await waitFor(() => {
      expect(screen.getByText("L'identifiant est requis")).toBeInTheDocument();
    });
  });

  it("affiche l'erreur mot de passe si login rempli mais pas le mot de passe", async () => {
    renderWithProviders(<LoginPage />);
    fireEvent.change(screen.getByPlaceholderText("agent_01"), {
      target: { value: "admin" },
    });
    fireEvent.click(screen.getByRole("button", { name: /Se connecter/i }));
    await waitFor(() => {
      expect(
        screen.getByText("Le mot de passe est requis"),
      ).toBeInTheDocument();
    });
  });

  it("affiche une erreur 401 si identifiants incorrects", async () => {
    authService.login.mockRejectedValue({ response: { status: 401 } });

    renderWithProviders(<LoginPage />);
    fireEvent.change(screen.getByPlaceholderText("agent_01"), {
      target: { value: "admin" },
    });
    fireEvent.change(screen.getByPlaceholderText("••••••••"), {
      target: { value: "mauvais_mdp" },
    });
    fireEvent.click(screen.getByRole("button", { name: /Se connecter/i }));

    await waitFor(() => {
      expect(
        screen.getByText("Identifiant ou mot de passe incorrect"),
      ).toBeInTheDocument();
    });
  });

  it("appelle authService.login avec les bons paramètres", async () => {
    authService.login.mockResolvedValue({
      access_token: "tok123",
      user_id: "uid1",
      role: "admin",
    });

    renderWithProviders(<LoginPage />);
    fireEvent.change(screen.getByPlaceholderText("agent_01"), {
      target: { value: "admin" },
    });
    fireEvent.change(screen.getByPlaceholderText("••••••••"), {
      target: { value: "admin1234" },
    });
    fireEvent.click(screen.getByRole("button", { name: /Se connecter/i }));

    await waitFor(() => {
      expect(authService.login).toHaveBeenCalledWith({
        login: "admin",
        password: "admin1234",
      });
    });
  });
});

// ════════════════════════════════════════════════════════════════════
// DashboardPage
// ════════════════════════════════════════════════════════════════════
describe("DashboardPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    dashboardService.stats.mockResolvedValue(MOCK_STATS);
    dashboardService.recentAlerts.mockResolvedValue({
      items: MOCK_ALERTS_DATA.items.slice(0, 2),
    });
  });

  it("affiche les 4 KPI cards", async () => {
    renderWithProviders(<DashboardPage />, { session: ADMIN_SESSION });
    await waitFor(() => {
      expect(screen.getByText("Total clients")).toBeInTheDocument();
      expect(screen.getByText("Risque élevé")).toBeInTheDocument();
      expect(screen.getByText("Alertes ouvertes")).toBeInTheDocument();
    });
  });

  it("affiche la valeur total_clients", async () => {
    renderWithProviders(<DashboardPage />, { session: ADMIN_SESSION });
    await waitFor(() => {
      expect(screen.getByText("500")).toBeInTheDocument();
    });
  });

  it('affiche le titre "Répartition du risque"', async () => {
    renderWithProviders(<DashboardPage />, { session: ADMIN_SESSION });
    await waitFor(() => {
      expect(screen.getByText("Répartition du risque")).toBeInTheDocument();
    });
  });

  it("affiche la section Actions rapides", async () => {
    renderWithProviders(<DashboardPage />, { session: ADMIN_SESSION });
    await waitFor(() => {
      expect(screen.getByText("Actions rapides")).toBeInTheDocument();
    });
  });

  it("affiche le bouton Nouveau client", async () => {
    renderWithProviders(<DashboardPage />, { session: ADMIN_SESSION });
    await waitFor(() => {
      expect(screen.getByText(/Nouveau client/i)).toBeInTheDocument();
    });
  });

  it("affiche la section Rescore rapide", async () => {
    renderWithProviders(<DashboardPage />, { session: ADMIN_SESSION });
    await waitFor(() => {
      expect(screen.getByText("Rescore rapide")).toBeInTheDocument();
    });
  });

  it("affiche les 5 dernières alertes", async () => {
    renderWithProviders(<DashboardPage />, { session: ADMIN_SESSION });
    await waitFor(() => {
      expect(screen.getByText("5 dernières alertes")).toBeInTheDocument();
    });
  });
});

// ════════════════════════════════════════════════════════════════════
// ClientsListPage
// ════════════════════════════════════════════════════════════════════
describe("ClientsListPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    customerService.list.mockResolvedValue(MOCK_CLIENTS);
  });

  it("affiche le champ de recherche", async () => {
    renderWithProviders(<ClientsListPage />, { session: ADMIN_SESSION });
    expect(
      screen.getByPlaceholderText(/Rechercher/i),
    ).toBeInTheDocument();
  });

  it("affiche le bouton Nouveau client", async () => {
    renderWithProviders(<ClientsListPage />, { session: ADMIN_SESSION });
    expect(screen.getByText(/Nouveau/i)).toBeInTheDocument();
  });

  it("affiche les clients après chargement", async () => {
    renderWithProviders(<ClientsListPage />, { session: ADMIN_SESSION });
    await waitFor(() => {
      expect(screen.getByText("BIAOU")).toBeInTheDocument();
      expect(screen.getByText("SOGLO")).toBeInTheDocument();
      expect(screen.getByText("OUEDRAOGO")).toBeInTheDocument();
    });
  });

  it("affiche le badge PEP pour Fatima", async () => {
    renderWithProviders(<ClientsListPage />, { session: ADMIN_SESSION });
    await waitFor(() => {
      const ligneFatima = screen.getByText(/Fatima/i).closest("tr");
      expect(ligneFatima).toBeInTheDocument();
      const pepBadge = within(ligneFatima).getByText("PEP");
      expect(pepBadge).toBeInTheDocument();
    });
  });
});

// ════════════════════════════════════════════════════════════════════
// AddClientPage — Stepper
// ════════════════════════════════════════════════════════════════════
describe("AddClientPage — Stepper", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    referentialService.countries.mockResolvedValue(MOCK_COUNTRIES);
    referentialService.riskZones.mockResolvedValue(MOCK_RISK_ZONES);
  });

  it("affiche les 3 étapes du stepper", async () => {
    renderWithProviders(<AddClientPage />, { session: ADMIN_SESSION });
    await waitFor(() => {
      expect(screen.getByText("Informations personnelles")).toBeInTheDocument();
      expect(screen.getByText("Géographie & KYC")).toBeInTheDocument();
      expect(screen.getByText("Récapitulatif")).toBeInTheDocument();
    });
  });

  it("affiche les champs de l'étape 1", () => {
    renderWithProviders(<AddClientPage />, { session: ADMIN_SESSION });
    expect(screen.getByLabelText(/Prénom/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Nom de famille/i)).toBeInTheDocument();
    expect(screen.getAllByText(/Profession/i).length).toBeGreaterThan(0);
  });

  it("affiche une erreur si on clique Suivant sans remplir les champs", async () => {
    renderWithProviders(<AddClientPage />, { session: ADMIN_SESSION });
    fireEvent.click(screen.getByText(/Suivant/i));
    await waitFor(() => {
      expect(screen.getByText("Le prénom est requis")).toBeInTheDocument();
      expect(screen.getByText("Le nom est requis")).toBeInTheDocument();
    });
  });

  it("passe à l'étape 2 si l'étape 1 est valide", async () => {
    renderWithProviders(<AddClientPage />, { session: ADMIN_SESSION });

    fireEvent.change(screen.getByPlaceholderText("ex : Koffi"), {
      target: { value: "Koffi" },
    });
    fireEvent.change(screen.getByPlaceholderText("ex : BIAOU"), {
      target: { value: "BIAOU" },
    });
    fireEvent.change(
      screen.getByDisplayValue("— Sélectionner une profession —"),
      {
        target: { value: "FONCT_PUBL" },
      },
    );

    fireEvent.click(screen.getByText(/Suivant/i));

    await waitFor(() => {
      expect(screen.getByText("Pays / Nationalité")).toBeInTheDocument();
    });
  });
});

// ════════════════════════════════════════════════════════════════════
// AlertsPage
// ════════════════════════════════════════════════════════════════════
describe("AlertsPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    alertService.list.mockResolvedValue(MOCK_ALERTS_DATA);
  });

  it("affiche le titre de la page", async () => {
    renderWithProviders(<AlertsPage />, { session: ADMIN_SESSION });
    await waitFor(() => {
      expect(screen.getByText("Gestion des alertes")).toBeInTheDocument();
    });
  });

  it("affiche les alertes chargées", async () => {
    renderWithProviders(<AlertsPage />, { session: ADMIN_SESSION });
    await waitFor(() => {
      expect(screen.getByText("Fatima OUEDRAOGO")).toBeInTheDocument();
      expect(screen.getByText("Koffi BIAOU")).toBeInTheDocument();
    });
  });

  it("affiche les filtres de statut et niveau", async () => {
    renderWithProviders(<AlertsPage />, { session: ADMIN_SESSION });
    expect(screen.getByText("Statut")).toBeInTheDocument();
    expect(screen.getByText("Niveau de risque")).toBeInTheDocument();
  });

  it("ouvre le modal de gestion au clic sur Gérer", async () => {
    renderWithProviders(<AlertsPage />, { session: ADMIN_SESSION });
    await waitFor(() => {
      expect(screen.getByText("Fatima OUEDRAOGO")).toBeInTheDocument();
    });
    const gererBtns = screen.getAllByRole("button", { name: /Gérer/i });
    fireEvent.click(gererBtns[0]);
    await waitFor(() => {
      expect(screen.getByText("Nouveau statut")).toBeInTheDocument();
    });
  });
});

// ════════════════════════════════════════════════════════════════════
// AdminPage
// ════════════════════════════════════════════════════════════════════
describe("AdminPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    adminService.getCriteria.mockResolvedValue({ items: MOCK_CRITERIA });
    adminService.getThresholds.mockResolvedValue({ items: MOCK_THRESHOLDS });
    adminService.getAuditLogs.mockResolvedValue({ items: [], total: 0 });
    referentialService.countries.mockResolvedValue(MOCK_COUNTRIES);
    referentialService.riskZones.mockResolvedValue(MOCK_RISK_ZONES);
  });

  it("affiche l'avertissement admin", async () => {
    renderWithProviders(<AdminPage />, { session: ADMIN_SESSION });
    expect(
      screen.getByText(/Zone réservée aux administrateurs/i),
    ).toBeInTheDocument();
  });

  it("affiche les 4 onglets", async () => {
    renderWithProviders(<AdminPage />, { session: ADMIN_SESSION });
    await waitFor(() => {
      expect(screen.getByText("Poids critères")).toBeInTheDocument();
      expect(screen.getByText("Seuils risque")).toBeInTheDocument();
      expect(screen.getByText("Gestion PEP")).toBeInTheDocument();
      expect(screen.getByText("Audit logs")).toBeInTheDocument();
    });
  });

  it("affiche les critères C1-C6 dans l'onglet poids", async () => {
    renderWithProviders(<AdminPage />, { session: ADMIN_SESSION });
    await waitFor(() => {
      expect(screen.getByText("C1")).toBeInTheDocument();
      expect(screen.getByText("C6")).toBeInTheDocument();
    });
  });

  it("bascule vers l'onglet Seuils risque", async () => {
    renderWithProviders(<AdminPage />, { session: ADMIN_SESSION });
    fireEvent.click(screen.getByText("Seuils risque"));
    await waitFor(() => {
      expect(screen.getByText("FAIBLE")).toBeInTheDocument();
      expect(screen.getByText("MOYEN")).toBeInTheDocument();
    });
  });

  it("bascule vers l'onglet Gestion PEP", async () => {
    renderWithProviders(<AdminPage />, { session: ADMIN_SESSION });
    fireEvent.click(screen.getByText("Gestion PEP"));
    await waitFor(() => {
      expect(screen.getByText(/Import CSV/i)).toBeInTheDocument();
      expect(screen.getByText(/Ajout manuel/i)).toBeInTheDocument();
    });
  });

  it("bascule vers l'onglet Audit logs", async () => {
    renderWithProviders(<AdminPage />, { session: ADMIN_SESSION });
    fireEvent.click(screen.getByText("Audit logs"));
    await waitFor(() => {
      expect(screen.getByText(/Toutes les actions/i)).toBeInTheDocument();
    });
  });

  it("affiche le formulaire ajout PEP manuel", async () => {
    renderWithProviders(<AdminPage />, { session: ADMIN_SESSION });
    fireEvent.click(screen.getByText("Gestion PEP"));
    await waitFor(() => {
      expect(screen.getByText("Ajouter à la liste PEP")).toBeInTheDocument();
    });
  });

  it("valide le formulaire PEP manuel si champs requis vides", async () => {
    renderWithProviders(<AdminPage />, { session: ADMIN_SESSION });
    fireEvent.click(screen.getByText("Gestion PEP"));
    await waitFor(() => {
      expect(screen.getByText("Ajouter à la liste PEP")).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText("Ajouter à la liste PEP"));
    await waitFor(() => {
      expect(screen.getByText("Le nom est requis")).toBeInTheDocument();
    });
  });
});
