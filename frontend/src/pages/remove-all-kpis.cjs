const fs = require('fs');

const filePath = 'Reportes.tsx';
let content = fs.readFileSync(filePath, 'utf8');

// Remove the useQuery hook for KPIs data
content = content.replace(
  /  \/\/ Obtener resumen del dashboard para KPIs[\s\S]*?refetchInterval: puedeVerReportes \? 5 \* 60 \* 1000 : false,[\s\S]*?\}\)\s*/,
  ''
);

// Remove KPI constants/variables
content = content.replace(
  /  \/\/ KPIs desde el backend[\s\S]*?const kpiPagosMes = Number\(resumenData\?\.pagos_mes \?\? 0\) \|\| 0\s*/,
  ''
);

// Remove KPI Cards section (the entire grid)
content = content.replace(
  /      {\/\* KPI Cards[\s\S]*?<\/div>\s*\n\s*{\/\* Reportes:/,
  '      {/* Reportes:'
);

// Remove queryClient invalidations for kpis - using different approach
content = content.replace(/queryClient\.invalidateQueries\({ queryKey: \['kpis'\] }\)/g, '');
content = content.replace(/\s*queryClient\.invalidateQueries\({ queryKey: \['kpis'\] }\)\s*/g, '');

fs.writeFileSync(filePath, content, 'utf8');
console.log('KPIs completely removed from reports page');
