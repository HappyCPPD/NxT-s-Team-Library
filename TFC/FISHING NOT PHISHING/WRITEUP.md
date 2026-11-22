# FISHING NOT PHISHING — Writeup

## Challenge summary

The challenge supplies a cropped photograph of a vessel and asks for its MMSI, departure port, the date and UTC time at which it began fishing, and the distance from the port to the fishing location.

Because the challenge was released in September 2026, “three years ago, during this same month” refers to **September 2023**.

## Identifying the vessel

A Google Lens reverse-image search pointed to the Romanian research trawler **STEAUA DE MARE 1**. Alternate photographs confirmed the identification through the vessel's distinctive features:

- dark-blue hull and white superstructure
- five wheelhouse windows
- blue external stairway
- yellow deck cranes
- matching porthole arrangement

The [ShipSpotting entry](https://www.shipspotting.com/photos/3042000) lists the vessel's details:

- Name: `STEAUA DE MARE 1`
- IMO: `8008709`
- MMSI: `264900119`

## Reconstructing the voyage

Searching MMSI `264900119` on [Global Fishing Watch](https://globalfishingwatch.org/platform/vessel-search) and selecting September 2023 reveals a voyage from **Constanta, Romania**, on 21 September 2023.

The first fishing event associated with that voyage is:

- Start: `2023-09-21T07:17:06Z`
- GFW event marker: `44.0637, 28.9227`

The Global Fishing Watch port-visit marker for Constanta is:

- Port marker: `44.1101, 28.7383`

The main trap is that the fishing event overlaps the end of GFW's unusually broad port-visit window. Skipping the overlapping event leads to the later—and incorrect—time of `01:13 PM`.

## Distance calculation

The straight-line great-circle distance between the two GFW markers can be calculated with the haversine formula:

```text
d = 2R * asin(sqrt(
 sin²((lat2-lat1)/2)
 + cos(lat1) * cos(lat2) * sin²((lon2-lon1)/2)
 ))
```

Using an Earth radius of `6371 km`:

```text
Constanta port: 44.1101, 28.7383
Fishing marker: 44.0637, 28.9227
Distance: 15.6056 km
Rounded: 15.6 km
```

The timestamp is already in UTC. In the required 12-hour format, `07:17` becomes `07:17 AM`.

## Flag

```text
TFCCTF{264900119_constanta_21.09.2023_07:17_AM_15.6}
```

## Included evidence

- `Fishing.jpeg` — original challenge image
- `Fishing-upscaled.png` — enlarged challenge image used during identification
- `steaua-de-mare-1-events-september-2023.csv` — exported Global Fishing Watch events
- `steaua-de-mare-1-track-september-2023.zip` — exported Global Fishing Watch vessel track

