import { MapContainer, TileLayer, Marker, Polyline, Popup } from "react-leaflet"
import L from "leaflet"
import "leaflet/dist/leaflet.css"
import type { RastreioData } from "@/types"
import { CAPITAL_COORDS } from "@/constants"

// Fix default Leaflet icon (Vite/webpack issue)
delete (L.Icon.Default.prototype as unknown as Record<string, unknown>)._getIconUrl
L.Icon.Default.mergeOptions({
  iconUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
  iconRetinaUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
  shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
})

interface Props {
  rastreio: RastreioData
}

export default function MapaRastreio({ rastreio }: Props) {
  const withCoords = rastreio.checkpoints.filter(
    (cp) => cp.galpao.lat != null && cp.galpao.lng != null
  )

  const originCoords = rastreio.estado_origem ? CAPITAL_COORDS[rastreio.estado_origem] : undefined
  const destCoords = rastreio.estado_destino ? CAPITAL_COORDS[rastreio.estado_destino] : undefined

  const center: [number, number] =
    withCoords.length > 0
      ? [withCoords[0].galpao.lat!, withCoords[0].galpao.lng!]
      : (originCoords ?? destCoords ?? [-15.7801, -47.9292])

  const line: [number, number][] = [
    ...(originCoords ? [originCoords] : []),
    ...withCoords.map((cp): [number, number] => [cp.galpao.lat!, cp.galpao.lng!]),
    ...(destCoords ? [destCoords] : []),
  ]

  return (
    <div className="rounded-xl overflow-hidden border" style={{ height: "40vh" }}>
      <MapContainer center={center} zoom={5} style={{ height: "100%", width: "100%" }}>
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        {originCoords && (
          <Marker position={originCoords}>
            <Popup>Origem · {rastreio.estado_origem}</Popup>
          </Marker>
        )}
        {withCoords.map((cp) => (
          <Marker key={cp.id} position={[cp.galpao.lat!, cp.galpao.lng!]}>
            <Popup>{cp.galpao.nome} — {cp.galpao.cidade}/{cp.galpao.estado}</Popup>
          </Marker>
        ))}
        {destCoords && (
          <Marker position={destCoords}>
            <Popup>Destino · {rastreio.estado_destino}</Popup>
          </Marker>
        )}
        {line.length > 1 && (
          <Polyline positions={line} color="red" weight={2} dashArray="6,4" />
        )}
      </MapContainer>
    </div>
  )
}
