import type { ApiClient } from '@thiqa/api-client';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { useTranslations } from 'use-intl';
import { useLocale } from '@/i18n/LocaleProvider';
import { useHealth } from '@/lib/useHealth';
import { colors, fonts, fontSize, minTapTarget, radii, spacing } from '@/theme';

export function HomeScreen({ client }: { client: ApiClient }) {
  const t = useTranslations();
  const { locale, setLocale } = useLocale();
  const { state, retry } = useHealth(client);

  return (
    <ScrollView contentContainerStyle={styles.container}>
      <View style={styles.header}>
        <Text style={styles.brand}>{t('app.name')}</Text>
        <Pressable
          accessibilityRole="button"
          accessibilityLabel={t('language.label')}
          onPress={() => setLocale(locale === 'ar' ? 'en' : 'ar')}
          style={styles.button}
        >
          <Text style={styles.buttonText}>{t('language.switchTo')}</Text>
        </Pressable>
      </View>

      <Text accessibilityRole="header" style={styles.title}>
        {t('home.title')}
      </Text>
      <Text style={styles.body}>{t('app.tagline')}</Text>
      <Text style={styles.muted}>{t('home.comingSoon')}</Text>

      <View style={styles.card}>
        <Text style={styles.cardTitle}>{t('health.title')}</Text>
        <View style={styles.statusRow} accessibilityLiveRegion="polite">
          <View
            style={[
              styles.dot,
              { backgroundColor: state.kind === 'error' ? colors.danger : colors.success },
              state.kind === 'loading' && { backgroundColor: colors.neutral[300] },
            ]}
          />
          <Text testID="health-status" style={styles.status}>
            {state.kind === 'loading'
              ? t('health.checking')
              : state.kind === 'ok'
                ? t('health.ok')
                : t('health.error')}
          </Text>
        </View>
        {state.kind === 'ok' && (
          <Text style={styles.muted}>
            {t('health.details', {
              version: state.health.version,
              environment: state.health.environment,
            })}
          </Text>
        )}
        {state.kind === 'error' && (
          <Pressable accessibilityRole="button" onPress={retry} style={styles.button}>
            <Text style={styles.buttonText}>{t('health.retry')}</Text>
          </Pressable>
        )}
      </View>
    </ScrollView>
  );
}

const text = { fontFamily: fonts.regular, color: colors.neutral[900], textAlign: 'auto' } as const;

const styles = StyleSheet.create({
  container: { padding: spacing[4], gap: spacing[4], backgroundColor: colors.neutral[50] },
  header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  brand: { ...text, fontFamily: fonts.semibold, fontSize: fontSize.xl, color: colors.brand[700] },
  title: { ...text, fontFamily: fonts.semibold, fontSize: fontSize['2xl'] },
  body: { ...text, fontSize: fontSize.lg, color: colors.neutral[700] },
  muted: { ...text, fontSize: fontSize.sm, color: colors.neutral[700] },
  card: {
    gap: spacing[2],
    padding: spacing[5],
    borderRadius: radii.lg,
    borderWidth: 1,
    borderColor: colors.neutral[200],
    backgroundColor: colors.neutral[0],
  },
  cardTitle: {
    ...text,
    fontFamily: fonts.semibold,
    fontSize: fontSize.sm,
    color: colors.neutral[700],
  },
  statusRow: { flexDirection: 'row', alignItems: 'center', gap: spacing[2] },
  dot: { width: 12, height: 12, borderRadius: radii.full },
  status: { ...text, fontSize: fontSize.lg },
  button: {
    minHeight: minTapTarget,
    minWidth: minTapTarget,
    paddingHorizontal: spacing[4],
    borderRadius: radii.md,
    borderWidth: 1,
    borderColor: colors.neutral[300],
    alignItems: 'center',
    justifyContent: 'center',
    alignSelf: 'flex-start',
  },
  buttonText: { ...text, fontFamily: fonts.semibold, color: colors.brand[700] },
});
