"use client";

import { useState } from "react";
import { Button } from "./ui/Button";
import { Card, CardHeader, CardTitle, CardDescription } from "./ui/Card";
import { Mic, MapPin, Upload, Loader2, CheckCircle2 } from "lucide-react";

export default function ReportForm() {
  const [step, setStep] = useState(1);
  const [isRecording, setIsRecording] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);

  const handleNext = () => {
    if (step === 2) {
      setIsProcessing(true);
      setStep(3);
      // Simulate AI processing
      setTimeout(() => {
        setIsProcessing(false);
        setStep(4);
      }, 2500);
    } else {
      setStep(s => s + 1);
    }
  };

  return (
    <div className="max-w-2xl mx-auto w-full">
      {/* Stepper */}
      <div className="flex justify-between mb-8 sm:mb-12 relative">
        <div className="absolute top-1/2 left-0 w-full h-0.5 bg-gray-200 -z-10 -translate-y-1/2" />
        {[1, 2, 3, 4].map((s) => (
          <div key={s} className="flex flex-col items-center gap-2">
            <div
              className={`w-8 h-8 sm:w-10 sm:h-10 rounded-full flex items-center justify-center text-sm font-medium border-2 transition-colors
                ${step > s ? 'bg-[#2D5A3D] border-[#2D5A3D] text-white' : 
                  step === s ? 'bg-white border-[#2D5A3D] text-[#2D5A3D]' : 
                  'bg-white border-gray-300 text-gray-400'}`}
            >
              {step > s ? <CheckCircle2 size={18} /> : s}
            </div>
            <span className={`text-xs sm:text-sm font-medium ${step >= s ? 'text-gray-900' : 'text-gray-400'}`}>
              {s === 1 ? 'Descripción' : s === 2 ? 'Ubicación' : s === 3 ? 'Análisis IA' : 'Resultado'}
            </span>
          </div>
        ))}
      </div>

      {/* Steps Content */}
      <Card className="min-h-[400px]">
        {step === 1 && (
          <div className="space-y-6">
            <CardHeader className="px-0 pt-0">
              <CardTitle>Describe el problema</CardTitle>
              <CardDescription>Puedes escribir o grabar un mensaje de voz explicando la situación.</CardDescription>
            </CardHeader>
            
            <div className="space-y-4">
              <textarea 
                className="w-full min-h-[120px] p-4 bg-gray-50 border border-gray-200 rounded-lg focus:ring-2 focus:ring-[#2D5A3D] focus:border-transparent transition-all resize-none"
                placeholder="Ej: Hay un bache muy profundo en la esquina de Insurgentes y Viaducto..."
              />
              
              <div className="flex items-center justify-center gap-4 p-6 bg-gray-50 rounded-lg border border-gray-200 border-dashed">
                <button 
                  onClick={() => setIsRecording(!isRecording)}
                  className={`w-14 h-14 rounded-full flex items-center justify-center transition-all shadow-sm
                    ${isRecording ? 'bg-red-500 animate-pulse text-white' : 'bg-white text-gray-700 hover:bg-gray-100'}`}
                >
                  <Mic size={24} />
                </button>
                <div className="text-sm text-gray-600 font-medium">
                  {isRecording ? 'Grabando... Pulsa para detener' : 'Presiona para usar tu voz'}
                </div>
              </div>

              <div className="flex items-center justify-center gap-2 p-6 bg-gray-50 rounded-lg border border-gray-200 border-dashed cursor-pointer hover:bg-gray-100 transition-colors">
                <Upload size={20} className="text-gray-400" />
                <span className="text-sm text-gray-600">Subir foto de evidencia (Opcional)</span>
              </div>
            </div>

            <div className="flex justify-end pt-4 border-t border-gray-100">
              <Button onClick={handleNext}>Continuar a Ubicación</Button>
            </div>
          </div>
        )}

        {step === 2 && (
          <div className="space-y-6">
            <CardHeader className="px-0 pt-0">
              <CardTitle>Ubicación del problema</CardTitle>
              <CardDescription>Confirma la ubicación para que el reporte sea preciso.</CardDescription>
            </CardHeader>

            <div className="h-[200px] bg-[#E8EDE8] rounded-lg border border-gray-200 flex items-center justify-center relative overflow-hidden">
              <MapPin size={32} className="text-[#C0392B] z-10 drop-shadow-md" />
              {/* Fake Map Grid */}
              <div className="absolute inset-0 opacity-20" style={{ backgroundImage: 'linear-gradient(#2D5A3D 1px, transparent 1px), linear-gradient(90deg, #2D5A3D 1px, transparent 1px)', backgroundSize: '20px 20px' }}></div>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Dirección aproximada</label>
                <input 
                  type="text" 
                  defaultValue="Av. Insurgentes Sur 890, Col. del Valle, CDMX"
                  className="w-full p-3 bg-gray-50 border border-gray-200 rounded-lg focus:ring-2 focus:ring-[#2D5A3D] focus:border-transparent transition-all"
                />
              </div>
            </div>

            <div className="flex justify-between pt-4 border-t border-gray-100">
              <Button variant="outline" onClick={() => setStep(1)}>Volver</Button>
              <Button onClick={handleNext}>Enviar y Analizar</Button>
            </div>
          </div>
        )}

        {step === 3 && (
          <div className="flex flex-col items-center justify-center h-[300px] space-y-6">
            <Loader2 size={48} className="text-[#2D5A3D] animate-spin" />
            <div className="text-center space-y-2">
              <h3 className="font-serif text-xl font-medium">Analizando reporte con Watsonx IA...</h3>
              <p className="text-sm text-gray-500 max-w-[280px]">Procesando ubicación, cruzando datos de servicios y evaluando prioridad.</p>
            </div>
          </div>
        )}

        {step === 4 && (
          <div className="space-y-6">
            <div className="flex items-start justify-between pb-6 border-b border-gray-100">
              <div>
                <CardTitle className="mb-2 text-green-700 flex items-center gap-2">
                  <CheckCircle2 size={24} />
                  Reporte Registrado
                </CardTitle>
                <div className="flex gap-2">
                  <span className="px-2.5 py-1 rounded-md bg-[#FBEAE8] text-[#C0392B] text-xs font-medium uppercase tracking-wider">Alta Prioridad</span>
                  <span className="px-2.5 py-1 rounded-md bg-gray-100 text-gray-700 text-xs font-medium uppercase tracking-wider">Infraestructura</span>
                </div>
              </div>
              <div className="text-right">
                <div className="text-3xl font-serif text-[#C0392B] leading-none">87%</div>
                <div className="text-xs text-gray-500 mt-1">Probabilidad de atención</div>
              </div>
            </div>

            <div className="p-4 bg-[#E8F0FA] rounded-lg border border-[#1A4A7A]/10">
              <h4 className="text-sm font-medium text-[#1A4A7A] mb-1">Análisis de IA:</h4>
              <p className="text-sm text-[#1A4A7A]/80 leading-relaxed">
                El problema reportado afecta una vía principal y representa un riesgo inmediato para la movilidad. Basado en reportes históricos y la ausencia de mantenimiento reciente, se requiere atención prioritaria de la Secretaría de Obras.
              </p>
            </div>

            <div className="flex justify-end pt-4 gap-3">
              <Button variant="outline" onClick={() => setStep(1)}>Crear otro</Button>
              <Button>Ver mis reportes</Button>
            </div>
          </div>
        )}
      </Card>
    </div>
  );
}
