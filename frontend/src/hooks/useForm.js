// src/hooks/useForm.js
// Hook générique pour gérer un formulaire avec validation
import { useState, useCallback } from "react";

/**
 * @param {object} initialValues - Valeurs initiales du formulaire
 * @param {function} validateFn  - Fonction de validation : (values) => errors{}
 * @returns {{ values, errors, touched, handleChange, handleBlur, setValues,
 *             reset, validate, setFieldError, setFieldValue }}
 */
export function useForm(initialValues, validateFn = () => ({})) {
  const [values, setValues] = useState(initialValues);
  const [errors, setErrors] = useState({});
  const [touched, setTouched] = useState({});

  const handleChange = useCallback(
    (e) => {
      const { name, value, type, checked } = e.target;
      const newVal = type === "checkbox" ? checked : value;
      setValues((v) => ({ ...v, [name]: newVal }));
      // Effacer l'erreur dès que l'utilisateur modifie le champ
      if (errors[name]) setErrors((er) => ({ ...er, [name]: "" }));
    },
    [errors],
  );

  const handleBlur = useCallback((e) => {
    setTouched((t) => ({ ...t, [e.target.name]: true }));
  }, []);

  const setFieldValue = useCallback(
    (name, value) => {
      setValues((v) => ({ ...v, [name]: value }));
      if (errors[name]) setErrors((er) => ({ ...er, [name]: "" }));
    },
    [errors],
  );

  const setFieldError = useCallback((name, message) => {
    setErrors((er) => ({ ...er, [name]: message }));
  }, []);

  const validate = useCallback(() => {
    const newErrors = validateFn(values);
    setErrors(newErrors);
    setTouched(
      Object.fromEntries(Object.keys(newErrors).map((k) => [k, true])),
    );
    return Object.keys(newErrors).length === 0;
  }, [values, validateFn]);

  const reset = useCallback(() => {
    setValues(initialValues);
    setErrors({});
    setTouched({});
  }, [initialValues]);

  // Patch multiple fields at once
  const patch = useCallback((patch) => {
    setValues((v) => ({ ...v, ...patch }));
  }, []);

  return {
    values,
    errors,
    touched,
    handleChange,
    handleBlur,
    setValues,
    setFieldValue,
    setFieldError,
    validate,
    reset,
    patch,
  };
}
