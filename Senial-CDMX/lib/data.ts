import { type Report } from "@/types/report";

export const CATEGORIES = {
  infraestructura: { label: "Infraestructura", color: "bg-secondary-light text-secondary" },
  seguridad: { label: "Seguridad", color: "bg-danger-light text-danger" },
  areas_verdes: { label: "Áreas verdes", color: "bg-primary-light text-primary" },
  servicios: { label: "Servicios públicos", color: "bg-warn-light text-warn" },
  transporte: { label: "Transporte", color: "bg-secondary-light text-secondary" },
  medio_ambiente: { label: "Medio ambiente", color: "bg-primary-light text-primary" },
};

export const MOCK_REPORTS: Report[] = [
  {
    id: "RPT-001",
    usuario: "Ana García",
    fecha: "2025-04-05",
    descripcion: "Bache profundo en Av. Insurgentes Sur frente al metro Mixcoac, peligroso para vehículos y ciclistas.",
    categoria: "infraestructura",
    tipo: "Bache vial",
    prioridad: "alta",
    probabilidad: 87,
    lat: 19.3699,
    lon: -99.187,
    status: "procesado",
  },
  {
    id: "RPT-002",
    usuario: "Carlos Mendez",
    fecha: "2025-04-04",
    descripcion: "Luminaria apagada en Calle Amores 245, Colonia del Valle, inseguro en las noches.",
    categoria: "infraestructura",
    tipo: "Alumbrado público",
    prioridad: "media",
    probabilidad: 72,
    lat: 19.38,
    lon: -99.16,
    status: "procesado",
  },
  {
    id: "RPT-003",
    usuario: "María Torres",
    fecha: "2025-04-04",
    descripcion: "Basura acumulada en parque Hundido desde hace 3 días, mal olor y riesgo sanitario.",
    categoria: "medio_ambiente",
    tipo: "Manejo de residuos",
    prioridad: "media",
    probabilidad: 65,
    lat: 19.3752,
    lon: -99.1814,
    status: "procesado",
  },
];
