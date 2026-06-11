import fs from 'node:fs';
import path from 'node:path';
import { buildApp } from '../index.js';

const app = await buildApp();
const spec = app.swagger();
const out = path.resolve(process.cwd(), 'openapi.json');
fs.writeFileSync(out, JSON.stringify(spec, null, 2));
console.log('wrote', out);
await app.close();
