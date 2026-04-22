Project Name
NavSafe – Smart Safe Route Navigation System
Theme- Open Innovation

Problem Statement:
In India, safety during travel- especially for women at night, remains a serious and growing
concern. According to the National Crime Records Bureau(NCRB), over 4.48 lakh cases of
crime against women were reported in 2023. Additionally, major categories such as assault,
kidnapping, and harassment collectively form a significant portion of these crimes, many of
which occur in public spaces during travel.
Our project introduces a Safety-Aware Smart Navigation System that prioritises user safety
alongside distance and time. This solution integrates factors like crime risk, street lighting,
and isolation into a unified safety score for each road segment. Using real-world map data
and graph-based algorithms, the system computes both the shortest and the safest routes,
allowing users to make informed decisions.
The innovation lies in transforming subjective safety concerns into measurable parameters
and embedding them into routing algorithms, enabling context-aware and safety-first
navigation, not offered by traditional Google Map

Solution
NavSafe is a web-based navigation system that provides:

Shortest route
Safest route (based on safety score)
It calculates a Safety Score (0–100) using real-time factors like:
time risk (day/night)
road isolation/density
proximity to police stations
proximity to hospitals
nearby CCTV camera locations (
It displays routes on an interactive map and stores route history for users.

Tech Stack-

Frontend:
HTML
CSS
JavaScript (basic)
Folium Map (embedded)

Backend:
Python Flask

Algorithms / DSA:
Graph (Adjacency List)
Dijkstra Algorithm
Min Heap / Priority Queue

Libraries / APIs:

OSMnx (road graph extraction)
Overpass API (police/hospital/CCTV data)
Folium (map rendering)

Database:
MySQL 

Team Members

Shravani Patil

Varada Kachroo
