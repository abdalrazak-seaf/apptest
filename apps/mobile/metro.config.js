// Expo's default config detects the pnpm workspace and watches shared packages.
const { getDefaultConfig } = require('expo/metro-config');

module.exports = getDefaultConfig(__dirname);
