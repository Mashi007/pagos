/**
 * Ciclo finiquito (30 dias calendario Caracas): bandeja 5 + revision 5 + contable 1 + trabajo 20.
 * Columna Ciclo = fase (N de M). Columna Conteo global = dia del ciclo (N de 30).
 */

export type FiniquitoTiempoCaso = {
  estado: string
  creado_en?: string | null
  fecha_liquidado?: string | null
  fecha_entrada_aceptado?: string | null
  fecha_entrada_revision_contable?: string | null
  fecha_entrada_en_proceso?: string | null
}

export const FINIQUITO_CICLO_DIAS = 30
export const FINIQUITO_FASE_BANDEJA_MAX = 5
export const FINIQUITO_FASE_REVISION_MAX = 5
export const FINIQUITO_FASE_CONTABLE_MAX = 1
export const FINIQUITO_FASE_TRABAJO_MAX = 20

/** Fin de cupo acumulado por fase (dia global inclusive). */
export const FINIQUITO_CUPO_FIN_BANDEJA = FINIQUITO_FASE_BANDEJA_MAX
export const FINIQUITO_CUPO_FIN_REVISION =
  FINIQUITO_FASE_BANDEJA_MAX + FINIQUITO_FASE_REVISION_MAX
export const FINIQUITO_CUPO_FIN_CONTABLE =
  FINIQUITO_CUPO_FIN_REVISION + FINIQUITO_FASE_CONTABLE_MAX
/** Primer dia global ideal en area de trabajo si todas las fases fueron a tiempo. */
export const FINIQUITO_IDEAL_INICIO_TRABAJO = FINIQUITO_CUPO_FIN_CONTABLE + 1

export type SemaforoTiempoFiniquito =
  | 'inicio'
  | 'avance'
  | 'termino'
  | 'atrasado'
  | 'recontraatrasado'

export type FiniquitoTiempoFila = {
  /** Dia global del ciclo (1 = creado_en). */
  diaGlobal: number | null
  /** Texto columna global: "N de 30". */
  textoGlobal: string
  /** Texto fase actual: "N de M". */
  textoFase: string
  diaFase: number | null
  maxFase: number | null
  atrasado: boolean
  /** Semaforo segun fase actual (columna Ciclo). */
  semaforo: SemaforoTiempoFiniquito
  /** Semaforo segun dia global (columna Conteo global). */
  semaforoGlobal: SemaforoTiempoFiniquito
}

const TZ_CARACAS = 'America/Caracas'

