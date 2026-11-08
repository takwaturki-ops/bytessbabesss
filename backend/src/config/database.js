import pg from "pg";

const { Pool } = pg;

const pool = new Pool({
    connectionString: process.env.DATABASE_URL,
    ssl: {
        rejectUnauthorized: false
    }
});

// Tester la connexion
pool.connect((err, client, release) => {
    if (err) {
        console.error("Erreur de connexion à PostgreSQL :", err.message);
    } else {
        console.log("Connexion réussie à Neon PostgreSQL !");
        release();
    }
});

export default pool;