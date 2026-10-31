import { api } from "../api/client";
import type { PickedPlace, PlaceSuggestion } from "../api/types";

export function newSession(): string {
  // randomUUID needs https, which a phone testing over the local network may not have.
  return crypto.randomUUID?.() ?? `${Date.now()}-${Math.random()}`;
}

export async function resolveSuggestion(item: PlaceSuggestion, session: string): Promise<PickedPlace> {
  if (item.latitude !== undefined && item.longitude !== undefined) {
    return { label: item.title, latitude: item.latitude, longitude: item.longitude };
  }
  const response = await api.get<{ title: string; latitude: number; longitude: number }>("/places/details/", {
    params: { place_id: item.place_id, session },
  });
  return { label: response.data.title || item.title, latitude: response.data.latitude, longitude: response.data.longitude };
}
