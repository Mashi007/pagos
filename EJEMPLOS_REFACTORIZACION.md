# Ejemplos Prácticos de Refactorización

## Ejemplo 1: Refactorización de `pagos.py`

### ANTES (Monolítico - 2337 líneas)
```python
# backend/app/api/v1/endpoints/pagos.py - ANTES (Simplificado)

@router.post("/pagos")
def crear_pago(pago_data: PagoCreacionSchema, db: Session = Depends(get_db)):
    # Validar cliente
    cliente = db.query(Cliente).filter(Cliente.id == pago_data.cliente_id).first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    
    # Validar cuenta
    cuenta = db.query(Cuenta).filter(Cuenta.id == pago_data.cuenta_id).first()
    if not cuenta:
        raise HTTPException(status_code=404, detail="Cuenta no encontrada")
    
    # Validar monto
    if pago_data.monto <= 0:
        raise HTTPException(status_code=400, detail="Monto debe ser mayor a 0")
    
    # Calcular tasa
    tasa = db.query(TasaCambio).order_by(TasaCambio.fecha.desc()).first()
    monto_en_dolares = pago_data.monto / tasa.valor if tasa else pago_data.monto
    
    # Crear pago
    nuevo_pago = Pago(
        cliente_id=pago_data.cliente_id,
        cuenta_id=pago_data.cuenta_id,
        monto=pago_data.monto,
        monto_dolares=monto_en_dolares,
        estado="pendiente"
    )
    
    db.add(nuevo_pago)
    db.commit()
    db.refresh(nuevo_pago)
    
    return nuevo_pago

# ... 300+ líneas más de endpoints
```

### DESPUÉS (Refactorizado)

#### Paso 1: Crear servicios
```python
# backend/app/services/pagos/__init__.py
from .pagos_service import PagosService
from .pagos_validacion import PagosValidacion
from .pagos_calculo import PagosCalculo

__all__ = ["PagosService", "PagosValidacion", "PagosCalculo"]
```

```python
# backend/app/services/pagos/pagos_validacion.py
from typing import Optional
from pydantic import ValidationError

class PagosValidacion:
    def __init__(self, db: Session):
        self.db = db
    
    def validar_cliente_existe(self, cliente_id: int) -> Optional[Cliente]:
        cliente = self.db.query(Cliente).filter(Cliente.id == cliente_id).first()
        if not cliente:
            raise ValueError(f"Cliente {cliente_id} no encontrado")
        return cliente
    
    def validar_cuenta_existe(self, cuenta_id: int) -> Optional[Cuenta]:
        cuenta = self.db.query(Cuenta).filter(Cuenta.id == cuenta_id).first()
        if not cuenta:
            raise ValueError(f"Cuenta {cuenta_id} no encontrada")
        return cuenta
    
    def validar_monto(self, monto: float) -> bool:
        if monto <= 0:
            raise ValueError("Monto debe ser mayor a 0")
        return True
    
    def validar_pago_completo(self, pago_data: PagoCreacionSchema) -> bool:
        self.validar_cliente_existe(pago_data.cliente_id)
        self.validar_cuenta_existe(pago_data.cuenta_id)
        self.validar_monto(pago_data.monto)
        return True
```

```python
# backend/app/services/pagos/pagos_calculo.py
class PagosCalculo:
    def __init__(self, db: Session):
        self.db = db
    
    def calcular_monto_en_dolares(self, monto_pesos: float) -> float:
        tasa = self.db.query(TasaCambio)\
            .order_by(TasaCambio.fecha.desc())\
            .first()
        
        if not tasa:
            return monto_pesos
        
        return monto_pesos / tasa.valor
    
    def calcular_interes(self, monto: float, dias_atraso: int, tasa_diaria: float) -> float:
        return monto * tasa_diaria * dias_atraso
```

