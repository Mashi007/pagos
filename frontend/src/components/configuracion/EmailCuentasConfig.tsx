/**




 * ConfiguraciÃ³n de 4 cuentas de correo con asignaciÃ³n por servicio.




 * Cuenta 1 = Cobros, 2 = Estado de cuenta, 3 y 4 = Notificaciones (por pestaÃ±a).




 */




import { useState, useEffect } from 'react'




import { Mail, Save, AlertCircle, CheckCircle } from 'lucide-react'




import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../ui/card'




import { Button } from '../ui/button'




import { Input } from '../ui/input'




import { Label } from '../ui/label'




import { toast } from 'sonner'




import {




  emailCuentasApi,




  SERVICIO_POR_CUENTA,




  NOTIF_TABS,




  type EmailCuentasResponse,




  type CuentaEmailItem,




} from '../../services/emailCuentasApi'









const CUENTAS_COUNT = 4









const emptyCuenta = (): CuentaEmailItem => ({




  smtp_host: 'smtp.gmail.com',




  smtp_port: '587',




  smtp_user: '',




  smtp_password: '',




  from_email: '',




  from_name: 'RapiCredit',




  smtp_use_tls: 'true',




  imap_host: '',




  imap_port: '993',




  imap_user: '',




  imap_password: '',




  imap_use_ssl: 'true',




})









