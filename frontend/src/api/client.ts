import axios, { AxiosError } from "axios";

import type { ApiErrorBody } from "./types";

export const TOKEN_KEY = "climatesense.token";

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? "/api/v1",
  timeout: 25000,
  headers: { Accept: "application/json" },
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem(TOKEN_KEY);
  if (token) {
    config.headers.Authorization = `Token ${token}`;
  }
  return config;
});

// The API rejects a dead token even on public pages, so drop it and retry signed out.
api.interceptors.response.use(undefined, (error: AxiosError) => {
  const config = error.config;
  if (error.response?.status === 401 && config && localStorage.getItem(TOKEN_KEY)) {
    localStorage.removeItem(TOKEN_KEY);
    config.headers.delete("Authorization");
    return api.request(config);
  }
  return Promise.reject(error);
});

export interface NormalizedError {
  code: string;
  message: string;
  details: Record<string, string[]> | string | null;
  status: number | null;
}

export function normalizeError(error: unknown): NormalizedError {
  if (axios.isAxiosError(error)) {
    const axiosError = error as AxiosError<ApiErrorBody>;
    const payload = axiosError.response?.data;
    const envelope = payload?.error;
    if (envelope) {
      return {
        code: envelope.code ?? "error",
        message: envelope.message ?? "The request could not be completed.",
        details: (envelope.details as Record<string, string[]> | string | null) ?? null,
        status: axiosError.response?.status ?? null,
      };
    }
    if (axiosError.code === "ECONNABORTED") {
      return {
        code: "timeout",
        message: "The server took too long to respond.",
        details: null,
        status: null,
      };
    }
    if (!axiosError.response) {
      return {
        code: "network_error",
        message: "Cannot reach the ClimateSense API. Is the backend running?",
        details: null,
        status: null,
      };
    }
    return {
      code: "http_error",
      message: `Request failed with status ${axiosError.response.status}.`,
      details: null,
      status: axiosError.response.status,
    };
  }
  return {
    code: "unknown_error",
    message: error instanceof Error ? error.message : "An unexpected error occurred.",
    details: null,
    status: null,
  };
}

export function fieldErrors(details: NormalizedError["details"]): string[] {
  if (!details) return [];
  if (typeof details === "string") return [details];
  return Object.entries(details).flatMap(([field, messages]) =>
    Array.isArray(messages) ? messages.map((message) => `${field}: ${message}`) : [],
  );
}