```python
# backend/app/services/pagos/pagos_service.py
from app.core.database import get_db

class PagosService:
    def __init__(self, db: Session):
        self.db = db
        self.validacion = PagosValidacion(db)
        self.calculo = PagosCalculo(db)
    
    def crear_pago(self, pago_data: PagoCreacionSchema) -> Pago:
        # Validar
        self.validacion.validar_pago_completo(pago_data)
        
        # Calcular
        monto_dolares = self.calculo.calcular_monto_en_dolares(pago_data.monto)
        
        # Crear
        nuevo_pago = Pago(
            cliente_id=pago_data.cliente_id,
            cuenta_id=pago_data.cuenta_id,
            monto=pago_data.monto,
            monto_dolares=monto_dolares,
            estado="pendiente"
        )
        
        self.db.add(nuevo_pago)
        self.db.commit()
        self.db.refresh(nuevo_pago)
        
        return nuevo_pago
    
    def obtener_pago(self, pago_id: int) -> Pago:
        pago = self.db.query(Pago).filter(Pago.id == pago_id).first()
        if not pago:
            raise ValueError(f"Pago {pago_id} no encontrado")
        return pago
    
    def actualizar_estado_pago(self, pago_id: int, nuevo_estado: str) -> Pago:
        pago = self.obtener_pago(pago_id)
        pago.estado = nuevo_estado
        self.db.commit()
        self.db.refresh(pago)
        return pago
```

#### Paso 2: Refactorizar endpoints
```python
# backend/app/api/v1/endpoints/pagos.py - DESPUÉS (Delgado)

from fastapi import APIRouter, Depends
from app.core.database import get_db
from app.services.pagos import PagosService
from sqlalchemy.orm import Session

router = APIRouter(prefix="/pagos", tags=["pagos"])

@router.post("/")
def crear_pago(pago_data: PagoCreacionSchema, db: Session = Depends(get_db)):
    """Crear un nuevo pago"""
    try:
        service = PagosService(db)
        return service.crear_pago(pago_data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{pago_id}")
def obtener_pago(pago_id: int, db: Session = Depends(get_db)):
    """Obtener un pago por ID"""
    try:
        service = PagosService(db)
        return service.obtener_pago(pago_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.put("/{pago_id}/estado")
def actualizar_estado(pago_id: int, estado: str, db: Session = Depends(get_db)):
    """Actualizar estado del pago"""
    try:
        service = PagosService(db)
        return service.actualizar_estado_pago(pago_id, estado)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

# ... más endpoints cortos y limpios
```

#### Paso 3: Tests
```python
# tests/unit/services/pagos/test_pagos_service.py
import pytest
from app.services.pagos import PagosService, PagosValidacion, PagosCalculo

@pytest.fixture
def mock_db(mocker):
    return mocker.MagicMock()

def test_crear_pago(mock_db):
    service = PagosService(mock_db)
    pago_data = PagoCreacionSchema(
        cliente_id=1,
        cuenta_id=1,
        monto=1000.00
    )
    resultado = service.crear_pago(pago_data)
    assert resultado.monto == 1000.00

def test_validar_cliente_no_existe(mock_db):
    mock_db.query.return_value.filter.return_value.first.return_value = None
    validacion = PagosValidacion(mock_db)
    
    with pytest.raises(ValueError):
        validacion.validar_cliente_existe(999)

def test_calcular_monto_en_dolares(mock_db):
    tasa = TasaCambio(valor=50.0)
    mock_db.query.return_value.order_by.return_value.first.return_value = tasa
    
    calculo = PagosCalculo(mock_db)
    resultado = calculo.calcular_monto_en_dolares(1000.0)
    assert resultado == 20.0
```

---

## Ejemplo 2: Refactorización de `Comunicaciones.tsx`

