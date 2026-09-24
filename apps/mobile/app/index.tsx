import { SafeAreaView } from 'react-native-safe-area-context';
import { HomeScreen } from '@/components/HomeScreen';
import { api } from '@/lib/api';
import { colors } from '@/theme';

export default function Index() {
  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: colors.neutral[50] }}>
      <HomeScreen client={api} />
    </SafeAreaView>
  );
}
