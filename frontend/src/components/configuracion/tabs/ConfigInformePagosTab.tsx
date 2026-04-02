import { useState } from 'react'

import { RefreshCw } from 'lucide-react'

import { Button } from '../../ui/button'

import { InformePagosConfig } from '../InformePagosConfig'

import { ConfigTabManualStrip } from '../ConfigTabManualStrip'

export function ConfigInformePagosTab() {
  const [reloadKey, setReloadKey] = useState(0)

  return (
    <>
      <ConfigTabManualStrip>
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={() => setReloadKey(k => k + 1)}
        >
          <RefreshCw className="mr-2 h-4 w-4" />
          Recargar esta pestaña
        </Button>
      </ConfigTabManualStrip>
      <InformePagosConfig key={reloadKey} />
    </>
  )
}
