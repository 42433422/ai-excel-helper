import type { AxiosInstance, InternalAxiosRequestConfig } from "axios";
import {
  combinedRequestUrl,
  dbReadHeaders,
  dbWriteHeaders,
  urlNeedsDbReadToken,
  urlNeedsDbWriteToken,
} from "../components/fhd/dbTokenHeaders";

export function attachAxiosDbReadInterceptor(axios: AxiosInstance): void {
  axios.interceptors.request.use((config: InternalAxiosRequestConfig) => {
    const method = (config.method || "get").toUpperCase();
    const full = combinedRequestUrl({
      baseURL: config.baseURL,
      url: config.url,
    });
    config.headers = config.headers || {};
    const headers = config.headers as Record<string, string>;
    if (method === "GET" && urlNeedsDbReadToken(full)) {
      Object.assign(headers, dbReadHeaders());
    }
    if (urlNeedsDbWriteToken(full, method)) {
      Object.assign(headers, dbWriteHeaders());
    }
    return config;
  });
}
