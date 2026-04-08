import Link from "next/link";
import { User, Menu } from "lucide-react";
import LogoPlaceholder from "./LogoPlaceholder";

export default function Navbar() {
  return (
    <nav className="sticky top-0 z-50 w-full bg-white/80 backdrop-blur-md border-b border-gray-200">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16 sm:h-20">
          <div className="flex-shrink-0 flex items-center">
            <Link href="/" className="flex items-center gap-3 group">
              <LogoPlaceholder className="h-8 w-8 text-[#2D5A3D] group-hover:opacity-80 transition-opacity" />
              <span className="font-serif text-xl sm:text-2xl text-[#1A1917] hidden sm:block">Señal CDMX</span>
            </Link>
          </div>
          
          <div className="hidden md:flex items-center space-x-1">
            <Link href="/" className="px-4 py-2 rounded-md text-sm font-medium text-gray-600 hover:text-gray-900 hover:bg-gray-50 transition-colors">
              Nuevo Reporte
            </Link>
            <Link href="/mis-reportes" className="px-4 py-2 rounded-md text-sm font-medium text-gray-600 hover:text-gray-900 hover:bg-gray-50 transition-colors">
              Mis Reportes
            </Link>
            <Link href="/dashboard" className="px-4 py-2 rounded-md text-sm font-medium text-gray-600 hover:text-gray-900 hover:bg-gray-50 transition-colors">
              Dashboard (Gobierno)
            </Link>
          </div>

          <div className="flex items-center gap-4">
            <button className="flex items-center gap-2 px-3 py-1.5 rounded-full border border-gray-200 hover:bg-gray-50 transition-colors text-sm font-medium text-gray-700">
              <div className="w-6 h-6 rounded-full bg-[#1A4A7A] flex items-center justify-center text-white text-xs">
                <User size={14} />
              </div>
              <span className="hidden sm:block">Ciudadano</span>
            </button>
            <button className="md:hidden p-2 text-gray-600 hover:bg-gray-100 rounded-md">
              <Menu size={20} />
            </button>
          </div>
        </div>
      </div>
    </nav>
  );
}
