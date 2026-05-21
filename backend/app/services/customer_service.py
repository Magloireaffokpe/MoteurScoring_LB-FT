from app.models.customers import Customer


def compute_kyc_completion(customer: Customer) -> int:
    """
    Calcule le pourcentage de complétion du dossier KYC d'un client.
    Utilisé après création et mise à jour d'un client.
    Retourne un entier entre 0 et 100.
    """
    fields = [
        customer.date_naissance,
        customer.phone,
        customer.email,
        customer.profession_code,
        customer.revenus_declares,
        customer.city,
        customer.region,
        customer.zone_geo,
        customer.pays,
    ]

    filled = sum(1 for f in fields if f is not None)
    completion = int((filled / len(fields)) * 100)

    # Bonus si documents valides présents
    if customer.documents:
        valid_docs = [d for d in customer.documents if d.valide]
        if valid_docs:
            completion = min(completion + 10, 100)

    return completion


def determine_kyc_level(completion: int) -> str:
    """
    Détermine le niveau KYC basé sur le % de complétion.
    LOW < 40% / MEDIUM 40-79% / HIGH >= 80%
    """
    if completion >= 80:
        return "HIGH"
    if completion >= 40:
        return "MEDIUM"
    return "LOW"
