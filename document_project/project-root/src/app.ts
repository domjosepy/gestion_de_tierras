// src/app.ts

import express from 'express';
import { json } from 'body-parser';
import { someMiddleware } from './middleware/someMiddleware'; // Example middleware
import { routes } from './routes'; // Example routes

const app = express();
const PORT = process.env.PORT || 3000;

// Middleware setup
app.use(json());
app.use(someMiddleware);

// Routes setup
app.use('/api', routes);

// Start the server
app.listen(PORT, () => {
    console.log(`Server is running on http://localhost:${PORT}`);
});