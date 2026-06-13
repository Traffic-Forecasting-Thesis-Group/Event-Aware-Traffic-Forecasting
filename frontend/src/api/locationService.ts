import apiClient from './client'; 

export interface LocationPoint {
  address: string;
  lat: number | null;
  lng: number | null;
}

export interface UserLocationsPayload {
  home: LocationPoint | null;
  work: LocationPoint | null;
}

export interface GeocodeResult {
  lat: number;
  lng: number;
  formattedAddress: string;
}

const DEFAULT_HOME = 'Search your Home Address';
const DEFAULT_WORK = 'Search your Work Address';

const runtimeCachedLocations = {
  Home: DEFAULT_HOME,
  Work: DEFAULT_WORK
};

export function getCachedLocations() {
  return runtimeCachedLocations;
}

export function updateCachedLocation(type: 'Home' | 'Work', address: string) {
  runtimeCachedLocations[type] = address;
}

export function clearCachedLocations() {
  runtimeCachedLocations.Home = DEFAULT_HOME;
  runtimeCachedLocations.Work = DEFAULT_WORK;
}

export async function saveUserLocations(payload: UserLocationsPayload): Promise<void> {
  await apiClient.post('/api/user/locations', payload);
}

export async function getUserLocations(): Promise<UserLocationsPayload> {
  const { data } = await apiClient.get<UserLocationsPayload>('/api/user/locations');
  return data;
}

export async function clearUserLocations(): Promise<void> {
  await apiClient.delete('/api/user/locations');
  clearCachedLocations();
}

export async function geocodeAddress(address: string): Promise<GeocodeResult | null> {
  try {
    const { data } = await apiClient.get<GeocodeResult>('/api/geocode', {
      params: { address },
    });
    return data;
  } catch {
    return null; 
  }
}

export interface RouteDataResponse {
  duration_minutes: number;
  distance_km: number;
  primary_route: string;
  congestion: {
    level: string;
    percentage: number;
  };
  intelligence_note: string;
  formatted_destination: string;
}

export async function fetchDynamicRouteEstimation(origin: string, destination: string): Promise<RouteDataResponse> {
  const { data } = await apiClient.post<RouteDataResponse>('/api/route/calculate', { origin, destination });
  return data;
}