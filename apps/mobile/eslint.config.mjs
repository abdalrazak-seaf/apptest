import base, { ignores } from '../../eslint.config.mjs';

const config = [
  ...base,
  { ignores: [...ignores, 'expo-env.d.ts'] },
  {
    files: ['*.config.js', 'babel.config.js', 'metro.config.js', 'jest.config.js'],
    rules: { '@typescript-eslint/no-require-imports': 'off' },
  },
];

export default config;
