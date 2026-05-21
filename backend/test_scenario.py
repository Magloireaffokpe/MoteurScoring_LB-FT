import time
from app.db.session import SessionLocal
from app.services.scoring import ScoringEngine
from app.models.customers import Customer

def main():
    db = SessionLocal()
    try:
        engine = ScoringEngine(db)
        clients = db.query(Customer).limit(500).all()

        t0 = time.time()
        stats = {'FAIBLE': 0, 'MOYEN': 0, 'ÉLEVÉ': 0, 'erreurs': 0}

        for c in clients:
            try:
                r = engine.calculate_score(c.id)
                cat = r['risk_category']
                stats[cat] = stats.get(cat, 0) + 1
            except Exception as e:
                stats['erreurs'] += 1
                print(f'  ✗ {c.id} : {e}')

        elapsed = time.time() - t0
        total = len(clients)

        print(f'Scorés en {elapsed:.2f}s ({total/elapsed:.0f} clients/s)')
        print(f'  FAIBLE : {stats["FAIBLE"]:>4}  ({stats["FAIBLE"]/total*100:.1f}%)')
        print(f'  MOYEN  : {stats["MOYEN"]:>4}  ({stats["MOYEN"]/total*100:.1f}%)')
        print(f'  ÉLEVÉ  : {stats.get("ÉLEVÉ",0):>4}  ({stats.get("ÉLEVÉ",0)/total*100:.1f}%)')
        print(f'  Erreurs: {stats["erreurs"]:>4}')
    finally:
        db.close()

if __name__ == "__main__":
    main()