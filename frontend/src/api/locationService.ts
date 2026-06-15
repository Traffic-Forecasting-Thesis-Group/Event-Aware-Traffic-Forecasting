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

// A single point along the route, used to draw the Polyline on the map
export interface RouteGeometryPoint {
  latitude: number;
  longitude: number;
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
  // Full road-following path returned by TomTom, used for the Polyline.
  route_geometry?: RouteGeometryPoint[];
}

export interface RouteCalculationRequest {
  origin: string;
  destination: string;
  // Optional precise coordinates so the backend doesn't have to re-geocode
  origin_lat?: number;
  origin_lng?: number;
  destination_lat?: number;
  destination_lng?: number;
}

export async function fetchDynamicRouteEstimation(
  origin: string,
  destination: string,
  originCoords?: { latitude: number; longitude: number },
  destCoords?: { latitude: number; longitude: number }
): Promise<RouteDataResponse> {
  const payload: RouteCalculationRequest = { origin, destination };

  if (originCoords) {
    payload.origin_lat = originCoords.latitude;
    payload.origin_lng = originCoords.longitude;
  }
  if (destCoords) {
    payload.destination_lat = destCoords.latitude;
    payload.destination_lng = destCoords.longitude;
  }

  const { data } = await apiClient.post<RouteDataResponse>('/api/route/calculate', payload);
  return data;
}
