import {
  IBMPlexSansArabic_400Regular,
  IBMPlexSansArabic_600SemiBold,
  useFonts,
} from '@expo-google-fonts/ibm-plex-sans-arabic';
import { Stack } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import { LocaleProvider } from '@/i18n/LocaleProvider';

export default function RootLayout() {
  const [fontsLoaded, fontError] = useFonts({
    IBMPlexSansArabic_400Regular,
    IBMPlexSansArabic_600SemiBold,
  });
  // Render with system fonts if loading fails rather than blocking the app.
  if (!fontsLoaded && !fontError) return null;

  return (
    <SafeAreaProvider>
      <LocaleProvider>
        <StatusBar style="dark" />
        <Stack screenOptions={{ headerShown: false }} />
      </LocaleProvider>
    </SafeAreaProvider>
  );
}
