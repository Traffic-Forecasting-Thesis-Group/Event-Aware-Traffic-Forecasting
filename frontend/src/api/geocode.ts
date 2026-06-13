import axios from 'axios';

export interface GeocodeResult {
  id: string;
  lat: number;
  lng: number;
  formattedAddress: string;
}

export async function fetchGeocodeAddress(address: string): Promise<GeocodeResult[]> {
  if (!address.trim()) {
    return [];
  }

  try {
    const response = await axios.get('https://nominatim.openstreetmap.org/search', {
      params: {
        q: address,
        format: 'json',
        limit: 10,
        addressdetails: 1,
        viewbox: '120.90,14.75,121.15,14.35', 
        bounded: 1 
      },
      headers: {
        'User-Agent': 'FuseTraffic' 
      }
    });

    if (response.data && response.data.length > 0) {
      return response.data.map((item: any) => ({
        id: item.place_id.toString(),
        lat: parseFloat(item.lat),
        lng: parseFloat(item.lon),
        formattedAddress: item.display_name
      }));
    }

    return [];

  } catch (error) {
    if (axios.isAxiosError(error)) {
      console.error('Geocoding frontend error:', error.message);
    } else {
      console.error('Unexpected geocoding error:', error);
    }
    return [];
  }
}