# Feature priorities

Every feature from the product plan, ranked by how much it matters to a Kolkata resident.
Status reflects the code today.

- **P1, most important:** the product fails without it.
- **P2, important:** strong daily value.
- **P3, useful:** good once the basics are steady.
- **P4, least important:** wait for partners, data or real demand.

## P1: most important

| Feature | Status | What is left |
| --- | --- | --- |
| Live city map and fast reporting | Built | Test on a real phone |
| Still there and cleared confirmations | Built | |
| Today brief | Built | |
| Rain in the next 2 hours | Built | Accuracy is coarse |
| Official alerts by area | Built | Not yet seen with a live West Bengal alert |
| Saved routes and route check | Built | |
| Google place search, saved places and From/To routes | Built | Needs `GOOGLE_MAPS_API_KEY`; check Google's map display terms before launch |
| Sign up, login, password reset, email confirmation | Built | Needs a real mail host |
| Bangla across the app | Built | Needs review by native readers |
| Waterlogging from terrain and rain | Pipeline built | Model waits for 300 real reports |
| Low-lying ground map | Built | Kolkata only |
| Emergency numbers and safety checklists | Built | Verify numbers before launch |

## P2: important

| Feature | Status | What is left |
| --- | --- | --- |
| Telegram alerts | Built | Needs a bot token |
| Web push alerts | Not built | Needs push keys |
| Humid heat index and night heat | Built | |
| Best time outdoors | Built | |
| Week planner and Puja hours | Built | |
| Climate story | Built | |
| Shareable status cards | Built | |
| Complaint helper | Built | Verify current KMC channels |
| Satellite heat for North and South 24 Parganas | Not built | Needs a grid for each district |
| Cyclone tracker | Built | Live GDACS storms on Home and Safety; not yet seen with an active storm here |
| Winter smog and fireworks tracker | Not built | Needs stored air history |
| Sensitive group mode | Built | Extra care tips on Home, saved only on the device |

## P3: useful

| Feature | Status | What is left |
| --- | --- | --- |
| Cool and water spots | Built | Needs residents to add places |
| Power cut, fallen tree and blocked road reports | Built | |
| Mosquito and stagnant water reports | Built | |
| Local Guardians levels | Built | |
| Issue history for a place | Built | Appears once a place has reports |
| Neighbourhood scorecards | Built | Ground heat, greenery and low ground, Kolkata only |
| Commute nudges | Built | Set a leaving time on a saved route; Telegram needs a bot token |
| Open dataset | Built | `/open-data`; confirm the CC BY 4.0 licence before launch |
| Privacy-friendly usage counts | Not built | |

## P4: least important

| Feature | Status | Why it waits |
| --- | --- | --- |
| Transport disruption board | Not built | Needs reports first |
| Rain and tide signal | Not built | Needs a reliable tide source and expert review |
| Relief and volunteer board | Not built | Needs partners and strict moderation |
| Official KMC data | Not built | Needs a partnership |
| PostGIS migration | Not started | Needs real scale |
