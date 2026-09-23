import { defaultLocale, getDirection, messages, type Locale } from '@thiqa/i18n';
import { createContext, useContext, useMemo, useState, type ReactNode } from 'react';
import { I18nManager, StyleSheet, View } from 'react-native';
import { IntlProvider } from 'use-intl';

// Arabic-first: native layout defaults to RTL (also set via `forcesRTL` in app.json).
// Switching to English flips direction on the root view, so no app reload is needed.
I18nManager.allowRTL(true);
I18nManager.forceRTL(true);

type LocaleContextValue = { locale: Locale; setLocale: (locale: Locale) => void };

const LocaleContext = createContext<LocaleContextValue | null>(null);

export function useLocale(): LocaleContextValue {
  const value = useContext(LocaleContext);
  if (!value) throw new Error('useLocale must be used inside <LocaleProvider>');
  return value;
}

export function LocaleProvider({
  children,
  initialLocale = defaultLocale,
}: {
  children: ReactNode;
  initialLocale?: Locale;
}) {
  const [locale, setLocale] = useState<Locale>(initialLocale);
  const value = useMemo(() => ({ locale, setLocale }), [locale]);
  const direction = getDirection(locale);

  return (
    <LocaleContext.Provider value={value}>
      <IntlProvider locale={locale} messages={messages[locale]} timeZone="Asia/Riyadh">
        <View testID="locale-root" style={[styles.root, { direction }]}>
          {children}
        </View>
      </IntlProvider>
    </LocaleContext.Provider>
  );
}

const styles = StyleSheet.create({ root: { flex: 1 } });
