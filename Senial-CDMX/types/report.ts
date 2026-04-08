export type ReportPriority = "alta" | "media" | "baja";

export interface Report {
  id: string;
  usuario: string;
  fecha: string;
  descripcion: string;
  categoria: "infraestructura" | "seguridad" | "areas_verdes" | "servicios" | "transporte" | "medio_ambiente";
  tipo: string;
  prioridad: ReportPriority;
  probabilidad: number;
  lat: number;
  lon: number;
  status: string;
}