### ANTES (Monolítico - 1437 líneas)
```typescript
// frontend/src/components/comunicaciones/Comunicaciones.tsx - ANTES (Simplificado)

export const Comunicaciones = () => {
  const [activeTab, setActiveTab] = useState<'email' | 'sms' | 'whatsapp'>('email');
  const [emails, setEmails] = useState([]);
  const [smsList, setSmsList] = useState([]);
  const [whatsappList, setWhatsappList] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  // Email handlers (200+ líneas)
  const handleSendEmail = async (to: string, subject: string, body: string) => {
    setLoading(true);
    try {
      const response = await fetch('/api/emails/send', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ to, subject, body })
      });
      const data = await response.json();
      setEmails([...emails, data]);
      setError(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };
  
  // SMS handlers (200+ líneas)
  const handleSendSMS = async (phone: string, message: string) => {
    setLoading(true);
    try {
      const response = await fetch('/api/sms/send', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ phone, message })
      });
      const data = await response.json();
      setSmsList([...smsList, data]);
      setError(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };
  
  // WhatsApp handlers (200+ líneas)
  const handleSendWhatsApp = async (phone: string, message: string) => {
    // ... similar pattern
  };
  
  // Rendering (600+ líneas)
  return (
    <div>
      <Tabs>
        <Tab label="Email">
          {/* Email form - 200+ líneas */}
          {/* Email list - 150+ líneas */}
        </Tab>
        <Tab label="SMS">
          {/* SMS form - 200+ líneas */}
          {/* SMS list - 150+ líneas */}
        </Tab>
        <Tab label="WhatsApp">
          {/* WhatsApp form - 200+ líneas */}
          {/* WhatsApp list - 150+ líneas */}
        </Tab>
      </Tabs>
    </div>
  );
};
```

### DESPUÉS (Refactorizado)

#### Paso 1: Hook de estado
```typescript
// frontend/src/components/comunicaciones/hooks/useComunicacionesState.ts
import { useState } from 'react';

export interface ComunicacionesState {
  activeTab: 'email' | 'sms' | 'whatsapp';
  loading: boolean;
  error: string | null;
  emails: Email[];
  smsList: SMS[];
  whatsappList: WhatsApp[];
}

export const useComunicacionesState = () => {
  const [state, setState] = useState<ComunicacionesState>({
    activeTab: 'email',
    loading: false,
    error: null,
    emails: [],
    smsList: [],
    whatsappList: [],
  });

  const setActiveTab = (tab: 'email' | 'sms' | 'whatsapp') => {
    setState(prev => ({ ...prev, activeTab: tab }));
  };

  const setLoading = (loading: boolean) => {
    setState(prev => ({ ...prev, loading }));
  };

  const setError = (error: string | null) => {
    setState(prev => ({ ...prev, error }));
  };

  const addEmail = (email: Email) => {
    setState(prev => ({ ...prev, emails: [...prev.emails, email] }));
  };

  const addSMS = (sms: SMS) => {
    setState(prev => ({ ...prev, smsList: [...prev.smsList, sms] }));
  };

  const addWhatsApp = (whatsapp: WhatsApp) => {
    setState(prev => ({ ...prev, whatsappList: [...prev.whatsappList, whatsapp] }));
  };

  return {
    state,
    setActiveTab,
    setLoading,
    setError,
    addEmail,
    addSMS,
    addWhatsApp,
  };
};
```

#### Paso 2: Componentes sección
```typescript
// frontend/src/components/comunicaciones/EmailSection.tsx (~350 líneas)
import { ComunicacionesState } from './hooks/useComunicacionesState';
import { EmailForm } from './forms/EmailForm';
import { EmailList } from './lists/EmailList';

interface EmailSectionProps {
  state: ComunicacionesState;
  onSend: (email: Email) => Promise<void>;
  loading: boolean;
}

export const EmailSection = ({ state, onSend, loading }: EmailSectionProps) => {
  return (
    <div className="email-section">
      <EmailForm onSend={onSend} loading={loading} />
      <EmailList emails={state.emails} />
    </div>
  );
};
```

