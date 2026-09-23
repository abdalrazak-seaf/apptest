module.exports = {
  preset: 'jest-expo',
  testMatch: ['<rootDir>/{app,src}/**/*.test.{ts,tsx}'],
  moduleNameMapper: { '^@/(.*)$': '<rootDir>/src/$1' },
  // jest-expo's defaults plus ESM-only i18n/client packages.
  transformIgnorePatterns: [
    'node_modules/(?!((jest-)?react-native|@react-native(-community)?)|expo(nent)?|@expo(nent)?/.*|@expo-google-fonts/.*|react-navigation|@react-navigation/.*|react-native-svg|use-intl|intl-messageformat|@formatjs/.*|icu-minify|openapi-fetch|@schummar/.*)',
  ],
};
