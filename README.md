# LakbayWise
A personal AI-powered itinerary project that also supports accessibility and disabled travelers, along with other features.

# Purpose
Planning a day out in a place you don't know takes a lot of small decisions: what to see, in what order, how long it takes to get there, where to eat, and what it costs. It is harder when you use a wheelchair or have other access needs, because most trip sites don't tell you whether a place works for you.
LakbayWise turns a few answers into a day plan you can read, change and share. It is built first for Calamba, Laguna in the Philippines, and is meant to grow to other Laguna cities later.

# Concept
You tell the planner where you are staying, which dates, how many people, when you want to start, your budget, how many places you want each day, and what you are thinking about (for example hot springs, churches or parks). The planner builds each day around one area, so you don't zigzag across the city.
Each day is split into morning, afternoon and evening. Lunch and dinner are placed at normal mealtimes. Between stops it shows the drive time and warns about rush hour. After the plan is built you can:
• remove a place and undo it,
• add a place from the "More places near your route" section to the morning, afternoon or evening,
• see the route on a map,
• share the plan with a link, or print it.

# Accessibility
Accessibility is a core part of the idea, not an extra.
• You can say what access you need when you plan.
• Each stop shows its wheelchair access and a note for rough terrain.
• Places with unknown access are still shown, with a clear warning. Only places known to be inaccessible are left out.
• We do not guess. If access has not been checked, the plan says so.

# How places are chosen
• Only public, walk-in places are planned: landmarks, parks, hot springs, food and similar. Private resorts that need a booking are kept apart and are not planned for now.
• Place data comes from OpenStreetMap, plus a list that is reviewed by hand. There is no paid map service in the beta.
• Local places are preferred over chains.
• Costs are only shown where we have a basis: meals (about 375 PHP per person) and hot springs (usually from 800 PHP per person). Parks, markets, malls and landmarks are not priced. All amounts are labeled as estimates.

# Where the AI fits
The beta planner follows fixed rules, so the same answers give the same plan. It reads your typed budget and the places you mention by matching keywords in English and Tagalog. The AI part is planned for later: understanding your free-text wishes and writing the reasons for each stop. The raw text you type is already saved for that.

# Current limits
• Calamba only, by car only. No public transport yet.
• No user accounts. A plan is kept by its link.
• Drive times are estimates when the route service is unavailable.
• Hours, prices and access should be checked before you go.
