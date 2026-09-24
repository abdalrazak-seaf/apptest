'use server';

import { revalidatePath } from 'next/cache';

import { authedApi } from '@/lib/api';
import { errorCode } from '@/lib/errors';

import type { ActionResult } from './auth';

const NOT_SIGNED_IN = { ok: false, code: 'not_authenticated' } as const;

export type NewListingInput = {
  make_id: string;
  model_id: string;
  trim_id?: string | null;
  city_id: string;
  year: string;
  mileage_km: string;
  asking_price_sar: string;
  floor_price_sar?: string | null;
  transmission: 'automatic' | 'manual';
  fuel_type: 'petrol' | 'diesel' | 'hybrid' | 'electric';
  regional_spec: 'saudi' | 'gcc' | 'american' | 'other';
  color_ar?: string | null;
  engine?: string | null;
  negotiable: boolean;
  accident_history_declared: boolean;
  service_history_declared: boolean;
  description_ar?: string | null;
};

/** Drops empty optional fields so the API applies its own defaults. */
function clean(input: NewListingInput): Record<string, unknown> {
  return Object.fromEntries(
    Object.entries(input).filter(([, value]) => value !== '' && value !== null),
  );
}

export async function createListing(input: NewListingInput): Promise<ActionResult<{ id: string }>> {
  const api = await authedApi();
  if (!api) return NOT_SIGNED_IN;

  const { data, error } = await api.POST('/listings', {
    // The API accepts Arabic-Indic digits, so numbers travel as the user typed them.
    body: clean(input) as never,
  });
  if (!data) return { ok: false, code: errorCode(error) };
  return { ok: true, data: { id: data.id } };
}

export async function uploadListingPhoto(
  listingId: string,
  formData: FormData,
): Promise<ActionResult> {
  const api = await authedApi();
  if (!api) return NOT_SIGNED_IN;

  const { error } = await api.POST('/listings/{listing_id}/photos', {
    params: { path: { listing_id: listingId } },
    // The endpoint takes multipart form data, so the body is passed through untouched.
    body: formData as never,
    bodySerializer: () => formData,
  });
  if (error) return { ok: false, code: errorCode(error) };
  revalidatePath('/sell');
  return { ok: true };
}

export async function publishListing(listingId: string): Promise<ActionResult> {
  const api = await authedApi();
  if (!api) return NOT_SIGNED_IN;

  const { error } = await api.POST('/listings/{listing_id}/publish', {
    params: { path: { listing_id: listingId } },
  });
  if (error) return { ok: false, code: errorCode(error) };
  revalidatePath('/my-listings');
  return { ok: true };
}

export async function setListingStatus(
  listingId: string,
  status: 'active' | 'hidden',
): Promise<ActionResult> {
  const api = await authedApi();
  if (!api) return NOT_SIGNED_IN;

  const { error } = await api.PUT('/listings/{listing_id}/status', {
    params: { path: { listing_id: listingId } },
    body: { status },
  });
  if (error) return { ok: false, code: errorCode(error) };
  revalidatePath('/my-listings');
  return { ok: true };
}

export async function markListingSold(
  listingId: string,
  finalPrice: string,
): Promise<ActionResult> {
  const api = await authedApi();
  if (!api) return NOT_SIGNED_IN;

  const { error } = await api.POST('/listings/{listing_id}/sold', {
    params: { path: { listing_id: listingId } },
    body: { final_price_sar: finalPrice as never },
  });
  if (error) return { ok: false, code: errorCode(error) };
  revalidatePath('/my-listings');
  return { ok: true };
}
