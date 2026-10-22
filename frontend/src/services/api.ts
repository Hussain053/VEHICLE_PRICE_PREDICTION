import type { ApiOptions, PredictionRequest, PredictionResponse } from "../types";

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8005").replace(/\/$/, "");

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      headers: { "Content-Type": "application/json", ...init?.headers },
    });
  } catch {
    throw new Error("We couldn't reach the prediction service. Check that the API is running and try again.");
  }

  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = typeof body.detail === "string" ? body.detail : "The request could not be completed.";
    throw new Error(detail);
  }
  return body as T;
}

export const fetchOptions = () => request<ApiOptions>("/api/options");

export const predictPrice = (input: PredictionRequest) =>
  request<PredictionResponse>("/api/predict", {
    method: "POST",
    body: JSON.stringify(input),
  });
