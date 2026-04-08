import { neon } from "@neondatabase/serverless";

// You can retrieve this from .env.local: process.env.DATABASE_URL
const sql = neon(process.env.DATABASE_URL || "postgres://user:pass@ep-restless-glade-a5j94w5j.us-east-2.aws.neon.tech/neondb?sslmode=require");

export async function getReports() {
  // Mock fallback if the DB fails to connect
  try {
    const reports = await sql`SELECT * FROM reports ORDER BY created_at DESC`;
    return reports;
  } catch (error) {
    console.error("NeonDB Error:", error);
    return [];
  }
}

export async function createReport(data: any) {
  try {
    const result = await sql`
      INSERT INTO reports (usuario, descripcion, lat, lon, categoria, tipo, prioridad, probabilidad, status)
      VALUES (${data.usuario}, ${data.descripcion}, ${data.lat}, ${data.lon}, ${data.categoria}, ${data.tipo}, ${data.prioridad}, ${data.probabilidad}, ${data.status})
      RETURNING *
    `;
    return result[0];
  } catch (error) {
    console.error("NeonDB Insert Error:", error);
    throw new Error("Failed to create report");
  }
}
