// src/services/exportService.js
import api from "./api";
import { downloadBlob } from "../utils/helpers";

export const exportService = {
  /**
   * GET /api/exports/customer/{customer_id}/pdf
   * Télécharge la fiche client PDF
   */
  customerPdf: async (customerId) => {
    const today = new Date().toISOString().slice(0, 10);
    const res = await api.get(`/api/exports/customer/${customerId}/pdf`, {
      responseType: "blob",
    });
    downloadBlob(
      res.data,
      `fiche_client_${customerId}_${today}.pdf`,
      "application/pdf",
    );
  },

  /**
   * GET /api/exports/transactions/{customer_id}/csv?days=90
   * Télécharge le CSV des transactions
   */
  transactionsCsv: async (customerId, days = 90) => {
    const today = new Date().toISOString().slice(0, 10);
    const res = await api.get(`/api/exports/transactions/${customerId}/csv`, {
      params: { days },
      responseType: "blob",
    });
    downloadBlob(
      res.data,
      `transactions_${customerId}_${today}.csv`,
      "text/csv",
    );
  },

  /**
   * GET /api/exports/sar/{alert_id}/pdf
   * Télécharge la Déclaration de Soupçon SAR
   */
  sarPdf: async (alertId) => {
    const today = new Date().toISOString().slice(0, 10);
    const res = await api.get(`/api/exports/sar/${alertId}/pdf`, {
      responseType: "blob",
    });
    downloadBlob(res.data, `SAR_${alertId}_${today}.pdf`, "application/pdf");
  },
};
