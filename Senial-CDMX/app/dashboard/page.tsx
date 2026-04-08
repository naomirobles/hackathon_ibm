import { Card, CardHeader, CardTitle, CardDescription } from "@/components/ui/Card";
import ReportTable from "@/components/ReportTable";
import { Badge } from "@/components/ui/Badge";
import { BarChart3, FileText, AlertTriangle, CheckCircle } from "lucide-react";

export default function Dashboard() {
  return (
    <div className="min-h-screen bg-[#F5F3EE] py-8 sm:py-12">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 space-y-8">
        
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl sm:text-3xl font-serif text-[#1A1917]">Dashboard Gubernamental</h1>
            <p className="text-sm text-gray-600 mt-1">CDMX · Secretaría de Obras y Servicios</p>
          </div>
          <Badge variant="info" className="w-fit">Vista Consolidada</Badge>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-6">
          <Card className="p-5 sm:p-6 flex flex-col justify-between">
            <div className="flex justify-between items-start">
              <span className="text-sm font-medium text-gray-500 uppercase tracking-wider">Total Reportes</span>
              <FileText className="text-gray-400" size={20} />
            </div>
            <div className="mt-4">
              <div className="text-3xl font-serif text-gray-900">248</div>
              <div className="text-sm text-green-600 mt-1 font-medium">↑ 12% este mes</div>
            </div>
          </Card>
          
          <Card className="p-5 sm:p-6 flex flex-col justify-between border-[#C0392B]/20 bg-[#FBEAE8]/30">
            <div className="flex justify-between items-start">
              <span className="text-sm font-medium text-[#C0392B] uppercase tracking-wider">Prioridad Alta</span>
              <AlertTriangle className="text-[#C0392B]" size={20} />
            </div>
            <div className="mt-4">
              <div className="text-3xl font-serif text-[#C0392B]">31</div>
              <div className="text-sm text-[#C0392B]/80 mt-1 font-medium">Requieren atención urgente</div>
            </div>
          </Card>

          <Card className="p-5 sm:p-6 flex flex-col justify-between">
            <div className="flex justify-between items-start">
              <span className="text-sm font-medium text-gray-500 uppercase tracking-wider">Prob. Atención</span>
              <BarChart3 className="text-[#1A4A7A]" size={20} />
            </div>
            <div className="mt-4">
              <div className="text-3xl font-serif text-gray-900">72%</div>
              <div className="text-sm text-green-600 mt-1 font-medium">↑ 5% vs mes anterior</div>
            </div>
          </Card>

          <Card className="p-5 sm:p-6 flex flex-col justify-between">
            <div className="flex justify-between items-start">
              <span className="text-sm font-medium text-gray-500 uppercase tracking-wider">Resueltos</span>
              <CheckCircle className="text-[#2D5A3D]" size={20} />
            </div>
            <div className="mt-4">
              <div className="text-3xl font-serif text-gray-900">156</div>
              <div className="text-sm text-[#2D5A3D] mt-1 font-medium">Este trimestre</div>
            </div>
          </Card>
        </div>

        {/* Tables & Lists */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          <Card className="lg:col-span-2 p-0 sm:p-0 overflow-hidden">
            <CardHeader className="p-6 border-b border-gray-100 mb-0">
              <CardTitle>Últimos Reportes</CardTitle>
              <CardDescription>Reportes ciudadanos procesados por IA.</CardDescription>
            </CardHeader>
            <ReportTable />
          </Card>

          <Card className="p-6">
            <CardTitle className="mb-6">Distribución por Categoría</CardTitle>
            <div className="space-y-5">
              {[
                { label: 'Infraestructura', pct: 65, val: 89, color: 'bg-[#1A4A7A]' },
                { label: 'Servicios', pct: 45, val: 67, color: 'bg-[#B7610A]' },
                { label: 'Seguridad', pct: 25, val: 31, color: 'bg-[#C0392B]' },
                { label: 'Áreas verdes', pct: 20, val: 28, color: 'bg-[#2D5A3D]' },
              ].map((cat, i) => (
                <div key={i} className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-600 font-medium">{cat.label}</span>
                    <span className="text-gray-900 font-semibold">{cat.val}</span>
                  </div>
                  <div className="h-2 w-full bg-gray-100 rounded-full overflow-hidden">
                    <div className={`h-full ${cat.color} rounded-full`} style={{ width: `${cat.pct}%` }} />
                  </div>
                </div>
              ))}
            </div>
          </Card>
        </div>

      </div>
    </div>
  );
}
