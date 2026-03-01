const fs = require('fs');

const filePath = 'Reportes.tsx';
let content = fs.readFileSync(filePath, 'utf8');

// 1. Remove the useQuery hook for resumenData
content = content.replace(
  /  \/\/ Obtener resumen del dashboard para KPIs.*?refetchInterval: puedeVerReportes \? 5 \* 60 \* 1000 : false,.*?\}\)\s*/s,
  ''
);

// 2. Remove the useQuery check return block for KPIs error
content = content.replace(
  /  \/\/ Bloque mostrado si canViewReports.*?if \(!puedeVerReportes\) \{[\s\S]*?return \([\s\S]*?<\/motion\.div>\s*\)\s*\}\s*/,
  ''
);

// 3. Remove isRefreshingManual state
content = content.replace(
  /  const \[isRefreshingManual, setIsRefreshingManual\] = useState\(false\)\s*/,
  ''
);

// 4. Remove KPI constants
content = content.replace(
  /  \/\/ KPIs desde el backend.*?const kpiPagosMes = Number\(resumenData\?\.pagos_mes \?\? 0\) \|\| 0\s*/s,
  ''
);

// 5. Remove header section with refresh button
content = content.replace(
  /      \{\/\* Header balanceado.*?Actualizar KPIs<\/Button>\s*<\/Button>\s*<\/div>\s*/s,
  ''
);

// 6. Remove error message section
content = content.replace(
  /      \{\/\* Mensaje de error si hay problema cargando datos \*\/\}.*?<\/div>\s*\}\)\s*/s,
  ''
);

// 7. Remove KPI Cards section
content = content.replace(
  /      \{\/\* KPI Cards.*?<\/Card>\s*<\/div>\s*/s,
  ''
);

// 8. Clean up queryClient invalidations in report generation
content = content.replace(
  /\s*queryClient\.invalidateQueries\(\{ queryKey: \['reportes-resumen'\] \}\)\s*queryClient\.invalidateQueries\(\{ queryKey: \['kpis'\] \}\)/g,
  ''
);

// 9. Remove queryClient from dependencies if it's no longer needed (check usage)
// Keep queryClient for now as it's used in DialogConciliacion

fs.writeFileSync(filePath, content, 'utf8');
console.log('KPIs section removed successfully');
