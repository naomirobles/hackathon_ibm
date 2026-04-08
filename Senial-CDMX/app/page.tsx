import ReportForm from "@/components/ReportForm";

export default function Home() {
  return (
    <div className="min-h-screen bg-[#F5F3EE] pt-8 pb-20 sm:pt-12 sm:pb-24">
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 space-y-10">
        
        {/* Header */}
        <div className="text-center max-w-2xl mx-auto space-y-4">
          <h1 className="text-3xl sm:text-4xl font-serif text-[#1A1917] tracking-tight">
            Reporte Ciudadano
          </h1>
          <p className="text-base sm:text-lg text-gray-600">
            Describe el problema y nuestro sistema lo analizará automáticamente para canalizarlo a las autoridades correspondientes.
          </p>
        </div>

        {/* Form Container */}
        <div className="flex justify-center">
          <ReportForm />
        </div>

      </main>
    </div>
  );
}
