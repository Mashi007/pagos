import { useState } from 'react'

import { RefreshCw } from 'lucide-react'

import { Button } from '../../ui/button'

import { ConcesionariosConfig } from '../ConcesionariosConfig'

import { ConfigTabManualStrip } from '../ConfigTabManualStrip'

export function ConfigConcesionariosTab() {
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
      <ConcesionariosConfig key={reloadKey} />
    </>
  )
}