function ymdCaracas(fecha: Date = new Date()): string {
  return new Intl.DateTimeFormat('en-CA', {
    timeZone: TZ_CARACAS,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).format(fecha)
}

function utcMsDesdeYmd(ymd: string): number | null {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(ymd.trim().slice(0, 10))
  if (!m) return null
  return Date.UTC(Number(m[1]), Number(m[2]) - 1, Number(m[3]))
}

/** Dias calendario entre ancla (inclusive como dia 1) y hoy Caracas. */
export function diasDesdeAnclaCaracas(
  iso: string | null | undefined
): number | null {
  if (iso == null || String(iso).trim() === '') return null
  const desde = utcMsDesdeYmd(String(iso))
  const hasta = utcMsDesdeYmd(ymdCaracas())
  if (desde == null || hasta == null) return null
  return Math.floor((hasta - desde) / 86_400_000)
}

export function diaGlobalCiclo(caso: FiniquitoTiempoCaso): number | null {
  const anchor = caso.creado_en ?? caso.fecha_liquidado ?? null
  const dias = diasDesdeAnclaCaracas(anchor)
  if (dias == null) return null
  return dias + 1
}

/** Mas antiguo primero (mayor dia global arriba). Sin fecha al final. */
export function ordenarCasosPorConteoGlobalAntiguoPrimero<
  T extends FiniquitoTiempoCaso,
>(items: T[]): T[] {
  return [...items].sort((a, b) => {
    const da = diaGlobalCiclo(a)
    const db = diaGlobalCiclo(b)
    if (da == null && db == null) return 0
    if (da == null) return 1
    if (db == null) return -1
    return db - da
  })
}

function diaGlobalDesdeEntrada(iso: string | null | undefined): number | null {
  const anchor = iso
  if (anchor == null) return null
  const dias = diasDesdeAnclaCaracas(anchor)
  if (dias == null) return null
  return dias + 1
}

function formatoNdM(dia: number, max: number): string {
  return `${dia} de ${max}`
}

function formatoGlobal(dia: number): string {
  return `${dia} de ${FINIQUITO_CICLO_DIAS}`
}

function semaforoDesdeFase(
  diaFase: number,
  maxFase: number
): SemaforoTiempoFiniquito {
  if (diaFase > maxFase + 1) return 'recontraatrasado'
  if (diaFase > maxFase) return 'atrasado'
  if (diaFase === maxFase) return 'termino'
  const umbralInicio = Math.max(1, Math.ceil(maxFase * 0.25))
  if (diaFase <= umbralInicio) return 'inicio'
  return 'avance'
}

function semaforoDesdeGlobal(diaGlobal: number): SemaforoTiempoFiniquito {
  if (diaGlobal > FINIQUITO_CICLO_DIAS + 1) return 'recontraatrasado'
  if (diaGlobal > FINIQUITO_CICLO_DIAS) return 'atrasado'
  if (diaGlobal === FINIQUITO_CICLO_DIAS) return 'termino'
  const umbralInicio = Math.max(1, Math.ceil(FINIQUITO_CICLO_DIAS * 0.25))
  if (diaGlobal <= umbralInicio) return 'inicio'
  if (diaGlobal >= FINIQUITO_CICLO_DIAS - 4) return 'termino'
  return 'avance'
}

export function claseSemaforoTiempoFiniquito(
  s: SemaforoTiempoFiniquito
): string {
  switch (s) {
    case 'inicio':
      return 'bg-emerald-100 text-emerald-950'
    case 'avance':
      return 'bg-sky-100 text-sky-950'
    case 'termino':
      return 'bg-amber-100 text-amber-950'
    case 'atrasado':
      return 'bg-orange-100 text-orange-950'
    case 'recontraatrasado':
      return 'bg-red-200 text-red-950 ring-1 ring-red-400/60'
    default:
      return 'bg-slate-100 text-slate-800'
  }
}

function maxTrabajoEfectivo(entryGlobalDay: number): number {
  const retraso = Math.max(0, entryGlobalDay - FINIQUITO_IDEAL_INICIO_TRABAJO)
  return Math.max(0, FINIQUITO_FASE_TRABAJO_MAX - retraso)
}

function calcularFaseBandeja(globalDay: number) {
  return {
    diaFase: globalDay,
    maxFase: FINIQUITO_FASE_BANDEJA_MAX,
    textoFase: formatoNdM(globalDay, FINIQUITO_FASE_BANDEJA_MAX),
  }
}

function calcularFaseRevision(caso: FiniquitoTiempoCaso, globalDay: number) {
  const transferDay = diaGlobalDesdeEntrada(caso.fecha_entrada_aceptado)
  if (transferDay == null) {
    return {
      diaFase: null,
      maxFase: FINIQUITO_FASE_REVISION_MAX,
      textoFase: '-',
    }
  }
  const diaFase = globalDay - Math.min(transferDay, FINIQUITO_CUPO_FIN_BANDEJA)
  return {
    diaFase,
    maxFase: FINIQUITO_FASE_REVISION_MAX,
    textoFase: formatoNdM(diaFase, FINIQUITO_FASE_REVISION_MAX),
  }
}

function calcularFaseContable(caso: FiniquitoTiempoCaso, globalDay: number) {
  const transferDay = diaGlobalDesdeEntrada(
    caso.fecha_entrada_revision_contable
  )
  if (transferDay == null) {
    return {
      diaFase: null,
      maxFase: FINIQUITO_FASE_CONTABLE_MAX,
      textoFase: '-',
    }
  }
  const diaFase = globalDay - Math.min(transferDay, FINIQUITO_CUPO_FIN_REVISION)
  return {
    diaFase,
    maxFase: FINIQUITO_FASE_CONTABLE_MAX,
    textoFase: formatoNdM(diaFase, FINIQUITO_FASE_CONTABLE_MAX),
  }
}

function calcularFaseTrabajo(caso: FiniquitoTiempoCaso, globalDay: number) {
  const entryDay = diaGlobalDesdeEntrada(caso.fecha_entrada_en_proceso)
  if (entryDay == null) {
    return {
      diaFase: null,
      maxFase: FINIQUITO_FASE_TRABAJO_MAX,
      textoFase: '-',
    }
  }
  const maxEfectivo = maxTrabajoEfectivo(entryDay)
  const diaFase = globalDay - entryDay + 1
  return {
    diaFase,
    maxFase: maxEfectivo,
    textoFase: formatoNdM(diaFase, maxEfectivo),
  }
}

export function calcularTiempoFiniquito(
  caso: FiniquitoTiempoCaso
): FiniquitoTiempoFila {
  const estado = (caso.estado || '').toUpperCase().trim()
  const diaGlobal = diaGlobalCiclo(caso)

  if (diaGlobal == null) {
    return {
      diaGlobal: null,
      textoGlobal: '-',
      textoFase: '-',
      diaFase: null,
      maxFase: null,
      atrasado: false,
      semaforo: 'inicio',
      semaforoGlobal: 'inicio',
    }
  }

  const textoGlobal = formatoGlobal(diaGlobal)
  const semaforoGlobal = semaforoDesdeGlobal(diaGlobal)

  let fase: { diaFase: number | null; maxFase: number; textoFase: string }

  switch (estado) {
    case 'REVISION':
      fase = calcularFaseBandeja(diaGlobal)
      break
    case 'ACEPTADO':
      fase = calcularFaseRevision(caso, diaGlobal)
      break
    case 'REVISION_CONTABLE':
      fase = calcularFaseContable(caso, diaGlobal)
      break
    case 'EN_PROCESO':
      fase = calcularFaseTrabajo(caso, diaGlobal)
      break
    default:
      return {
        diaGlobal,
        textoGlobal,
        textoFase: '-',
        diaFase: null,
        maxFase: null,
        atrasado: false,
        semaforo: 'inicio',
        semaforoGlobal,
      }
  }

  const diaFase = fase.diaFase
  const maxFase = fase.maxFase
  const atrasado =
    diaFase != null &&
    maxFase != null &&
    (diaFase > maxFase || diaGlobal > FINIQUITO_CICLO_DIAS)

  const semaforo =
    diaFase != null && maxFase != null
      ? semaforoDesdeFase(diaFase, maxFase)
      : semaforoGlobal

  return {
    diaGlobal,
    textoGlobal,
    textoFase: fase.textoFase,
    diaFase,
    maxFase,
    atrasado,
    semaforo,
    semaforoGlobal,
  }
}

export function casoFiniquitoAtrasado(caso: FiniquitoTiempoCaso): boolean {
  const t = calcularTiempoFiniquito(caso)
  return t.atrasado
}
