import type { SelectHTMLAttributes } from "react";
import { ChevronDown } from "lucide-react";
import { FormField } from "./FormField";

interface SelectOption {
  value: string;
  label: string;
}

interface SelectInputProps extends SelectHTMLAttributes<HTMLSelectElement> {
  label: string;
  hint?: string;
  options: SelectOption[];
  placeholder: string;
}

export function SelectInput({ label, hint, options, placeholder, ...props }: SelectInputProps) {
  return (
    <FormField label={label} htmlFor={props.id || ""} hint={hint}>
      <div className="relative">
        <select {...props} className={`field-control appearance-none pr-10 ${props.className || ""}`} required>
          <option value="">{placeholder}</option>
          {options.map((option) => <option value={option.value} key={option.value}>{option.label}</option>)}
        </select>
        <ChevronDown aria-hidden="true" className="pointer-events-none absolute right-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
      </div>
    </FormField>
  );
}
