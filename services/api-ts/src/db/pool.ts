import { Pool } from 'pg';
import { env } from '../config/env.js';

export const pg = new Pool({ connectionString: env.DATABASE_URL });
