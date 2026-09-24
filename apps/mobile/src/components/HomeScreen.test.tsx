import { createApiClient } from '@thiqa/api-client';
import { fireEvent, render, screen, waitFor } from '@testing-library/react-native';
import { LocaleProvider } from '@/i18n/LocaleProvider';
import { HomeScreen } from './HomeScreen';

const healthy = { status: 'ok', service: 'api', version: '0.1.0', environment: 'local' };

function clientReturning(...responses: (() => Response)[]) {
  const fetch = jest.fn(async (_req: Request) => {
    const next = responses.shift();
    if (!next) throw new Error('no more responses');
    return next();
  });
  return { client: createApiClient('http://api.test', { fetch }), fetch };
}

const json = (status: number, body: unknown) => () =>
  new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } });

async function renderHome(client: ReturnType<typeof createApiClient>) {
  return await render(
    <LocaleProvider>
      <HomeScreen client={client} />
    </LocaleProvider>,
  );
}

describe('HomeScreen', () => {
  it('renders Arabic by default with an RTL root and calls /health', async () => {
    const { client, fetch } = clientReturning(json(200, healthy));
    await renderHome(client);
    expect(screen.getByTestId('locale-root')).toHaveStyle({ direction: 'rtl' });
    expect(screen.getByText('سوق السيارات المستعملة الموثوق')).toBeTruthy();
    await waitFor(() =>
      expect(screen.getByTestId('health-status')).toHaveTextContent('الخادم يعمل'),
    );
    expect(fetch.mock.calls[0]![0].url).toBe('http://api.test/health');
  });

  it('shows an error with a retry button that recovers', async () => {
    const { client } = clientReturning(json(503, {}), json(200, healthy));
    await renderHome(client);
    await waitFor(() =>
      expect(screen.getByTestId('health-status')).toHaveTextContent('تعذّر الاتصال بالخادم'),
    );
    await fireEvent.press(screen.getByText('إعادة المحاولة'));
    await waitFor(() =>
      expect(screen.getByTestId('health-status')).toHaveTextContent('الخادم يعمل'),
    );
  });

  it('switches to English and LTR', async () => {
    const { client } = clientReturning(json(200, healthy));
    await renderHome(client);
    await fireEvent.press(screen.getByLabelText('اللغة'));
    expect(screen.getByTestId('locale-root')).toHaveStyle({ direction: 'ltr' });
    await waitFor(() =>
      expect(screen.getByTestId('health-status')).toHaveTextContent('Server is up'),
    );
  });
});
