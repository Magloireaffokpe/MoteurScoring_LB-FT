from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Routers Marcos
from app.routers import (
    auth,
    customers,
    alerts,
    dashboard,
    admin,
    customer_accounts,
    customer_docs,
    transactions,
    pep,
)

# Routers Magloire 
from app.routers import scoring, exports

app = FastAPI(
    title="RiskGuard API",
    description="Module de scoring LBC/FT pour IMF Béninoises — IUT Parakou 2025-2026",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS — autorise le frontend React (dev)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Routers Marcos ───────────────────────────────────────
app.include_router(auth.router,             tags=["Authentification"])
app.include_router(customers.router,        prefix="/api", tags=["Clients"])
app.include_router(alerts.router,           prefix="/api", tags=["Alertes"])
app.include_router(dashboard.router,        prefix="/api", tags=["Dashboard"])
app.include_router(admin.router,            prefix="/api/admin", tags=["Administration"])
app.include_router(customer_accounts.router,prefix="/api", tags=["Comptes"])
app.include_router(customer_docs.router,    prefix="/api", tags=["Documents"])
app.include_router(transactions.router,     prefix="/api", tags=["Transactions"])
app.include_router(pep.router,              prefix="/api", tags=["PEP"])

# ─── Routers Magloire ─────────────────────────────────────
app.include_router(scoring.router,  prefix="/api", tags=["Scoring"])
app.include_router(exports.router,  prefix="/api", tags=["Exports"])


@app.get("/", tags=["Health"])
def health_check():
    return {"status": "ok", "app": "RiskGuard API", "version": "1.0.0"}