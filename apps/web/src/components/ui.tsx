/** Small presentational building blocks shared by the pages. */
import type { ReactNode } from 'react';

import { Link } from '@/i18n/navigation';

const BUTTON_BASE =
  'inline-flex min-h-11 items-center justify-center gap-2 rounded-md px-4 text-sm font-semibold transition disabled:cursor-not-allowed disabled:opacity-60';

const VARIANTS = {
  primary: 'bg-brand-700 text-neutral-0 hover:bg-brand-600',
  secondary: 'border border-neutral-300 text-brand-700 hover:bg-neutral-100',
  danger: 'border border-danger text-danger hover:bg-danger/5',
} as const;

type Variant = keyof typeof VARIANTS;

export function buttonClass(variant: Variant = 'primary'): string {
  return `${BUTTON_BASE} ${VARIANTS[variant]}`;
}

export function Button({
  children,
  variant = 'primary',
  className = '',
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant }) {
  return (
    <button className={`${buttonClass(variant)} ${className}`} {...props}>
      {children}
    </button>
  );
}

export function ButtonLink({
  href,
  children,
  variant = 'primary',
}: {
  href: string;
  children: ReactNode;
  variant?: Variant;
}) {
  return (
    <Link href={href} className={buttonClass(variant)}>
      {children}
    </Link>
  );
}

export function Card({ children, className = '' }: { children: ReactNode; className?: string }) {
  return (
    <div className={`rounded-lg border border-neutral-200 bg-neutral-0 p-5 shadow-sm ${className}`}>
      {children}
    </div>
  );
}

export function Field({
  label,
  hint,
  children,
}: {
  label: string;
  hint?: string;
  children: ReactNode;
}) {
  return (
    <label className="flex flex-col gap-1 text-sm">
      <span className="font-semibold text-neutral-700">{label}</span>
      {children}
      {hint ? <span className="text-xs text-neutral-700">{hint}</span> : null}
    </label>
  );
}

export const inputClass =
  'min-h-11 w-full rounded-md border border-neutral-300 bg-neutral-0 px-3 text-base text-neutral-900 focus:border-brand-500 focus:outline-2 focus:outline-brand-500';

export function ErrorNote({ children }: { children: ReactNode }) {
  return (
    <p role="alert" className="rounded-md bg-danger/10 px-3 py-2 text-sm text-danger">
      {children}
    </p>
  );
}

const STATUS_STYLES: Record<string, string> = {
  active: 'bg-success/10 text-success',
  sold: 'bg-neutral-200 text-neutral-700',
  pending_review: 'bg-warning/10 text-warning',
  rejected: 'bg-danger/10 text-danger',
  hidden: 'bg-neutral-200 text-neutral-700',
  draft: 'bg-neutral-200 text-neutral-700',
  expired: 'bg-neutral-200 text-neutral-700',
};

export function StatusBadge({ status, label }: { status: string; label: string }) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-3 py-1 text-xs font-semibold ${
        STATUS_STYLES[status] ?? STATUS_STYLES.draft
      }`}
    >
      {label}
    </span>
  );
}
