// tests/unit/components.test.jsx
import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { MemoryRouter } from "react-router-dom";

// ── Composants à tester ───────────────────────────────────────────────
import { Badge } from "../../src/components/Badge";
import { Button } from "../../src/components/Button";
import { Card } from "../../src/components/Card";
import { Loader } from "../../src/components/Loader";
import { Modal, ModalFooter } from "../../src/components/Modal";
import { Table, Pagination } from "../../src/components/Table";
import { FormInput, FormSelect } from "../../src/components/FormInput";
import { ScorePanel } from "../../src/components/ScorePanel";

// Mock Recharts to avoid layout warnings in jsdom
vi.mock("recharts", async () => {
  const original = await vi.importActual("recharts");
  return {
    ...original,
    ResponsiveContainer: ({ children }) => (
      <div style={{ width: 800, height: 600 }}>{children}</div>
    ),
  };
});

// ────────────────────────────────────────────────────────────────────
// Badge
// ────────────────────────────────────────────────────────────────────
describe("Badge", () => {
  it("affiche le texte enfant", () => {
    render(<Badge type="FAIBLE">Faible</Badge>);
    expect(screen.getByText("Faible")).toBeInTheDocument();
  });

  it("affiche badge FAIBLE avec classe verte", () => {
    const { container } = render(<Badge type="FAIBLE">Faible</Badge>);
    expect(container.firstChild.className).toContain("#ECFDF5");
  });

  it("affiche badge ÉLEVÉ", () => {
    render(<Badge type="ÉLEVÉ">Élevé</Badge>);
    expect(screen.getByText("Élevé")).toBeInTheDocument();
  });

  it("affiche badge MOYEN", () => {
    render(<Badge type="MOYEN">Moyen</Badge>);
    expect(screen.getByText("Moyen")).toBeInTheDocument();
  });

  it("affiche badge PEP", () => {
    render(<Badge type="PEP">PEP</Badge>);
    expect(screen.getByText("PEP")).toBeInTheDocument();
  });

  it("affiche badge OPEN", () => {
    render(<Badge type="OPEN">Ouvert</Badge>);
    expect(screen.getByText("Ouvert")).toBeInTheDocument();
  });
});

// ────────────────────────────────────────────────────────────────────
// Button
// ────────────────────────────────────────────────────────────────────
describe("Button", () => {
  it("affiche le texte", () => {
    render(<Button>Cliquer ici</Button>);
    expect(
      screen.getByRole("button", { name: /Cliquer ici/i }),
    ).toBeInTheDocument();
  });

  it("est désactivé en état loading", () => {
    render(<Button loading>Chargement</Button>);
    expect(screen.getByRole("button")).toBeDisabled();
  });

  it("appelle onClick quand cliqué", () => {
    const fn = vi.fn();
    render(<Button onClick={fn}>Clic</Button>);
    fireEvent.click(screen.getByRole("button"));
    expect(fn).toHaveBeenCalledTimes(1);
  });

  it("ne déclenche pas onClick si disabled", () => {
    const fn = vi.fn();
    render(
      <Button disabled onClick={fn}>
        Désactivé
      </Button>,
    );
    fireEvent.click(screen.getByRole("button"));
    expect(fn).not.toHaveBeenCalled();
  });

  it("affiche variante ghost sans background coloré", () => {
    const { container } = render(<Button variant="ghost">Ghost</Button>);
    expect(container.firstChild.className).toContain("bg-transparent");
  });

  it("affiche variante secondary", () => {
    const { container } = render(<Button variant="secondary">Sec</Button>);
    expect(container.firstChild.className).toContain("#10B981");
  });

  it("taille sm applique des classes plus petites", () => {
    const { container } = render(<Button size="sm">Petit</Button>);
    expect(container.firstChild.className).toContain("px-3");
  });

  it("fullWidth occupe toute la largeur", () => {
    const { container } = render(<Button fullWidth>Full</Button>);
    expect(container.firstChild.className).toContain("w-full");
  });
});

// ────────────────────────────────────────────────────────────────────
// Card
// ────────────────────────────────────────────────────────────────────
describe("Card", () => {
  it("affiche le titre", () => {
    render(<Card title="Mon titre">Contenu</Card>);
    expect(screen.getByText("Mon titre")).toBeInTheDocument();
  });

  it("affiche le contenu enfant", () => {
    render(<Card>Contenu de la card</Card>);
    expect(screen.getByText("Contenu de la card")).toBeInTheDocument();
  });

  it("affiche l'action quand fournie", () => {
    render(
      <Card title="Test" action={<button>Action</button>}>
        Contenu
      </Card>,
    );
    expect(screen.getByText("Action")).toBeInTheDocument();
  });
});

// ────────────────────────────────────────────────────────────────────
// Loader
// ────────────────────────────────────────────────────────────────────
describe("Loader", () => {
  it("affiche le texte de chargement", () => {
    render(<Loader text="Chargement en cours…" />);
    expect(screen.getByText("Chargement en cours…")).toBeInTheDocument();
  });

  it("affiche le texte par défaut", () => {
    render(<Loader />);
    expect(screen.getByText("Chargement…")).toBeInTheDocument();
  });
});

