import React from 'react';
import { CircleMarker, MapContainer, TileLayer, useMap } from 'react-leaflet';
import type { LatLngExpression } from 'leaflet';
import 'leaflet/dist/leaflet.css';

import { cn } from '../../lib/utils';

interface LocationDisplayMapProps {
  value?: {
    latitude?: number | null;
    longitude?: number | null;
  } | null;
  zoom?: number;
  className?: string;
}

const MAP_TILE_URL = import.meta.env.VITE_MAP_TILE_URL
  || 'https://tile.openstreetmap.org/{z}/{x}/{y}.png';
const MAP_ATTRIBUTION = import.meta.env.VITE_MAP_ATTRIBUTION
  || '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors';

function MapViewport({ center, zoom }: { center: LatLngExpression; zoom: number }) {
  const map = useMap();

  React.useEffect(() => {
    map.setView(center, zoom);
    const frame = window.requestAnimationFrame(() => map.invalidateSize());
    return () => window.cancelAnimationFrame(frame);
  }, [center, map, zoom]);

  return null;
}

export function LocationDisplayMap({ value, zoom = 15, className }: LocationDisplayMapProps) {
  const latitude = value?.latitude;
  const longitude = value?.longitude;
  if (latitude == null || longitude == null) {
    return (
      <div className={cn('flex aspect-video items-center justify-center rounded-md border bg-muted/30 text-sm text-muted-foreground', className)}>
        -
      </div>
    );
  }

  const center: LatLngExpression = [latitude, longitude];
  return (
    <div className={cn('space-y-1', className)}>
      <MapContainer
        center={center}
        zoom={zoom}
        scrollWheelZoom={false}
        dragging={false}
        doubleClickZoom={false}
        className="aspect-video w-full rounded-md border"
        style={{ minHeight: '12rem', width: '100%' }}
      >
        <TileLayer attribution={MAP_ATTRIBUTION} url={MAP_TILE_URL} />
        <MapViewport center={center} zoom={zoom} />
        <CircleMarker
          center={center}
          radius={8}
          pathOptions={{ color: 'hsl(var(--primary))', fillOpacity: 0.85 }}
        />
      </MapContainer>
      <p className="truncate text-xs text-muted-foreground">
        {latitude}, {longitude}
      </p>
    </div>
  );
}
