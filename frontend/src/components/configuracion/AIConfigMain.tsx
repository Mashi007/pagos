import { useState } from 'react'
import { Settings, FileText, Zap, Database, X, Brain } from 'lucide-react'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../../components/ui/tabs'
import { ModelSelectionTab } from './ModelSelectionTab'
import { PromptConfigTab } from './PromptConfigTab'
import { AITestTab } from './AITestTab'
import { FineTuningTab } from './FineTuningTab'
import { RAGTab } from './RAGTab'
import { DiccionarioSemanticoTab } from './DiccionarioSemanticoTab'
import { DefinicionesCamposTab } from './DefinicionesCamposTab'
import { CalificacionesChatTab } from './CalificacionesChatTab'
import { type AIConfigState } from '../../types/aiConfig'

interface AIConfigMainProps {
  config: AIConfigState
  onConfigChange: (campo: keyof AIConfigState, valor: string) => void
  onSave: () => Promise<void>
  onVerifyAndSave: () => Promise<void>
  configuracionCorrecta: boolean
  verificandoConfig: boolean
  guardando: boolean
}

export function AIConfigMain({
  config,
  onConfigChange,
  onSave,
  onVerifyAndSave,
  configuracionCorrecta,
  verificandoConfig,
  guardando,
}: AIConfigMainProps) {
  const [activeTab, setActiveTab] = useState('model')
  const [activeHybridTab, setActiveHybridTab] = useState('fine-tuning')

  return (
    <div className="space-y-6">
      <div className="bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-200 rounded-xl p-5 shadow-sm">
        <div className="flex items-center gap-3 mb-2">
          <div className="p-2 bg-blue-100 rounded-lg">
            <Brain className="h-6 w-6 text-blue-600" />
          </div>
          <div>
            <h3 className="font-bold text-lg text-blue-900">Configuración de Inteligencia Artificial</h3>
            <p className="text-sm text-blue-700 mt-1">
              Configura ChatGPT para respuestas automáticas contextualizadas en WhatsApp usando tus documentos como base de conocimiento.
            </p>
          </div>
        </div>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
        <TabsList className="grid w-full grid-cols-3 bg-gray-100/50 p-1 rounded-lg">
          <TabsTrigger
            value="model"
            className="flex items-center gap-2 data-[state=active]:bg-white data-[state=active]:shadow-sm transition-all duration-200"
          >
            <Settings className="h-4 w-4" />
            Modelo
          </TabsTrigger>
          <TabsTrigger
            value="prompt"
            className="flex items-center gap-2 data-[state=active]:bg-white data-[state=active]:shadow-sm transition-all duration-200"
          >
            <FileText className="h-4 w-4" />
            Prompt
          </TabsTrigger>
          <TabsTrigger
            value="test"
            className="flex items-center gap-2 data-[state=active]:bg-white data-[state=active]:shadow-sm transition-all duration-200"
          >
            <Zap className="h-4 w-4" />
            Prueba
          </TabsTrigger>
        </TabsList>

        <TabsContent value="model" className="space-y-4 mt-6">
          <ModelSelectionTab
            config={config}
            onConfigChange={onConfigChange}
            onSave={onSave}
            onVerifyAndSave={onVerifyAndSave}
            configuracionCorrecta={configuracionCorrecta}
            verificandoConfig={verificandoConfig}
            guardando={guardando}
          />
        </TabsContent>

        <TabsContent value="prompt" className="space-y-4 mt-6">
          <PromptConfigTab />
        </TabsContent>

        <TabsContent value="test" className="space-y-4 mt-6">
          <AITestTab config={config} />
        </TabsContent>
      </Tabs>

      {/* Sistema Híbrido Tab */}
      <div className="border-t pt-6">
        <div className="mb-4">
          <h3 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
            <Zap className="h-5 w-5 text-blue-600" />
            Sistema Híbrido
          </h3>
          <p className="text-sm text-gray-600 mt-1">
            Configuración avanzada: Fine-tuning, RAG, Diccionario Semántico, Campos y Calificaciones
          </p>
        </div>

        <Tabs value={activeHybridTab} onValueChange={setActiveHybridTab} className="w-full">
          <TabsList className="grid w-full grid-cols-5 bg-gray-100/50 p-1 rounded-lg">
            <TabsTrigger
              value="fine-tuning"
              className="flex items-center gap-2 data-[state=active]:bg-white data-[state=active]:shadow-sm transition-all duration-200"
            >
              <Brain className="h-4 w-4" />
              Fine-tuning
            </TabsTrigger>
            <TabsTrigger
              value="rag"
              className="flex items-center gap-2 data-[state=active]:bg-white data-[state=active]:shadow-sm transition-all duration-200"
            >
              <Zap className="h-4 w-4" />
              RAG
            </TabsTrigger>
            <TabsTrigger
              value="diccionario"
              className="flex items-center gap-2 data-[state=active]:bg-white data-[state=active]:shadow-sm transition-all duration-200"
            >
              <FileText className="h-4 w-4" />
              Diccionario
            </TabsTrigger>
            <TabsTrigger
              value="campos"
              className="flex items-center gap-2 data-[state=active]:bg-white data-[state=active]:shadow-sm transition-all duration-200"
            >
              <Database className="h-4 w-4" />
              Campos
            </TabsTrigger>
            <TabsTrigger
              value="calificaciones"
              className="flex items-center gap-2 data-[state=active]:bg-white data-[state=active]:shadow-sm transition-all duration-200"
            >
              <X className="h-4 w-4" />
              Calificaciones
            </TabsTrigger>
          </TabsList>

          <TabsContent value="fine-tuning" className="mt-6">
            <FineTuningTab />
          </TabsContent>

          <TabsContent value="rag" className="mt-6">
            <RAGTab />
          </TabsContent>

          <TabsContent value="diccionario" className="mt-6">
            <DiccionarioSemanticoTab />
          </TabsContent>

          <TabsContent value="campos" className="mt-6">
            <DefinicionesCamposTab />
          </TabsContent>

          <TabsContent value="calificaciones" className="mt-6">
            <CalificacionesChatTab />
          </TabsContent>
        </Tabs>
      </div>
    </div>
  )
}
