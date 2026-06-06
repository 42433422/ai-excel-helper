import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend } from 'k6/metrics';
import { BASE_URL, API_PATHS } from './config.js';

const errorRate = new Rate('error_rate');
const apiDuration = new Trend('api_duration');

export const options = {
  stages: [
    { duration: '30s', target: 10 },
    { duration: '1m', target: 50 },
    { duration: '1m', target: 50 },
    { duration: '30s', target: 10 },
  ],
  thresholds: {
    http_req_duration: ['p(99)<1000'],
    error_rate: ['rate<0.1'],
  },
};

export default function () {
  const healthRes = http.get(`${BASE_URL}${API_PATHS.health}`);
  check(healthRes, {
    'health status is 200': (r) => r.status === 200,
  });
  errorRate.add(healthRes.status !== 200);
  apiDuration.add(healthRes.timings.duration);

  sleep(1);

  const catalogRes = http.get(`${BASE_URL}${API_PATHS.products}`);
  check(catalogRes, {
    'mod-store catalog is 200': (r) => r.status === 200,
  });
  errorRate.add(catalogRes.status !== 200);
  apiDuration.add(catalogRes.timings.duration);

  sleep(1);

  const livenessRes = http.get(`${BASE_URL}${API_PATHS.shipments}`);
  check(livenessRes, {
    'liveness is 200': (r) => r.status === 200,
  });
  errorRate.add(livenessRes.status !== 200);
  apiDuration.add(livenessRes.timings.duration);

  sleep(1);
}
