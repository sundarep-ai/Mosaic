/**
 * Valid date display formats.
 * Must stay in sync with backend/models.py VALID_DATE_FORMATS.
 */
export const DATE_FORMATS = [
  { value: "DD/MM/YYYY", label: "DD/MM/YYYY", example: "25/12/2025" },
  { value: "MM/DD/YYYY", label: "MM/DD/YYYY", example: "12/25/2025" },
  { value: "YYYY/MM/DD", label: "YYYY/MM/DD", example: "2025/12/25" },
  { value: "YYYY/DD/MM", label: "YYYY/DD/MM", example: "2025/25/12" },
];

export const VALID_DATE_FORMAT_VALUES = DATE_FORMATS.map((f) => f.value);
