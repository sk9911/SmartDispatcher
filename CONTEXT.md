# Forecast Regret

Measures how much the quality of a weather forecast costs a flight, by comparing flights planned on forecast winds against the best flight possible with hindsight knowledge of the true winds.

## Language

### Flights and plans

**Flight**:
One city pair, flown in one direction, departing at one fixed time (e.g. JFK→LHR departing 2020-01-15 00:00 UTC).
_Avoid_: Trip, sortie, route (a route is part of a plan)

**Showcase flight**:
The single flight (JFK→LHR departing 2020-02-09 00:00 UTC, a record strong-jet night) that is re-planned live and drawn on the map.
_Avoid_: Example flight, demo case

**Plan**:
The lateral path a flight will follow, chosen at a fixed flight level and fixed Mach, using the winds of one source.
_Avoid_: Route, trajectory, flight plan

**Truth-optimised plan**:
The plan made using the truth's winds, as if the forecast had been perfect.
_Avoid_: Perfect-forecast plan, ERA5 plan

**Hindsight plan**:
The candidate plan for a flight with the lowest truth cost: the best of the truth-optimised plan and every forecast plan. Ties go to the truth-optimised plan, so there is exactly one per flight.
_Avoid_: Optimal plan, perfect plan, oracle

**Optimiser gap**:
A case where a forecast plan has a strictly lower truth cost than the plan optimised directly on the truth.
_Avoid_: Negative regret

### Weather

**Truth**:
ERA5 reanalysis winds, treated as the winds the flight actually meets.
_Avoid_: Analysis, observations, actuals

**Forecast source**:
One weather model whose forecast winds are used to plan flights (e.g. IFS HRES, GraphCast).
_Avoid_: Model (ambiguous with aircraft model), provider

**Persistence baseline**:
A no-skill forecast source: the truth at the forecast's initialisation, held frozen for the whole flight.
_Avoid_: Climatology, naive forecast

**Lead time**:
Hours from a forecast's initialisation to the flight's departure.
_Avoid_: Horizon, forecast step

**Wind error**:
The RMS vector difference between a forecast source's winds and the truth, sampled along the hindsight plan's path at the times the aircraft passes each point.
_Avoid_: Forecast skill, RMSE (unqualified)

**Ageostrophic fraction**:
How far a source's 250 hPa winds depart from geostrophic balance: |V − V_g| / |V|, over 30–70°N.
_Avoid_: Balance error, physical consistency score

### Outcomes

**Replay**:
Flying a plan's fixed path, flight level and Mach through the truth to get its true time, fuel and CO₂.
_Avoid_: Simulation, evaluation

**Cost**:
The time, fuel and CO₂ of a replayed plan, always reported as three separate quantities.
_Avoid_: Score, objective

**Regret**:
A plan's replayed cost minus the hindsight plan's replayed cost for the same flight; zero or positive by definition.
_Avoid_: Penalty, loss, error

**Zero-regret share**:
The share of flights on which a forecast source's plan has regret exactly zero, counting ties with the hindsight plan.
_Avoid_: Hit rate, win rate
