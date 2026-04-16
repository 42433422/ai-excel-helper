/**
 * 在主工程 axios 实例上注册一级读头（解决 price-list-template-preview、list 等 403）。
 * 在创建 axios 后调用一次： attachAxiosDbReadInterceptor(api);
 */
import type { AxiosInstance, InternalAxiosRequestConfig } from "axios";
import { combinedRequestUrl, dbReadHeaders, urlNeedsDbReadToken } from "./dbTokenHeaders";

export function attachAxiosDbReadInterceptor(axios: AxiosInstance): void {
  axios.interceptors.request.use((config: InternalAxiosRequestConfig) => {
    const method = (config.method || "get").toLowerCase();
    if (method !== "get") return config;
    const full = combinedRequestUrl({
      baseURL: config.baseURL,
      url: config.url,
    });
    if (!urlNeedsDbReadToken(full)) return config;
    const h = dbReadHeaders();
    if (!Object.keys(h).length) return config;
    config.headers = config.headers || {};
    Object.assign(config.headers as Record<string, string>, h);
    return config;
  });
}
