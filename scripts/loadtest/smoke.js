import http from 'k6/http';
import { check, sleep } from 'k6';
import { BASE_URL, API_PATHS } from './config.js';

export const options = {
  vus: 5,
  duration: '30s',
  thresholds: {
    // GitHub-hosted runners are noisy; gate on availability not sub-500ms p99.
    http_req_duration: ['p(99)<5000'],
    http_req_failed: ['rate<0.05'],
  },
};

export function handleSummary(data) {
  return {
    'results.json': JSON.stringify(data, null, 2),
  };
}

export default function () {
  const healthRes = http.get(`${BASE_URL}${API_PATHS.health}`);
  check(healthRes, {
    'health status is 200': (r) => r.status === 200,
  });

  sleep(1);

  const pingRes = http.get(`${BASE_URL}/api/ping`);
  check(pingRes, {
    'ping is 200': (r) => r.status === 200,
  });

  sleep(1);
}
