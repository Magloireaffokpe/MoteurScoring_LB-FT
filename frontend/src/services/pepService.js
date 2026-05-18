// src/services/pepService.js
// Service pour la consultation de la liste PEP (Personnes Exposées Politiquement)
// Synchronisé avec PepEntry (pep_list.py) et api_routes_backend.md
import api from "./api";

export const pepService = {
  /**
   * GET /api/pep?nom=&prenom=&pays=&active=&skip=0&limit=25
   * Retourne { items: [...], total }
   *
   * Champs alignés avec PepEntry (pep_list.py) :
   *   id         : UUID
   *   nom        : string
   *   prenom     : string
   *   fonction   : string  (ex. 'Ministre des Finances')
   *   pays       : int FK → countries.id
   *   source     : string  ('GIABA' | 'CENTIF' | 'ONU')
   *   date_debut : date
   *   date_fin   : date | null  (null = toujours en fonction)
   *   active     : boolean
   */
  list: (params) => api.get("/api/pep", { params }).then((r) => r.data),
};
