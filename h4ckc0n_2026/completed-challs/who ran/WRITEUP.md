# who ran

Flag (accepted): `d4rk{35.9545685,50.7236063}`

## Solve

1. `who_ran.webp` is a Google Maps screenshot of a user-contributed photosphere. Metadata has nothing useful (macOS screenshot).
2. The billboard reads "هایپر کالای خانه آرتیمال+" (Artimal+, home goods hypermarket). Searching the name places the store in Hashtgerd, Alborz province, Iran. The bottom line of the billboard mentions old Hashtgerd, below the freeway bridge.
3. The compass in the screenshot points the camera roughly north-west (~305°), which fits the Karaj–Qazvin freeway heading towards Qazvin, just before the Hashtgerd exit.
4. Street View coverage there is a photo trail by contributor "Hamed Zarepoor" (Apr 2023), shot from the same black car bonnet seen in the screenshot.
5. Stepping along the trail with `https://www.google.com/maps/@?api=1&map_action=pano&viewpoint=LAT,LNG&heading=305` finds the yellow Artimal billboard between 35.9544 and 35.9547 N. Frames are 10–20 m apart:

| Frame | Match |
|---|---|
| 35.9543955, 50.7238484 | too early, white billboard still visible on the left |
| 35.9544821, 50.7237272 | too early, lamp post far left |
| **35.9545685, 50.7236063** | matches: white car's door, mirror and front wheel, oncoming white car beside the lamp post, lane dash at its bumper |
| 35.9546551, 50.7234851 | too late, only the white car's bonnet is left in frame |

Coordinates are read from the Google Maps URL of the matching frame.
