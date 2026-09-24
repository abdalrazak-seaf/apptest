import nextVitals from 'eslint-config-next/core-web-vitals';
import nextTs from 'eslint-config-next/typescript';
import { ignores } from '../../eslint.config.mjs';

const config = [{ ignores }, ...nextVitals, ...nextTs];

export default config;
