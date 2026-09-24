import { createApiClient } from '@thiqa/api-client';
import { Platform } from 'react-native';

// Android emulators reach the host machine via 10.0.2.2; on a physical device set
// EXPO_PUBLIC_API_URL to your computer's LAN address (see .env.example).
const fallback = Platform.OS === 'android' ? 'http://10.0.2.2:8000' : 'http://localhost:8000';

export const apiBaseUrl = process.env.EXPO_PUBLIC_API_URL || fallback;

export const api = createApiClient(apiBaseUrl);