export function EmailCuentasConfig() {




  const [data, setData] = useState<EmailCuentasResponse | null>(null)




  const [loading, setLoading] = useState(true)




  const [saving, setSaving] = useState(false)



  const [sendingTest, setSendingTest] = useState(false)




  const [asignacion, setAsignacion] = useState<Record<string, number>>({})









  useEffect(() => {




    load()




  }, [])









  const load = async () => {




    setLoading(true)




    try {




      const res = await emailCuentasApi.get()




      setData(res)




      const tab = res.asignacion?.notificaciones_tab?? {}




      setAsignacion({ ...tab })




    } catch (e) {




      console.error(e)




      toast.error('Error cargando configuraciÃ³n de cuentas')




      setData({




        version: 2,




        cuentas: Array.from({ length: CUENTAS_COUNT }, emptyCuenta),




        asignacion: { cobros: 1, estado_cuenta: 2, notificaciones_tab: {} },




      })




      setAsignacion({})




    } finally {




      setLoading(false)




    }




  }









  const updateCuenta = (index: number, field: keyof CuentaEmailItem, value: string) => {




    if (!data) return




    const next = [...data.cuentas]




    if (!next[index]) next[index] = emptyCuenta()




    next[index] = { ...next[index], [field]: value }




    if (field === 'smtp_user' && !next[index].from_email?.trim()) next[index].from_email = value




    setData({ ...data, cuentas: next })




  }









  const setNotifTabCuenta = (tabId: string, cuenta: number) => {



    setAsignacion(prev => ({ ...prev, [tabId]: cuenta }))



  }







  const setServicioActivo = (key: keyof EmailCuentasResponse, value: string) => {



    if (!data) return



    setData({ ...data, [key]: value })



  }







  const SERVICIOS_DISPONIBLES: { key: keyof EmailCuentasResponse; label: string; cuenta: number }[] = [



    { key: 'email_activo_cobros', label: 'Cobros (formulario pÃºblico, recibos)', cuenta: 1 },



    { key: 'email_activo_estado_cuenta', label: 'Estado de cuenta (cÃ³digo y envÃ­o PDF)', cuenta: 2 },



    { key: 'email_activo_notificaciones', label: 'Notificaciones (plantillas a clientes)', cuenta: 3 },



  ]









  const handleSave = async () => {




    if (!data) return




    setSaving(true)




    try {




      const cuentas = data.cuentas.slice(0, CUENTAS_COUNT)




      while (cuentas.length < CUENTAS_COUNT) cuentas.push(emptyCuenta())




      await emailCuentasApi.put({




        cuentas,




        asignacion: {




          cobros: data.asignacion?.cobros?? 1,




          estado_cuenta: data.asignacion?.estado_cuenta?? 2,




          notificaciones_tab: asignacion,




        },




        modo_pruebas: data.modo_pruebas,




        email_pruebas: data.email_pruebas,




        email_activo: data.email_activo,




        email_activo_notificaciones: data.email_activo_notificaciones,




        email_activo_estado_cuenta: data.email_activo_estado_cuenta,




        email_activo_cobros: data.email_activo_cobros,




        tickets_notify_emails: data.tickets_notify_emails,




      })




      toast.success('ConfiguraciÃ³n de 4 cuentas guardada')




      await load()




    } catch (e: unknown) {




      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail?? (e as Error)?.message?? 'Error al guardar'




      toast.error(String(msg))




    } finally {




      setSaving(false)




    }




  }



  const handleEnviarPrueba = async () => {



    setSendingTest(true)



    try {



      const res = await emailCuentasApi.enviarPrueba()



      if (res.success) {



        const cuentasOk = [...new Set((res.enviados || []).map(e => e.cuenta))].sort((a, b) => a - b)



        toast.success(cuentasOk.length ? `Pruebas OK: Cuentas ${cuentasOk.join(', ')}. ${res.mensaje}` : res.mensaje)



      } else {



        const errMsg = res.errores?.length ? res.errores.map(e => `Cuenta ${e.cuenta}: ${e.mensaje}`).join('; ') : res.mensaje



        toast.warning(errMsg || res.mensaje)



      }



    } catch (e: unknown) {



      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail?? (e as Error)?.message?? 'Error al enviar prueba'



      toast.error(String(msg))



    } finally {



      setSendingTest(false)



    }



  }



if (loading) {




    return (




      <Card>




        <CardContent className="pt-6">Cargando configuraciÃ³n de cuentas...</CardContent>




      </Card>




    )




  }









  const cuentas = data?.cuentas?? Array.from({ length: CUENTAS_COUNT }, emptyCuenta)









  return (




    <div className="space-y-6">




      <Card>



        <CardHeader>



          <CardTitle className="text-base flex items-center gap-2">



            <CheckCircle className="h-4 w-4" />



            Servicios disponibles



          </CardTitle>



          <CardDescription>



            Active o desactive el envÃ­o de correo por servicio. Cada uno usa la cuenta indicada (Cuenta 1, 2 o 3/4).



          </CardDescription>



        </CardHeader>



        <CardContent>



          <div className="grid gap-3 sm:grid-cols-2">



            {SERVICIOS_DISPONIBLES.map(({ key, label, cuenta }) => (



              <div key={key} className="flex items-center justify-between rounded border p-3">



                <div>



                  <p className="text-sm font-medium">{label}</p>



                  <p className="text-xs text-muted-foreground">Cuenta {cuenta}</p>



                </div>



                <label className="relative inline-flex items-center cursor-pointer">



                  <input



                    type="checkbox"



                    checked={(data?.[key] ? 'true') === 'true'}



                    onChange={e => setServicioActivo(key, e.target.checked ? 'true' : 'false')}



                    className="sr-only peer"



                  />



                  <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none rounded-full peer dark:bg-gray-700 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all dark:border-gray-600 peer-checked:bg-blue-600" />



                  <span className="ml-2 text-sm">{(data?.[key] ? 'true') === 'true' ? 'Activo' : 'Inactivo'}</span>



                </label>



              </div>



            ))}



          </div>



        </CardContent>



      </Card>







      








      <Card className="border-amber-200 bg-amber-50/50 dark:bg-amber-950/20">



        <CardHeader>



          <CardTitle className="text-base flex items-center gap-2">Modo pruebas y correo de pruebas</CardTitle>



          <CardDescription>



            Si "Modo pruebas" está activo, todos los envíos se redirigen al correo indicado. El correo de pruebas es obligatorio cuando el modo pruebas está activado.



          </CardDescription>



        </CardHeader>



        <CardContent className="space-y-4">



          <div className="flex items-center justify-between rounded border p-3">



            <span className="text-sm font-medium">Modo pruebas (redirigir envíos al correo de pruebas)</span>



            <label className="relative inline-flex items-center cursor-pointer">



              <input



                type="checkbox"



                checked={(data?.modo_pruebas?? 'true') === 'true'}



                onChange={e => setData(data ? { ...data, modo_pruebas: e.target.checked ? 'true' : 'false' } : data)}



                className="sr-only peer"



              />



              <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none rounded-full peer dark:bg-gray-700 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all dark:border-gray-600 peer-checked:bg-amber-600" />



              <span className="ml-2 text-sm">{(data?.modo_pruebas ? 'true') === 'true' ? 'Activo' : 'Inactivo'}</span>



            </label>



          </div>



          <div>



            <Label>Correo de pruebas (obligatorio si modo pruebas está activo)</Label>



            <Input



              type="email"



              value={data?.email_pruebas?? ''}



              onChange={e => setData(data ? { ...data, email_pruebas: e.target.value } : data)}



              placeholder="ejemplo@correo.com"



              className="mt-1"



            />



          </div>        <div className="flex justify-end pt-2">



          <Button type="button" variant="outline" onClick={handleEnviarPrueba} disabled={sendingTest || !(data?.email_pruebas?? '').trim()}>



            <Mail className="mr-2 h-4 w-4" />



            {sendingTest ? 'Enviando...' : 'Enviar prueba a todos los correos registrados'}



          </Button>



        </div>



</CardContent>



      </Card>







            <Card className="border-blue-200 bg-blue-50/50 dark:bg-blue-950/20">




        <CardHeader>




          <CardTitle className="flex items-center gap-2 text-lg">




            <Mail className="h-5 w-5" />




            Cuentas de correo por servicio




          </CardTitle>




          <CardDescription>




            Configure hasta 4 cuentas. Cada servicio usa una cuenta: <strong>Cuenta 1</strong> = Cobros (formulario pÃºblico),




            <strong> Cuenta 2</strong> = Estado de cuenta, <strong>Cuentas 3 y 4</strong> = Notificaciones (puede elegir por pestaÃ±a).




          </CardDescription>




        </CardHeader>




      </Card>









      {[0, 1, 2, 3].map(i => (




        <Card key={i}>




          <CardHeader className="pb-2">




            <CardTitle className="text-base">




              Cuenta {i + 1} â {SERVICIO_POR_CUENTA[i + 1] ? `Cuenta ${i + 1}`}




            </CardTitle>




            <CardDescription>




              {i === 0 && 'Usada en: rapicredit-cobros (reporte de pago).'}




              {i === 1 && 'Usada en: rapicredit-estadocuenta (consulta y envÃ­o de PDF).'}




              {(i === 2 || i === 3) && `Usada en: Notificaciones (pestaÃ±as que elija como "Cuenta ${i + 1}" abajo).`}




            </CardDescription>




          </CardHeader>




          <CardContent className="space-y-4">




            <div className="grid gap-2 sm:grid-cols-2">




              <div>




                <Label>Servidor SMTP</Label>




                <Input




                  value={cuentas[i]?.smtp_host?? ''}




                  onChange={e => updateCuenta(i, 'smtp_host', e.target.value)}




                  placeholder="smtp.gmail.com"




                />




              </div>




              <div>




                <Label>Puerto SMTP</Label>




                <Input




                  type="text"




                  value={cuentas[i]?.smtp_port?? '587'}




                  onChange={e => updateCuenta(i, 'smtp_port', e.target.value)}




                  placeholder="587"




                />




              </div>




              <div>




                <Label>Usuario / Email</Label>




                <Input




                  type="email"




                  value={cuentas[i]?.smtp_user?? ''}




                  onChange={e => updateCuenta(i, 'smtp_user', e.target.value)}




                  placeholder="correo@ejemplo.com"




                />




              </div>




              <div>




                <Label>ContraseÃ±a</Label>




                <Input




                  type="password"




                  value={cuentas[i]?.smtp_password && (cuentas[i].smtp_password as string) !== '***' ? (cuentas[i].smtp_password as string) : ''}




                  onChange={e => updateCuenta(i, 'smtp_password', e.target.value)}




                  placeholder="***"




                  autoComplete="off"




                />




              </div>




              <div>




                <Label>Remitente (From)</Label>




                <Input




                  type="email"




                  value={cuentas[i]?.from_email?? ''}




                  onChange={e => updateCuenta(i, 'from_email', e.target.value)}




                  placeholder="correo@ejemplo.com"




                />




              </div>




              <div>




                <Label>Nombre remitente</Label>




                <Input




                  value={cuentas[i]?.from_name?? 'RapiCredit'}




                  onChange={e => updateCuenta(i, 'from_name', e.target.value)}




                />




              </div>




            </div>




          </CardContent>




        </Card>




      ))}









      <Card>




        <CardHeader>




          <CardTitle className="text-base flex items-center gap-2">




            <AlertCircle className="h-4 w-4" />




            AsignaciÃ³n Notificaciones: quÃ© cuenta usa cada pestaÃ±a




          </CardTitle>




          <CardDescription>




            Elija para cada pestaÃ±a de Notificaciones si usa <strong>Cuenta 3</strong> o <strong>Cuenta 4</strong>.




          </CardDescription>




        </CardHeader>




        <CardContent>




          <div className="grid gap-3 sm:grid-cols-2">




            {NOTIF_TABS.map(({ id, label }) => (




              <div key={id} className="flex items-center justify-between rounded border p-3">




                <span className="text-sm font-medium">{label}</span>




                <select




                  className="rounded border bg-background px-2 py-1 text-sm"




                  value={asignacion[id] ? 3}




                  onChange={e => setNotifTabCuenta(id, Number(e.target.value))}




                >




                  <option value={3}>Cuenta 3</option>




                  <option value={4}>Cuenta 4</option>




                </select>




              </div>




            ))}




          </div>




        </CardContent>




      </Card>









      <div className="flex justify-end">




        <Button onClick={handleSave} disabled={saving}>




          <Save className="mr-2 h-4 w-4" />




          {saving ? 'Guardandoâ¦' : 'Guardar configuraciÃ³n de 4 cuentas'}




        </Button>




      </div>




    </div>




  )




}




