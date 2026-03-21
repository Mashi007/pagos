import { useState } from 'react'

import { Settings, FileText, Zap, Database, X, Brain } from 'lucide-react'

import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from '../../components/ui/tabs'

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
      <div className="rounded-xl border border-blue-200 bg-gradient-to-r from-blue-50 to-indigo-50 p-5 shadow-sm">
        <div className="mb-2 flex items-center gap-3">
          <div className="rounded-lg bg-blue-100 p-2">
            <Brain className="h-6 w-6 text-blue-600" />
          </div>

          <div>
            <h3 className="text-lg font-bold text-blue-900">
              Configuración de Inteligencia Artificial
            </h3>

            <p className="mt-1 text-sm text-blue-700">
              Configura ChatGPT para respuestas automáticas contextualizadas en
              WhatsApp usando tus documentos como base de conocimiento.
            </p>
          </div>
        </div>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
        <TabsList className="grid w-full grid-cols-3 rounded-lg bg-gray-100/50 p-1">
          <TabsTrigger
            value="model"
            className="flex items-center gap-2 transition-all duration-200 data-[state=active]:bg-white data-[state=active]:shadow-sm"
          >
            <Settings className="h-4 w-4" />
            Modelo
          </TabsTrigger>

          <TabsTrigger
            value="prompt"
            className="flex items-center gap-2 transition-all duration-200 data-[state=active]:bg-white data-[state=active]:shadow-sm"
          >
            <FileText className="h-4 w-4" />
            Prompt
          </TabsTrigger>

          <TabsTrigger
            value="test"
            className="flex items-center gap-2 transition-all duration-200 data-[state=active]:bg-white data-[state=active]:shadow-sm"
          >
            <Zap className="h-4 w-4" />
            Prueba
          </TabsTrigger>
        </TabsList>

        <TabsContent value="model" className="mt-6 space-y-4">
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

        <TabsContent value="prompt" className="mt-6 space-y-4">
          <PromptConfigTab />
        </TabsContent>

        <TabsContent value="test" className="mt-6 space-y-4">
          <AITestTab config={config} />
        </TabsContent>
      </Tabs>

      {/* Sistema Híbrido Tab */}

      <div className="border-t pt-6">
        <div className="mb-4">
          <h3 className="flex items-center gap-2 text-lg font-semibold text-gray-900">
            <Zap className="h-5 w-5 text-blue-600" />
            Sistema Híbrido
          </h3>

          <p className="mt-1 text-sm text-gray-600">
            Configuración avanzada: Fine-tuning, RAG, Diccionario Semántico,
            Campos y Calificaciones
          </p>
        </div>

        <Tabs
          value={activeHybridTab}
          onValueChange={setActiveHybridTab}
          className="w-full"
        >
          <TabsList className="grid w-full grid-cols-5 rounded-lg bg-gray-100/50 p-1">
            <TabsTrigger
              value="fine-tuning"
              className="flex items-center gap-2 transition-all duration-200 data-[state=active]:bg-white data-[state=active]:shadow-sm"
            >
              <Brain className="h-4 w-4" />
              Fine-tuning
            </TabsTrigger>

            <TabsTrigger
              value="rag"
              className="flex items-center gap-2 transition-all duration-200 data-[state=active]:bg-white data-[state=active]:shadow-sm"
            >
              <Zap className="h-4 w-4" />
              RAG
            </TabsTrigger>

            <TabsTrigger
              value="diccionario"
              className="flex items-center gap-2 transition-all duration-200 data-[state=active]:bg-white data-[state=active]:shadow-sm"
            >
              <FileText className="h-4 w-4" />
              Diccionario
            </TabsTrigger>

            <TabsTrigger
              value="campos"
              className="flex items-center gap-2 transition-all duration-200 data-[state=active]:bg-white data-[state=active]:shadow-sm"
            >
              <Database className="h-4 w-4" />
              Campos
            </TabsTrigger>

            <TabsTrigger
              value="calificaciones"
              className="flex items-center gap-2 transition-all duration-200 data-[state=active]:bg-white data-[state=active]:shadow-sm"
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
