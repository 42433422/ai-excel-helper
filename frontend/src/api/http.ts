import axios from "axios";
import { attachAxiosDbReadInterceptor } from "./attachAxiosDbReadInterceptor";

export const api = axios.create({
  baseURL: "",
});

attachAxiosDbReadInterceptor(api);
