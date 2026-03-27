# -*- coding: utf-8 -*-
from pathlib import Path

p = Path(__file__).resolve().parents[1] / "frontend" / "src" / "pages" / "Notificaciones.tsx"
text = p.read_text(encoding="utf-8")

old1 = """  const handleRefresh = async () => {
    setActualizandoListas(true)
    try {
      await notificacionService.actualizarNotificaciones()
      await queryClient.invalidateQueries({
        queryKey: ['notificaciones-estadisticas-por-tab'],
      })
      await refetch()
      toast.success(
        'Listas y mora actualizadas. El servidor tambien recalcula automaticamente a las 00:50 (America/Caracas), antes del envio programado 01:00.'
      )
    } catch (e) {
      console.error(e)
      toast.error(
        'No se pudo recalcular la mora en el servidor. Puede reintentar o revisar conexion y permisos.'
      )
    } finally {
      setActualizandoListas(false)
    }
  }"""

new1 = """  const handleRefresh = async () => {
    setActualizandoListas(true)
    try {
      await notificacionService.actualizarNotificaciones()
      await invalidateListasNotificacionesMora(queryClient, {
        skipCrossTabBroadcast: true,
      })
      await queryClient.invalidateQueries({
        queryKey: ['notificaciones-masivos-lista'],
      })
      await Promise.all([
        queryClient.refetchQueries({
          queryKey: NOTIFICACIONES_CLIENTES_RETRASADOS_QUERY_KEY,
        }),
        queryClient.refetchQueries({
          queryKey: NOTIFICACIONES_ESTADISTICAS_POR_TAB_QUERY_KEY,
        }),
        queryClient.refetchQueries({
          queryKey: ['notificaciones-masivos-lista'],
        }),
      ])
      toast.success(
        'Listas y KPI actualizados manualmente. El servidor tambien ejecuta un job a las 00:50 (America/Caracas).'
      )
    } catch (e) {
      console.error(e)
      toast.error(
        'No se pudo recalcular la mora en el servidor. Puede reintentar o revisar conexion y permisos.'
      )
    } finally {
      setActualizandoListas(false)
    }
  }"""

old2 = """  if (activeTab === 'configuracion') {
    return (
      <div className="space-y-6">
        <ModulePageHeader
          icon={Bell}
          title="Notificaciones"
          description="Clientes retrasados por fecha de vencimiento y mora"
        />"""

new2 = """  if (activeTab === 'configuracion') {
    return (
      <div className="space-y-6">
        <ModulePageHeader
          icon={Bell}
          title="Notificaciones"
          description="Clientes retrasados por fecha de vencimiento y mora"
          actions={
            <Button
              variant="outline"
              onClick={() => void handleRefresh()}
              disabled={actualizandoListas}
            >
              <RefreshCw
                className={`mr-2 h-4 w-4 ${actualizandoListas ? 'animate-spin' : ''}`}
              />
              Actualizacion manual
            </Button>
          }
        />"""

old3 = """          actions={
            <Button
              variant="outline"
              onClick={() => void handleRefresh()}
              disabled={isFetching || actualizandoListas}
            >
              <RefreshCw
                className={`mr-2 h-4 w-4 ${isFetching || actualizandoListas ? 'animate-spin' : ''}`}
              />
              Actualizar
            </Button>
          }"""

new3 = """          actions={
            <Button
              variant="outline"
              onClick={() => void handleRefresh()}
              disabled={actualizandoListas}
            >
              <RefreshCw
                className={`mr-2 h-4 w-4 ${actualizandoListas ? 'animate-spin' : ''}`}
              />
              Actualizacion manual
            </Button>
          }"""

old4 = """          <CardContent>
            {/* KPIs por pestaAa: correos enviados y rebotados */}"""

# Try common encodings for comment corruption
old4_alt = """          <CardContent>
            {/* KPIs por pestaña: correos enviados y rebotados */}"""

new4 = """          <CardContent>
            <div className="mb-4 flex flex-wrap items-center gap-3 rounded-lg border border-slate-200 bg-slate-50/80 px-3 py-2">
              <Button
                variant="secondary"
                size="sm"
                onClick={() => void handleRefresh()}
                disabled={actualizandoListas}
              >
                <RefreshCw
                  className={`mr-2 h-4 w-4 ${actualizandoListas ? 'animate-spin' : ''}`}
                />
                Actualizacion manual
              </Button>
              <p className="max-w-xl text-xs text-gray-600">
                Vuelve a pedir al servidor las listas de mora, los KPI y masivos (POST{' '}
                <code className="rounded bg-white px-1">/notificaciones/actualizar</code> y
                refetch de datos).
              </p>
            </div>

            {/* KPIs por pestaña: correos enviados y rebotados */}"""

for name, o, n in [
    ("handleRefresh", old1, new1),
    ("config header", old2, new2),
    ("main header", old3, new3),
]:
    if o not in text:
        raise SystemExit(f"block not found: {name}")
    text = text.replace(o, n, 1)

if old4 in text:
    text = text.replace(old4, new4, 1)
elif old4_alt in text:
    text = text.replace(old4_alt, new4, 1)
else:
    # find CardContent after CardDescription block
    needle = "          <CardContent>\n"
    idx = text.find(needle)
    if idx == -1:
        raise SystemExit("CardContent not found")
    # insert only once: after first CardContent that precedes KPIs comment
    marker = "            {/* KPIs"
    pos = text.find(marker, idx)
    if pos == -1:
        raise SystemExit("KPIs comment not found")
    insert = """          <CardContent>
            <div className="mb-4 flex flex-wrap items-center gap-3 rounded-lg border border-slate-200 bg-slate-50/80 px-3 py-2">
              <Button
                variant="secondary"
                size="sm"
                onClick={() => void handleRefresh()}
                disabled={actualizandoListas}
              >
                <RefreshCw
                  className={`mr-2 h-4 w-4 ${actualizandoListas ? 'animate-spin' : ''}`}
                />
                Actualizacion manual
              </Button>
              <p className="max-w-xl text-xs text-gray-600">
                Vuelve a pedir al servidor las listas de mora, los KPI y masivos (POST{' '}
                <code className="rounded bg-white px-1">/notificaciones/actualizar</code> y
                refetch de datos).
              </p>
            </div>

"""
    text = text[: idx + len(needle)] + insert + text[idx + len(needle) :]

p.write_text(text, encoding="utf-8")
print("patched", p)
