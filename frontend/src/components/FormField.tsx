import type { ReactNode } from "react";

interface FormFieldProps {
  label: string;
  htmlFor: string;
  hint?: string;
  unit?: string;
  children: ReactNode;
}

export function FormField({ label, htmlFor, hint, unit, children }: FormFieldProps) {
  return (
    <div className="min-w-0">
      <div className="mb-2 flex items-center justify-between gap-2">
        <label className="text-sm font-semibold text-slate-100" htmlFor={htmlFor}>{label}</label>
        {unit && <span className="text-xs text-slate-400">{unit}</span>}
      </div>
      {children}
      {hint && <p className="mt-1.5 text-xs leading-5 text-slate-400">{hint}</p>}
    </div>
  );
}
