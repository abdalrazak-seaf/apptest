import { writeFileSync } from 'node:fs';
import { renderThemeCss } from '../src/css';

writeFileSync(new URL('../theme.css', import.meta.url), renderThemeCss());
