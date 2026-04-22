const BASE_URL = (process.env.ESCANER_BASE_URL || 'https://rapicredit.onrender.com').replace(/\/$/, '');

const targets = [
  { name: 'escaner_route', path: '/pagos/escaner', expected: 200 },
  { name: 'frontend_health_escaner', path: '/health/escaner', expected: 200 },
];

async function checkTarget(target) {
  const url = `${BASE_URL}${target.path}`;
  const response = await fetch(url, {
    method: 'GET',
    headers: {
      'Cache-Control': 'no-cache',
      Pragma: 'no-cache',
    },
  });
  const text = await response.text();
  const ok = response.status === target.expected;
  return {
    ...target,
    url,
    ok,
    status: response.status,
    bodyPreview: text.slice(0, 280).replace(/\s+/g, ' ').trim(),
  };
}

async function run() {
  const startedAt = new Date().toISOString();
  const results = [];
  for (const target of targets) {
    try {
      results.push(await checkTarget(target));
    } catch (error) {
      results.push({
        ...target,
        url: `${BASE_URL}${target.path}`,
        ok: false,
        status: 0,
        bodyPreview: error instanceof Error ? error.message : String(error),
      });
    }
  }

  const failed = results.filter((r) => !r.ok);
  console.log(
    JSON.stringify(
      {
        check: 'escaner-smoke',
        started_at: startedAt,
        finished_at: new Date().toISOString(),
        base_url: BASE_URL,
        ok: failed.length === 0,
        results,
      },
      null,
      2
    )
  );

  if (failed.length > 0) {
    process.exitCode = 1;
  }
}

run();