```typescript
// frontend/src/components/comunicaciones/SMSSection.tsx (~350 líneas)
interface SMSSectionProps {
  state: ComunicacionesState;
  onSend: (sms: SMS) => Promise<void>;
  loading: boolean;
}

export const SMSSection = ({ state, onSend, loading }: SMSSectionProps) => {
  return (
    <div className="sms-section">
      <SMSForm onSend={onSend} loading={loading} />
      <SMSList smsList={state.smsList} />
    </div>
  );
};
```

```typescript
// frontend/src/components/comunicaciones/WhatsAppSection.tsx (~350 líneas)
interface WhatsAppSectionProps {
  state: ComunicacionesState;
  onSend: (whatsapp: WhatsApp) => Promise<void>;
  loading: boolean;
}

export const WhatsAppSection = ({ state, onSend, loading }: WhatsAppSectionProps) => {
  return (
    <div className="whatsapp-section">
      <WhatsAppForm onSend={onSend} loading={loading} />
      <WhatsAppList whatsappList={state.whatsappList} />
    </div>
  );
};
```

#### Paso 3: Componente contenedor refactorizado
```typescript
// frontend/src/components/comunicaciones/Comunicaciones.tsx - DESPUÉS (~300 líneas)
import { Tabs } from '@/components/ui/Tabs';
import { EmailSection } from './EmailSection';
import { SMSSection } from './SMSSection';
import { WhatsAppSection } from './WhatsAppSection';
import { useComunicacionesState } from './hooks/useComunicacionesState';
import { comunicacionesService } from '@/services/comunicacionesService';

export const Comunicaciones = () => {
  const { 
    state, 
    setActiveTab, 
    setLoading, 
    setError, 
    addEmail, 
    addSMS, 
    addWhatsApp 
  } = useComunicacionesState();

  const handleSendEmail = async (email: Email) => {
    setLoading(true);
    try {
      const result = await comunicacionesService.sendEmail(email);
      addEmail(result);
      setError(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleSendSMS = async (sms: SMS) => {
    setLoading(true);
    try {
      const result = await comunicacionesService.sendSMS(sms);
      addSMS(result);
      setError(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleSendWhatsApp = async (whatsapp: WhatsApp) => {
    setLoading(true);
    try {
      const result = await comunicacionesService.sendWhatsApp(whatsapp);
      addWhatsApp(result);
      setError(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="comunicaciones">
      {state.error && <Alert type="error" message={state.error} />}
      
      <Tabs value={state.activeTab} onChange={setActiveTab}>
        <Tab label="Email">
          <EmailSection 
            state={state} 
            onSend={handleSendEmail} 
            loading={state.loading}
          />
        </Tab>
        
        <Tab label="SMS">
          <SMSSection 
            state={state} 
            onSend={handleSendSMS} 
            loading={state.loading}
          />
        </Tab>
        
        <Tab label="WhatsApp">
          <WhatsAppSection 
            state={state} 
            onSend={handleSendWhatsApp} 
            loading={state.loading}
          />
        </Tab>
      </Tabs>
    </div>
  );
};
```

---

## Ejemplo 3: Refactorización de `useExcelUploadPagos.ts`

### ANTES (Monolítico - 1234 líneas)
```typescript
// Simplificado - el archivo real es mucho más grande
export const useExcelUploadPagos = () => {
  const [file, setFile] = useState<File | null>(null);
  const [data, setData] = useState([]);
  const [errors, setErrors] = useState([]);
  const [loading, setLoading] = useState(false);
  const [validating, setValidating] = useState(false);
  const [processing, setProcessing] = useState(false);
  const [progress, setProgress] = useState(0);
  
  const handleFileUpload = async (uploadedFile: File) => {
    setLoading(true);
    
    // Parse Excel (100+ líneas)
    const workbook = XLSX.read(await uploadedFile.arrayBuffer());
    const worksheet = workbook.Sheets[workbook.SheetNames[0]];
    const rawData = XLSX.utils.sheet_to_json(worksheet);
    
    // Validar datos (200+ líneas)
    const validatedErrors: string[] = [];
    const validatedData: any[] = [];
    
    rawData.forEach((row, index) => {
      if (!row.monto || parseFloat(row.monto) <= 0) {
        validatedErrors.push(`Fila ${index + 1}: Monto inválido`);
      }
      if (!row.cliente_id) {
        validatedErrors.push(`Fila ${index + 1}: Cliente ID requerido`);
      }
      // ... 100+ validaciones más
    });
    
    if (validatedErrors.length > 0) {
      setErrors(validatedErrors);
      setLoading(false);
      return;
    }
    
    // Procesar datos (300+ líneas)
    setValidating(true);
    const processedData = await Promise.all(
      validatedData.map(async (row, index) => {
        // Cálculos complejos
        const cliente = await fetchCliente(row.cliente_id);
        const cuenta = await fetchCuenta(row.cuenta_id);
        // ... más procesamiento
        return processedRow;
      })
    );
    
    setData(processedData);
    setProcessing(true);
    setLoading(false);
  };
  
  return { file, data, errors, loading, handleFileUpload };
};
```

