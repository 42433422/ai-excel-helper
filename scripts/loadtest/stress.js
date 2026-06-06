import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate } from 'k6/metrics';
import { BASE_URL, API_PATHS } from './config.js';

const errorRate = new Rate('error_rate');

export const options = {
  stages: [
    { duration: '30s', target: 50 },
    { duration: '1m', target: 100 },
    { duration: '1m', target: 200 },
    { duration: '1m', target: 200 },
    { duration: '30s', target: 100 },
    { duration: '30s', target: 50 },
  ],
  thresholds: {
    http_req_duration: ['p(99)<2000'],
    http_req_failed: ['rate<0.15'],
  },
};

export default function () {
  const healthRes = http.get(`${BASE_URL}${API_PATHS.health}`);
  check(healthRes, {
    'health status is 200': (r) => r.status === 200,
  });
  errorRate.add(healthRes.status !== 200);

  sleep(1);

  const catalogRes = http.get(`${BASE_URL}${API_PATHS.products}`);
  check(catalogRes, {
    'mod-store catalog is 200': (r) => r.status === 200,
  });
  errorRate.add(catalogRes.status !== 200);

  sleep(1);

  const livenessRes = http.get(`${BASE_URL}${API_PATHS.shipments}`);
  check(livenessRes, {
    'liveness is 200': (r) => r.status === 200,
  });
  errorRate.add(livenessRes.status !== 200);

  sleep(1);

  const authRes = http.post(
    `${BASE_URL}${API_PATHS.auth}`,
    JSON.stringify({ username: 'k6_loadtest', password: 'invalid' }),
    { headers: { 'Content-Type': 'application/json' } }
  );
  check(authRes, {
    'auth status is 200 or 401': (r) => r.status === 200 || r.status === 401,
  });
  errorRate.add(authRes.status !== 200 && authRes.status !== 401);

  sleep(1);
}

export function teardown(data) {
  console.log('Stress test completed');
  console.log(`Base URL: ${BASE_URL}`);
  console.log('Summary: Stress test with VUs ramping 50→100→200→200→100→50 over 5 minutes');
}
