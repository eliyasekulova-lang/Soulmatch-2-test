import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { pg } from './pool.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const migrationsDir = path.resolve(__dirname, '../../migrations');

await pg.query(`CREATE TABLE IF NOT EXISTS schema_migrations (name text primary key, applied_at timestamptz not null default now())`);

const files = fs.readdirSync(migrationsDir).filter((f) => f.endsWith('.sql')).sort();
for (const file of files) {
  const exists = await pg.query('SELECT 1 FROM schema_migrations WHERE name=$1', [file]);
  if (exists.rowCount) continue;
  const sql = fs.readFileSync(path.join(migrationsDir, file), 'utf8');
  await pg.query('BEGIN');
  try {
    await pg.query(sql);
    await pg.query('INSERT INTO schema_migrations(name) VALUES($1)', [file]);
    await pg.query('COMMIT');
    console.log('applied', file);
  } catch (e) {
    await pg.query('ROLLBACK');
    throw e;
  }
}
await pg.end();