### DESPUÉS (Refactorizado)

#### Paso 1: Servicios de Excel
```typescript
// frontend/src/services/excel/excelParsingService.ts
import * as XLSX from 'xlsx';

export class ExcelParsingService {
  static async parse(file: File): Promise<any[]> {
    try {
      const arrayBuffer = await file.arrayBuffer();
      const workbook = XLSX.read(arrayBuffer);
      const worksheet = workbook.Sheets[workbook.SheetNames[0]];
      return XLSX.utils.sheet_to_json(worksheet);
    } catch (error) {
      throw new Error(`Error parsing Excel: ${error.message}`);
    }
  }

  static validateHeaders(headers: string[], requiredHeaders: string[]): boolean {
    return requiredHeaders.every(header => headers.includes(header));
  }
}
```

```typescript
// frontend/src/services/excel/excelValidationService.ts
export interface ValidationError {
  row: number;
  field: string;
  message: string;
  value: any;
}

export class ExcelValidationService {
  static validateMonto(monto: string | number, rowIndex: number): ValidationError | null {
    const value = parseFloat(monto as string);
    if (isNaN(value) || value <= 0) {
      return {
        row: rowIndex + 1,
        field: 'monto',
        message: 'Monto debe ser un número mayor a 0',
        value: monto,
      };
    }
    return null;
  }

  static validateClienteId(clienteId: string | number, rowIndex: number): ValidationError | null {
    if (!clienteId) {
      return {
        row: rowIndex + 1,
        field: 'cliente_id',
        message: 'Cliente ID es requerido',
        value: clienteId,
      };
    }
    return null;
  }

  static validateRow(row: any, rowIndex: number): ValidationError[] {
    const errors: ValidationError[] = [];

    const montoError = this.validateMonto(row.monto, rowIndex);
    if (montoError) errors.push(montoError);

    const clienteError = this.validateClienteId(row.cliente_id, rowIndex);
    if (clienteError) errors.push(clienteError);

    // ... más validaciones

    return errors;
  }

  static validateData(data: any[]): ValidationError[] {
    const allErrors: ValidationError[] = [];
    
    data.forEach((row, index) => {
      const rowErrors = this.validateRow(row, index);
      allErrors.push(...rowErrors);
    });

    return allErrors;
  }
}
```

```typescript
// frontend/src/services/excel/excelProcessingService.ts
export class ExcelProcessingService {
  static async enrich(data: any[], clienteService: any, cuentaService: any) {
    return Promise.all(
      data.map(async (row) => {
        const cliente = await clienteService.get(row.cliente_id);
        const cuenta = await cuentaService.get(row.cuenta_id);

        return {
          ...row,
          clienteNombre: cliente?.nombre,
          cuentaNombre: cuenta?.nombre,
          timestamp: new Date().toISOString(),
        };
      })
    );
  }

  static calculateTotals(data: any[]): { totalMonto: number; totalRegistros: number } {
    const totalMonto = data.reduce((sum, row) => sum + parseFloat(row.monto), 0);
    return {
      totalMonto,
      totalRegistros: data.length,
    };
  }
}
```

