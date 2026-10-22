import type { InputHTMLAttributes } from "react";
import { FormField } from "./FormField";

interface NumericInputProps extends InputHTMLAttributes<HTMLInputElement> {
  label: string;
  hint?: string;
  unit?: string;
}

export function NumericInput({ label, hint, unit, ...props }: NumericInputProps) {
  return (
    <FormField label={label} htmlFor={props.id || ""} hint={hint} unit={unit}>
      <input
        {...props}
        className={`field-control ${props.className || ""}`}
        type="number"
        step={props.step ?? "any"}
        required
      />
    </FormField>
  );
}
