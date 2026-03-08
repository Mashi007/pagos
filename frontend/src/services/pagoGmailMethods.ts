  /** Pagos Gmail: ejecutar pipeline (Gmail -> Drive -> Gemini -> Sheets). */
  async runGmailNow(): Promise<{ sync_id: number | null; status: string }> {
    return await apiClient.post(`${this.baseUrl}/gmail/run-now`)
  }

  /** Pagos Gmail: estado última ejecución y próxima (cron cada 15 min). */
  async getGmailStatus(): Promise<{
    last_run: string | null
    last_status: string | null
    last_emails: number
    last_files: number
    next_run_approx: string | null
  }> {
    return await apiClient.get(`${this.baseUrl}/gmail/status`)
  }

  /** Pagos Gmail: descargar Excel del día (datos del Sheet). */
  async downloadGmailExcel(): Promise<void> {
    const axiosInstance = apiClient.getAxiosInstance()
    const response = await axiosInstance.get(`${this.baseUrl}/gmail/download-excel`, {
      responseType: 'blob',
      timeout: 60000,
    })
    const blob = response.data as Blob
    const disposition = response.headers?.['content-disposition']
    let filename = 'Pagos_Gmail.xlsx'
    if (typeof disposition === 'string' && disposition.includes('filename=')) {
      const m = disposition.match(/filename=(.+?)(?:;|$)/)
      if (m) filename = m[1].replace(/^["']|["']$/g, '').trim()
    }
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = filename
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)
  }
