import { useState } from 'react'

import { RefreshCw } from 'lucide-react'

import { Button } from '../../ui/button'

import { ValidadoresConfig } from '../ValidadoresConfig'

import { ConfigTabManualStrip } from '../ConfigTabManualStrip'

export function ConfigValidadoresTab() {
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
      <ValidadoresConfig key={reloadKey} />
    </>
  )
}
