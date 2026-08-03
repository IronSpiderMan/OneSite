import * as React from 'react';
import { Crosshair, Loader2, MapPin } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { CircleMarker, MapContainer, TileLayer, useMap, useMapEvents } from 'react-leaflet';
import type { LatLngExpression } from 'leaflet';
import 'leaflet/dist/leaflet.css';

import { Button } from './button';
import { Input } from './input';

export interface LocationValue {
  latitude: number | null;
  longitude: number | null;
}

interface LocationInputProps {
  value?: Partial<LocationValue> | null;
  onChange: (value: LocationValue) => void;
  disabled?: boolean;
}

const parseCoordinate = (rawValue: string): number | null => {
  if (rawValue.trim() === '') return null;
  const parsed = Number(rawValue);
  return Number.isFinite(parsed) ? parsed : null;
};

const DEFAULT_MAP_CENTER: LatLngExpression = [35, 105];
const MAP_TILE_URL = import.meta.env.VITE_MAP_TILE_URL
  || 'https://tile.openstreetmap.org/{z}/{x}/{y}.png';
const MAP_ATTRIBUTION = import.meta.env.VITE_MAP_ATTRIBUTION
  || '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors';

function MapSelectionEvents({ onSelect }: { onSelect: (value: LocationValue) => void }) {
  useMapEvents({
    click: ({ latlng }) => {
      onSelect({ latitude: latlng.lat, longitude: latlng.lng });
    },
  });
  return null;
}

function MapViewport({ center }: { center: LatLngExpression }) {
  const map = useMap();

  React.useEffect(() => {
    map.panTo(center);
    const frame = window.requestAnimationFrame(() => map.invalidateSize());
    return () => window.cancelAnimationFrame(frame);
  }, [center, map]);

  return null;
}

export function LocationInput({ value, onChange, disabled = false }: LocationInputProps) {
  const { t } = useTranslation();
  const [locating, setLocating] = React.useState(false);
  const [mapOpen, setMapOpen] = React.useState(false);
  const [tileError, setTileError] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  const currentValue: LocationValue = {
    latitude: value?.latitude ?? null,
    longitude: value?.longitude ?? null,
  };
  const hasSelectedLocation = currentValue.latitude !== null && currentValue.longitude !== null;
  const mapCenter = React.useMemo<LatLngExpression>(
    () => hasSelectedLocation
      ? [currentValue.latitude as number, currentValue.longitude as number]
      : DEFAULT_MAP_CENTER,
    [currentValue.latitude, currentValue.longitude, hasSelectedLocation],
  );

  const updateCoordinate = (key: keyof LocationValue, rawValue: string) => {
    setError(null);
    onChange({ ...currentValue, [key]: parseCoordinate(rawValue) });
  };

  const locate = () => {
    if (!navigator.geolocation) {
      setError(t('location.unsupported', 'Geolocation is not supported by this browser.'));
      return;
    }

    setLocating(true);
    setError(null);
    navigator.geolocation.getCurrentPosition(
      ({ coords }) => {
        onChange({ latitude: coords.latitude, longitude: coords.longitude });
        setLocating(false);
      },
      (geolocationError) => {
        const key = geolocationError.code === geolocationError.PERMISSION_DENIED
          ? 'location.permission_denied'
          : geolocationError.code === geolocationError.TIMEOUT
            ? 'location.timeout'
            : 'location.unavailable';
        setError(t(key, 'Unable to get the current location.'));
        setLocating(false);
      },
      { enableHighAccuracy: true, timeout: 15000, maximumAge: 0 },
    );
  };

  return (
    <div className="space-y-2">
      <div className="grid gap-2 sm:grid-cols-2">
        <Input
          aria-label={t('location.latitude', 'Latitude')}
          type="number"
          min={-90}
          max={90}
          step="any"
          placeholder={t('location.latitude', 'Latitude')}
          value={currentValue.latitude ?? ''}
          onChange={(event) => updateCoordinate('latitude', event.target.value)}
          disabled={disabled || locating}
        />
        <Input
          aria-label={t('location.longitude', 'Longitude')}
          type="number"
          min={-180}
          max={180}
          step="any"
          placeholder={t('location.longitude', 'Longitude')}
          value={currentValue.longitude ?? ''}
          onChange={(event) => updateCoordinate('longitude', event.target.value)}
          disabled={disabled || locating}
        />
      </div>
      <div className="flex flex-wrap gap-2">
        <Button type="button" variant="outline" onClick={locate} disabled={disabled || locating}>
          {locating ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Crosshair className="mr-2 h-4 w-4" />}
          {locating
            ? t('location.locating', 'Locating...')
            : t('location.use_current', 'Use current location')}
        </Button>
        <Button
          type="button"
          variant="outline"
          onClick={() => setMapOpen((open) => !open)}
          disabled={disabled}
        >
          <MapPin className="mr-2 h-4 w-4" />
          {mapOpen
            ? t('location.hide_map', 'Hide map')
            : t('location.choose_on_map', 'Choose on map')}
        </Button>
      </div>
      {mapOpen && (
        <div className="space-y-2 rounded-md border p-2">
          <MapContainer
            center={mapCenter}
            zoom={hasSelectedLocation ? 15 : 4}
            scrollWheelZoom
            className="h-72 w-full rounded-md"
            style={{ height: '18rem', minHeight: '18rem', width: '100%' }}
          >
            <TileLayer
              attribution={MAP_ATTRIBUTION}
              url={MAP_TILE_URL}
              eventHandlers={{
                loading: () => setTileError(false),
                tileerror: () => setTileError(true),
              }}
            />
            <MapSelectionEvents onSelect={onChange} />
            <MapViewport center={mapCenter} />
            {hasSelectedLocation && (
              <CircleMarker
                center={mapCenter}
                radius={8}
                pathOptions={{ color: 'hsl(var(--primary))', fillOpacity: 0.85 }}
              />
            )}
          </MapContainer>
          <p className="text-xs text-muted-foreground">
            {t('location.map_hint', 'Click the map to select a location.')}
          </p>
          {tileError && (
            <p className="text-sm text-destructive" role="alert">
              {t(
                'location.tiles_unavailable',
                'Map tiles could not be loaded. Check the network or configure VITE_MAP_TILE_URL.',
              )}
            </p>
          )}
        </div>
      )}
      {error && <p className="text-sm text-destructive" role="alert">{error}</p>}
    </div>
  );
}
