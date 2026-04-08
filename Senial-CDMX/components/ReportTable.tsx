import { MOCK_REPORTS, CATEGORIES } from "@/lib/data";
import { Badge } from "./ui/Badge";

export default function ReportTable() {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left border-collapse">
        <thead>
          <tr className="border-b border-gray-200">
            <th className="px-4 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wider">ID</th>
            <th className="px-4 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wider">Problema</th>
            <th className="px-4 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wider">Categoría</th>
            <th className="px-4 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wider">Prioridad</th>
            <th className="px-4 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wider">Probabilidad</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {MOCK_REPORTS.map((report) => (
            <tr key={report.id} className="hover:bg-gray-50 transition-colors group cursor-pointer">
              <td className="px-4 py-4">
                <span className="text-xs font-mono text-gray-500 group-hover:text-gray-900 transition-colors">{report.id}</span>
              </td>
              <td className="px-4 py-4">
                <div className="text-sm font-medium text-gray-900">{report.tipo}</div>
                <div className="text-xs text-gray-500 truncate max-w-[200px] mt-0.5">{report.descripcion}</div>
              </td>
              <td className="px-4 py-4">
                <Badge variant="default" className={CATEGORIES[report.categoria as keyof typeof CATEGORIES]?.color}>
                  {CATEGORIES[report.categoria as keyof typeof CATEGORIES]?.label}
                </Badge>
              </td>
              <td className="px-4 py-4">
                <Badge variant={report.prioridad}>{report.prioridad}</Badge>
              </td>
              <td className="px-4 py-4">
                <div className="flex items-center gap-3">
                  <div className="w-full h-1.5 bg-gray-100 rounded-full overflow-hidden max-w-[60px]">
                    <div 
                      className={`h-full ${report.prioridad === 'alta' ? 'bg-[#C0392B]' : report.prioridad === 'media' ? 'bg-[#B7610A]' : 'bg-[#2D5A3D]'}`} 
                      style={{ width: `${report.probabilidad}%` }}
                    />
                  </div>
                  <span className="text-xs font-medium text-gray-700">{report.probabilidad}%</span>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
