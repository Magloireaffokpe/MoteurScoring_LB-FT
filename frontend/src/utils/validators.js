// src/utils/validators.js
// Validation synchronisée avec les contraintes SQLAlchemy du backend (Marcos)

/**
 * Valide le formulaire de l'étape 1 (informations personnelles)
 * Champs : nom, prenom, phone, email, profession_code, revenus_declares
 */
export function validateStep1(data) {
  const errors = {};

  // Customer.prenom : String(100), nullable=False
  if (!data.prenom?.trim()) errors.prenom = "Le prénom est requis";
  else if (data.prenom.trim().length > 100)
    errors.prenom = "Le prénom ne peut pas dépasser 100 caractères";

  // Customer.nom : String(100), nullable=False
  if (!data.nom?.trim()) errors.nom = "Le nom est requis";
  else if (data.nom.trim().length > 100)
    errors.nom = "Le nom ne peut pas dépasser 100 caractères";

  // Customer.phone : String(20), unique=True
  if (data.phone?.trim()) {
    if (!/^\+?[0-9\s\-]{8,20}$/.test(data.phone.trim()))
      errors.phone = "Numéro de téléphone invalide (ex: +22966123456)";
  }

  // Customer.email : String(150), unique=True
  if (data.email?.trim()) {
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(data.email.trim()))
      errors.email = "Adresse email invalide";
    else if (data.email.trim().length > 150)
      errors.email = "L'email ne peut pas dépasser 150 caractères";
  }

  // Customer.profession_code : String(50)
  if (!data.profession_code)
    errors.profession_code = "La profession est requise";

  // Customer.revenus_declares : Numeric(15,2), nullable=True
  if (data.revenus_declares !== "" && data.revenus_declares != null) {
    const val = Number(data.revenus_declares);
    if (isNaN(val) || val < 0)
      errors.revenus_declares = "Les revenus doivent être un nombre positif";
    else if (val > 9_999_999_999_999.99)
      errors.revenus_declares = "Montant trop élevé";
  }

  return errors;
}

/**
 * Valide le formulaire de l'étape 2 (géographie & KYC)
 * Champs : pays, zone_geo, city, region, type_doc, numero, date_expiration
 */
export function validateStep2(data) {
  const errors = {};

  // Customer.pays : ForeignKey("countries.id"), nullable=True
  if (!data.pays) errors.pays = "Le pays est requis";

  // Customer.city : String(100)
  if (data.city?.trim() && data.city.trim().length > 100)
    errors.city = "La ville ne peut pas dépasser 100 caractères";

  // Customer.region : String(100)
  if (data.region?.trim() && data.region.trim().length > 100)
    errors.region = "La région ne peut pas dépasser 100 caractères";

  // CustomerDoc.numero : String(100)
  if (data.numero?.trim() && data.numero.trim().length > 100)
    errors.numero = "Le numéro de document ne peut pas dépasser 100 caractères";

  // CustomerDoc.date_expiration : Date
  if (data.date_expiration) {
    const exp = new Date(data.date_expiration);
    if (isNaN(exp.getTime()))
      errors.date_expiration = "Date d'expiration invalide";
  }

  return errors;
}

/**
 * Valide le formulaire d'ajout manuel PEP
 * Champs : nom, prenom, fonction, pays, source, date_debut, date_fin
 */
export function validatePepForm(data) {
  const errors = {};

  // PepEntry.nom : String(100), nullable=False, index=True
  if (!data.nom?.trim()) errors.nom = "Le nom est requis";
  else if (data.nom.trim().length > 100)
    errors.nom = "Le nom ne peut pas dépasser 100 caractères";

  // PepEntry.prenom : String(100), nullable=False
  if (!data.prenom?.trim()) errors.prenom = "Le prénom est requis";
  else if (data.prenom.trim().length > 100)
    errors.prenom = "Le prénom ne peut pas dépasser 100 caractères";

  // PepEntry.fonction : String(200)
  if (data.fonction?.trim() && data.fonction.trim().length > 200)
    errors.fonction = "La fonction ne peut pas dépasser 200 caractères";

  // PepEntry.source : String(100)
  if (data.source?.trim() && data.source.trim().length > 100)
    errors.source = "La source ne peut pas dépasser 100 caractères";

  // Cohérence dates
  if (data.date_debut && data.date_fin) {
    if (new Date(data.date_debut) > new Date(data.date_fin))
      errors.date_fin =
        "La date de fin doit être postérieure à la date de début";
  }

  return errors;
}

/**
 * Valide les identifiants de connexion
 */
export function validateLoginForm(data) {
  const errors = {};
  if (!data.login?.trim()) errors.login = "L'identifiant est requis";
  if (!data.password?.trim()) errors.password = "Le mot de passe est requis";
  return errors;
}

/**
 * Vérifie si un objet d'erreurs est vide (formulaire valide)
 */
export function isValid(errors) {
  return Object.keys(errors).length === 0;
}
