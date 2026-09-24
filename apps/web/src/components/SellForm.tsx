'use client';

import type { components } from '@thiqa/api-client';
import { useTranslations } from 'next-intl';
import { useState, useTransition } from 'react';

import { createListing, publishListing, uploadListingPhoto } from '@/actions/listings';
import { Button, Card, ErrorNote, Field, inputClass } from '@/components/ui';
import { useRouter } from '@/i18n/navigation';

type City = components['schemas']['CityOut'];
type Make = components['schemas']['MakeOut'];
type VehicleModel = components['schemas']['VehicleModelOut'];

const MIN_PHOTOS = 4;
const MAX_PHOTOS = 20;

type Step = { name: 'details' } | { name: 'photos'; listingId: string; uploaded: number };

export function SellForm({
  cities,
  makes,
  models,
  localeName,
}: {
  cities: City[];
  makes: Make[];
  models: VehicleModel[];
  localeName: 'name_ar' | 'name_en';
}) {
  const t = useTranslations('sell');
  const errors = useTranslations('errors');
  const enums = useTranslations('enums');
  const router = useRouter();

  const [step, setStep] = useState<Step>({ name: 'details' });
  const [makeId, setMakeId] = useState('');
  const [errorCode, setErrorCode] = useState<string | null>(null);
  const [pending, startTransition] = useTransition();

  const modelsForMake = models.filter((model) => model.make_id === makeId);

  function saveDraft(form: FormData) {
    setErrorCode(null);
    startTransition(async () => {
      const result = await createListing({
        make_id: String(form.get('make_id')),
        model_id: String(form.get('model_id')),
        city_id: String(form.get('city_id')),
        year: String(form.get('year')),
        mileage_km: String(form.get('mileage_km')),
        asking_price_sar: String(form.get('asking_price_sar')),
        floor_price_sar: String(form.get('floor_price_sar') ?? ''),
        transmission: form.get('transmission') as 'automatic' | 'manual',
        fuel_type: form.get('fuel_type') as 'petrol',
        regional_spec: form.get('regional_spec') as 'saudi',
        color_ar: String(form.get('color_ar') ?? ''),
        engine: String(form.get('engine') ?? ''),
        negotiable: form.get('negotiable') === 'on',
        accident_history_declared: form.get('accident_history_declared') === 'on',
        service_history_declared: form.get('service_history_declared') === 'on',
        description_ar: String(form.get('description_ar') ?? ''),
      });
      if (result.ok) setStep({ name: 'photos', listingId: result.data.id, uploaded: 0 });
      else setErrorCode(result.code);
    });
  }

  function addPhotos(form: FormData) {
    if (step.name !== 'photos') return;
    const files = form.getAll('photos').filter((file): file is File => file instanceof File);
    setErrorCode(null);
    startTransition(async () => {
      let uploaded = step.uploaded;
      for (const file of files) {
        if (uploaded >= MAX_PHOTOS) break;
        const body = new FormData();
        body.append('file', file);
        const result = await uploadListingPhoto(step.listingId, body);
        if (!result.ok) {
          setErrorCode(result.code);
          break;
        }
        uploaded += 1;
      }
      setStep({ ...step, uploaded });
    });
  }

  function submitForReview() {
    if (step.name !== 'photos') return;
    setErrorCode(null);
    startTransition(async () => {
      const result = await publishListing(step.listingId);
      if (result.ok) {
        router.push('/my-listings');
        router.refresh();
      } else {
        setErrorCode(result.code);
      }
    });
  }

  if (step.name === 'photos') {
    return (
      <Card className="flex flex-col gap-4">
        <div>
          <h2 className="text-lg font-semibold">{t('photosSection')}</h2>
          <p className="mt-1 text-sm text-neutral-700">
            {t('photosHint', { min: MIN_PHOTOS, max: MAX_PHOTOS })}
          </p>
        </div>

        <form action={addPhotos} className="flex flex-col gap-3">
          <Field label={t('choosePhotos')}>
            <input
              type="file"
              name="photos"
              accept="image/jpeg,image/png,image/webp"
              multiple
              className={`${inputClass} py-2`}
            />
          </Field>
          <Button type="submit" variant="secondary" disabled={pending}>
            {t('addPhotos')}
          </Button>
        </form>

        <p className="text-sm font-semibold" data-testid="photo-count">
          {t('photoCount', { count: step.uploaded, min: MIN_PHOTOS })}
        </p>

        {errorCode ? <ErrorNote>{errors(errorCode, { min: MIN_PHOTOS })}</ErrorNote> : null}

        <Button
          type="button"
          onClick={submitForReview}
          disabled={pending || step.uploaded < MIN_PHOTOS}
        >
          {t('submit')}
        </Button>
      </Card>
    );
  }

  return (
    <form action={saveDraft} className="flex flex-col gap-5">
      <Card className="flex flex-col gap-4">
        <h2 className="text-lg font-semibold">{t('carSection')}</h2>
        <div className="grid gap-3 sm:grid-cols-2">
          <Field label={t('make')}>
            <select
              name="make_id"
              required
              value={makeId}
              onChange={(event) => setMakeId(event.target.value)}
              className={inputClass}
            >
              <option value="">{t('chooseFirst')}</option>
              {makes.map((make) => (
                <option key={make.id} value={make.id}>
                  {make[localeName]}
                </option>
              ))}
            </select>
          </Field>

          <Field label={t('model')}>
            <select name="model_id" required disabled={!makeId} className={inputClass}>
              {modelsForMake.map((model) => (
                <option key={model.id} value={model.id}>
                  {model[localeName]}
                </option>
              ))}
            </select>
          </Field>

          <Field label={t('year')}>
            <input name="year" inputMode="numeric" required className={inputClass} />
          </Field>
          <Field label={t('mileage')}>
            <input name="mileage_km" inputMode="numeric" required className={inputClass} />
          </Field>

          <Field label={t('transmission')}>
            <select name="transmission" defaultValue="automatic" className={inputClass}>
              <option value="automatic">{enums('transmission.automatic')}</option>
              <option value="manual">{enums('transmission.manual')}</option>
            </select>
          </Field>
          <Field label={t('fuelType')}>
            <select name="fuel_type" defaultValue="petrol" className={inputClass}>
              {(['petrol', 'diesel', 'hybrid', 'electric'] as const).map((fuel) => (
                <option key={fuel} value={fuel}>
                  {enums(`fuelType.${fuel}`)}
                </option>
              ))}
            </select>
          </Field>
          <Field label={t('regionalSpec')}>
            <select name="regional_spec" defaultValue="saudi" className={inputClass}>
              {(['saudi', 'gcc', 'american', 'other'] as const).map((spec) => (
                <option key={spec} value={spec}>
                  {enums(`regionalSpec.${spec}`)}
                </option>
              ))}
            </select>
          </Field>
          <Field label={`${t('color')} (${t('optional')})`}>
            <input name="color_ar" className={inputClass} />
          </Field>
        </div>

        <div className="flex flex-col gap-2 text-sm">
          <label className="flex min-h-11 items-center gap-2">
            <input type="checkbox" name="accident_history_declared" className="size-5" />
            {t('accidentHistory')}
          </label>
          <label className="flex min-h-11 items-center gap-2">
            <input type="checkbox" name="service_history_declared" className="size-5" />
            {t('serviceHistory')}
          </label>
        </div>
      </Card>

      <Card className="flex flex-col gap-4">
        <h2 className="text-lg font-semibold">{t('priceSection')}</h2>
        <div className="grid gap-3 sm:grid-cols-2">
          <Field label={t('askingPrice')}>
            <input name="asking_price_sar" inputMode="numeric" required className={inputClass} />
          </Field>
          <Field label={t('floorPrice')} hint={t('floorPriceHint')}>
            <input name="floor_price_sar" inputMode="numeric" className={inputClass} />
          </Field>
          <Field label={t('city')}>
            <select name="city_id" required className={inputClass}>
              {cities.map((city) => (
                <option key={city.id} value={city.id}>
                  {city[localeName]}
                </option>
              ))}
            </select>
          </Field>
        </div>
        <label className="flex min-h-11 items-center gap-2 text-sm">
          <input type="checkbox" name="negotiable" defaultChecked className="size-5" />
          {t('negotiable')}
        </label>
        <Field label={t('descriptionAr')}>
          <textarea
            name="description_ar"
            rows={4}
            placeholder={t('descriptionPlaceholder')}
            className={`${inputClass} py-2`}
          />
        </Field>
      </Card>

      {errorCode ? <ErrorNote>{errors(errorCode, { min: MIN_PHOTOS })}</ErrorNote> : null}

      <Button type="submit" disabled={pending}>
        {t('create')}
      </Button>
    </form>
  );
}