// ────────────────────────────────────────────────────────────────────
// FormInput
// ────────────────────────────────────────────────────────────────────
describe("FormInput", () => {
  it("affiche le label", () => {
    render(<FormInput label="Nom du client" />);
    expect(screen.getByText("Nom du client")).toBeInTheDocument();
  });

  it("affiche l'astérisque rouge si required", () => {
    render(<FormInput label="Champ" required />);
    expect(screen.getByText("*")).toBeInTheDocument();
  });

  it("affiche le message d'erreur", () => {
    render(<FormInput label="Champ" error="Ce champ est requis" />);
    expect(screen.getByText("Ce champ est requis")).toBeInTheDocument();
  });

  it("affiche le texte d'aide quand pas d'erreur", () => {
    render(<FormInput label="Champ" helper="Format : +229XXXXXXXX" />);
    expect(screen.getByText("Format : +229XXXXXXXX")).toBeInTheDocument();
  });

  it("appelle onChange quand la valeur change", () => {
    const fn = vi.fn();
    render(<FormInput label="Test" onChange={fn} />);
    fireEvent.change(screen.getByRole("textbox"), {
      target: { value: "test" },
    });
    expect(fn).toHaveBeenCalled();
  });
});

// ────────────────────────────────────────────────────────────────────
// Modal
// ────────────────────────────────────────────────────────────────────
describe("Modal", () => {
  it("ne s'affiche pas quand open=false", () => {
    render(
      <Modal open={false} onClose={() => {}} title="Mon modal">
        <p>Contenu</p>
      </Modal>,
    );
    expect(screen.queryByText("Mon modal")).not.toBeInTheDocument();
  });

  it("s'affiche quand open=true", () => {
    render(
      <Modal open={true} onClose={() => {}} title="Mon modal">
        <p>Contenu modal</p>
      </Modal>,
    );
    expect(screen.getByText("Mon modal")).toBeInTheDocument();
    expect(screen.getByText("Contenu modal")).toBeInTheDocument();
  });

  it("appelle onClose au clic sur le bouton fermer", () => {
    const onClose = vi.fn();
    render(
      <Modal open={true} onClose={onClose} title="Test">
        <p>Body</p>
      </Modal>,
    );
    fireEvent.click(screen.getByRole("button", { name: /Fermer/i }));
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("appelle onClose sur touche Echap", () => {
    const onClose = vi.fn();
    render(
      <Modal open={true} onClose={onClose} title="Test">
        <p>Body</p>
      </Modal>,
    );
    fireEvent.keyDown(window, { key: "Escape" });
    expect(onClose).toHaveBeenCalledTimes(1);
  });
});

// ────────────────────────────────────────────────────────────────────
// Table
// ────────────────────────────────────────────────────────────────────
describe("Table", () => {
  const COLUMNS = [
    { key: "nom", label: "Nom" },
    { key: "score", label: "Score", render: (v) => `${v}/100` },
    { key: "status", label: "Statut" },
  ];

  const DATA = [
    { id: "1", nom: "BIAOU", score: 48, status: "ACTIVE" },
    { id: "2", nom: "SOGLO", score: 12, status: "ACTIVE" },
    { id: "3", nom: "OUEDRAOGO", score: 74, status: "SUSPENDED" },
  ];

  it("affiche les en-têtes de colonnes", () => {
    render(<Table columns={COLUMNS} data={DATA} />);
    expect(screen.getByText("Nom")).toBeInTheDocument();
    expect(screen.getByText("Score")).toBeInTheDocument();
    expect(screen.getByText("Statut")).toBeInTheDocument();
  });

  it("affiche toutes les lignes de données", () => {
    render(<Table columns={COLUMNS} data={DATA} />);
    expect(screen.getByText("BIAOU")).toBeInTheDocument();
    expect(screen.getByText("SOGLO")).toBeInTheDocument();
    expect(screen.getByText("OUEDRAOGO")).toBeInTheDocument();
  });

  it("applique la fonction render sur les cellules", () => {
    render(<Table columns={COLUMNS} data={DATA} />);
    expect(screen.getByText("48/100")).toBeInTheDocument();
    expect(screen.getByText("74/100")).toBeInTheDocument();
  });

  it('affiche le texte "Aucune donnée" si data est vide', () => {
    render(<Table columns={COLUMNS} data={[]} />);
    expect(screen.getByText("Aucune donnée")).toBeInTheDocument();
  });

  it("affiche le texte vide personnalisé", () => {
    render(
      <Table columns={COLUMNS} data={[]} emptyText="Aucun client trouvé" />,
    );
    expect(screen.getByText("Aucun client trouvé")).toBeInTheDocument();
  });

  it("appelle onRowClick au clic sur une ligne", () => {
    const fn = vi.fn();
    render(<Table columns={COLUMNS} data={DATA} onRowClick={fn} />);
    fireEvent.click(screen.getByText("BIAOU"));
    expect(fn).toHaveBeenCalledWith(DATA[0]);
  });

  it("affiche le Loader si loading=true", () => {
    render(<Table columns={COLUMNS} data={[]} loading />);
    expect(screen.getByText("Chargement des données…")).toBeInTheDocument();
  });
});

// ────────────────────────────────────────────────────────────────────
// Pagination
// ────────────────────────────────────────────────────────────────────
describe("Pagination", () => {
  it("ne s'affiche pas si une seule page", () => {
    const { container } = render(
      <Pagination total={20} page={1} pageSize={25} onChange={vi.fn()} />,
    );
    expect(container.firstChild).toBeNull();
  });

  it("s'affiche si plusieurs pages", () => {
    render(
      <Pagination total={100} page={1} pageSize={25} onChange={vi.fn()} />,
    );
    expect(screen.getByText("1")).toBeInTheDocument();
  });

  it("affiche les infos de pagination (de–à sur total)", () => {
    render(
      <Pagination total={100} page={1} pageSize={25} onChange={vi.fn()} />,
    );
    expect(screen.getByText(/1–25/)).toBeInTheDocument();
  });

  it("appelle onChange au clic sur la page suivante", () => {
    const fn = vi.fn();
    render(<Pagination total={100} page={1} pageSize={25} onChange={fn} />);
    const nextBtn = screen.getByRole("button", { name: /Page suivante/i });
    fireEvent.click(nextBtn);
    expect(fn).toHaveBeenCalledWith(2);
  });

  it("désactive le bouton précédent sur la première page", () => {
    render(
      <Pagination total={100} page={1} pageSize={25} onChange={vi.fn()} />,
    );
    const prevBtn = screen.getByRole("button", { name: /Page précédente/i });
    expect(prevBtn).toBeDisabled();
  });

  it("désactive le bouton suivant sur la dernière page", () => {
    render(
      <Pagination total={100} page={4} pageSize={25} onChange={vi.fn()} />,
    );
    const nextBtn = screen.getByRole("button", { name: /Page suivante/i });
    expect(nextBtn).toBeDisabled();
  });

  it("appelle onChange avec la page cliquée", () => {
    const fn = vi.fn();
    render(<Pagination total={200} page={3} pageSize={25} onChange={fn} />);
    fireEvent.click(screen.getByRole("button", { name: "2" }));
    expect(fn).toHaveBeenCalledWith(2);
  });
});

// ────────────────────────────────────────────────────────────────────
// ScorePanel
// ────────────────────────────────────────────────────────────────────
describe("ScorePanel", () => {
  const DETAIL = { C1: 9.0, C2: 13.0, C3: 21.25, C4: 7.5, C5: 15.0, C6: 8.5 };

  it("affiche le score global", () => {
    render(<ScorePanel score={74} riskCategory="ÉLEVÉ" detailJson={DETAIL} />);
    expect(screen.getByText("74")).toBeInTheDocument();
  });

  it('affiche "/100"', () => {
    render(<ScorePanel score={74} riskCategory="ÉLEVÉ" detailJson={DETAIL} />);
    expect(screen.getByText("/100")).toBeInTheDocument();
  });

  it("affiche la catégorie de risque", () => {
    render(<ScorePanel score={74} riskCategory="ÉLEVÉ" detailJson={DETAIL} />);
    expect(screen.getByText("ÉLEVÉ")).toBeInTheDocument();
  });

  it('affiche le titre "Contributions par critère (C1–C6)"', () => {
    render(<ScorePanel score={74} riskCategory="ÉLEVÉ" detailJson={DETAIL} />);
    expect(
      screen.getByText("Contributions par critère (C1–C6)"),
    ).toBeInTheDocument();
  });

  it("affiche les 6 labels de critères", () => {
    render(<ScorePanel score={74} riskCategory="ÉLEVÉ" detailJson={DETAIL} />);
    ["C1", "C2", "C3", "C4", "C5", "C6"].forEach((c) => {
      expect(screen.getAllByText(c).length).toBeGreaterThan(0);
    });
  });

  it("affiche la somme totale des contributions", () => {
    render(<ScorePanel score={74} riskCategory="ÉLEVÉ" detailJson={DETAIL} />);
    const sum = Object.values(DETAIL)
      .reduce((a, b) => a + b, 0)
      .toFixed(2);
    expect(screen.getByText(sum)).toBeInTheDocument();
  });

  it("gère un score nul (0)", () => {
    render(
      <ScorePanel
        score={0}
        riskCategory="FAIBLE"
        detailJson={{ C1: 0, C2: 0, C3: 0, C4: 0, C5: 0, C6: 0 }}
      />,
    );
    expect(screen.getByText("0")).toBeInTheDocument();
    expect(screen.getByText("FAIBLE")).toBeInTheDocument();
  });

  it("affiche l'agent si fourni", () => {
    render(
      <ScorePanel
        score={30}
        riskCategory="FAIBLE"
        detailJson={DETAIL}
        scoredBy="admin"
      />,
    );
    expect(screen.getByText("admin")).toBeInTheDocument();
  });
});
