import dotenv from "dotenv";
import pg from "pg";

dotenv.config({ path: "../.env.local" });

const { Pool } = pg;

const pool = new Pool({
    connectionString: process.env.DATABASE_URL,
    ssl: {
        rejectUnauthorized: false
    }
});

pool.connect((err, client, release) => {
    if (err) {
        console.error("Erreur de connexion à PostgreSQL :", err);
    } else {
        console.log("Connexion réussie à Neon PostgreSQL !");
        release();
    }
});

export default pool;