#### Paso 2: Hooks especializados
```typescript
// frontend/src/hooks/useExcelUpload.ts (~200 líneas)
import { useState } from 'react';
import { ExcelParsingService } from '@/services/excel/excelParsingService';

export const useExcelUpload = () => {
  const [file, setFile] = useState<File | null>(null);
  const [rawData, setRawData] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);

  const handleFileSelect = async (selectedFile: File) => {
    setLoading(true);
    setFile(selectedFile);

    try {
      const data = await ExcelParsingService.parse(selectedFile);
      setRawData(data);
    } catch (error) {
      console.error('Error uploading file:', error);
    } finally {
      setLoading(false);
    }
  };

  return { file, rawData, loading, handleFileSelect };
};
```

```typescript
// frontend/src/hooks/useExcelValidation.ts (~200 líneas)
import { useState } from 'react';
import { ValidationError, ExcelValidationService } from '@/services/excel/excelValidationService';

export const useExcelValidation = (data: any[]) => {
  const [errors, setErrors] = useState<ValidationError[]>([]);
  const [isValid, setIsValid] = useState(false);

  const validate = async () => {
    const validationErrors = ExcelValidationService.validateData(data);
    setErrors(validationErrors);
    setIsValid(validationErrors.length === 0);
    return validationErrors.length === 0;
  };

  return { errors, isValid, validate };
};
```

```typescript
// frontend/src/hooks/useExcelProcessing.ts (~200 líneas)
import { useState } from 'react';
import { ExcelProcessingService } from '@/services/excel/excelProcessingService';
import { clienteService, cuentaService } from '@/services';

export const useExcelProcessing = (data: any[]) => {
  const [processedData, setProcessedData] = useState<any[]>([]);
  const [processing, setProcessing] = useState(false);

  const process = async () => {
    setProcessing(true);

    try {
      const enriched = await ExcelProcessingService.enrich(
        data,
        clienteService,
        cuentaService
      );
      setProcessedData(enriched);
      return enriched;
    } catch (error) {
      console.error('Error processing:', error);
    } finally {
      setProcessing(false);
    }
  };

  return { processedData, processing, process };
};
```

#### Paso 3: Componente usando hooks refactorizados
```typescript
// Uso en componente
import { useExcelUpload } from '@/hooks/useExcelUpload';
import { useExcelValidation } from '@/hooks/useExcelValidation';
import { useExcelProcessing } from '@/hooks/useExcelProcessing';

export const PagosUpload = () => {
  const { file, rawData, loading: uploading, handleFileSelect } = useExcelUpload();
  const { errors, isValid, validate } = useExcelValidation(rawData);
  const { processedData, processing, process } = useExcelProcessing(rawData);

  const handleUpload = async (file: File) => {
    await handleFileSelect(file);
    const valid = await validate();
    
    if (valid) {
      await process();
    }
  };

  return (
    <div>
      <FileInput onChange={handleUpload} />
      {errors.length > 0 && <ErrorList errors={errors} />}
      {processedData.length > 0 && <DataPreview data={processedData} />}
    </div>
  );
};
```

---

## Resumen de Beneficios

### Antes de Refactorizar
- ❌ Archivos monolíticos difíciles de entender
- ❌ Lógica mezclada (UI + validación + cálculos)
- ❌ Reutilización difícil
- ❌ Tests complejos e integrados
- ❌ Mantenimiento lento
- ❌ Bugs que afectan múltiples áreas

### Después de Refactorizar
- ✅ Archivos pequeños y enfocados
- ✅ Separación clara de responsabilidades
- ✅ Fácil reutilización de servicios
- ✅ Tests unitarios simples
- ✅ Mantenimiento rápido
- ✅ Bugs aislados y fáciles de corregir
- ✅ Mejor performance (lazy loading, tree-shaking)
- ✅ Código más legible y onboarding más rápido

