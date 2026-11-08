import express from "express";
import cors from "cors";
import helmet from "helmet";
import dotenv from "dotenv";

dotenv.config({ path: "../.env.local" });
console.log("DATABASE_URL chargée :", !!process.env.DATABASE_URL);

const app = express();

// Middlewares
app.use(helmet());
app.use(cors());
app.use(express.json());

// Test du serveur
app.get("/api/health", (req, res) => {
    res.status(200).json({
        status: "success",
        message: "FinTech Backend is running!"
    });
});

// Port du serveur


const PORT = 4000;

app.listen(PORT, () => {
    console.log(`Server running on http://localhost:${PORT}`);
});