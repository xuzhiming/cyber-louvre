# Stair audit before / after

Rules: side gap to wall <=0.12 m (hugging, handrail on the wall side) or >=1.2 m; approach / exit zone >= max(width,1.8) m (grand >= max(width,3.0)); <=18 risers per flight; turn landing depth >= width, straight landing >= 1.2 m; riser 0.15-0.17, tread 0.30-0.32, 2R+T 0.60-0.64; headroom >= 2.4 m; handrails both sides; slab openings guarded; no door overlap.

## S_PM (main pyramid -> B1)
- BEFORE: w 3.0; 1 flt, max 36 risers; tread 0.30, 2R+T 0.633; side-gap(min) -; zones in/out 15.0/15.0 m (need 3.0); landings: none; head 2.43
  - issues: 36 risers in one flight
- AFTER:  w 3.4; 2 flt, max 18 risers; tread 0.30, 2R+T 0.633; side-gap(min) -; zones in/out 15.0/15.0 m (need 3.4); landings: s 3.0; head 2.60
  - issues: none

## S_PSL / S_PSR (small pyramids -> B1)
- BEFORE: w 2.0; 2 flt, max 18 risers; tread 0.28, 2R+T 0.613; side-gap(min) 1.54; zones in/out 3.7/4.8 m (need 2.0); landings: t 2.4; head 2.43
  - issues: tread 0.28
- AFTER:  w 2.0; 2 flt, max 18 risers; tread 0.30, 2R+T 0.633; side-gap(min) 1.54; zones in/out 3.7/4.8 m (need 2.0); landings: t 2.4; head 2.60
  - issues: none

## S_LOBBY (B1 spine -> lobby)
- BEFORE: w 3.0; 1 flt, max 36 risers; tread 0.30, 2R+T 0.633; side-gap(min) 3.30; zones in/out 15.0/15.0 m (need 3.0); landings: none; head 2.60
  - issues: 36 risers in one flight
- AFTER:  w 3.4; 2 flt, max 18 risers; tread 0.30, 2R+T 0.633; side-gap(min) 3.10; zones in/out 15.0/15.0 m (need 3.4); landings: s 3.0; head 2.60
  - issues: none

## S_GR1W / S_GR1E (grand stair L1->L2)
- BEFORE: w 3.5; 1 flt, max 48 risers; tread 0.30, 2R+T 0.633; side-gap(min) 0.10; zones in/out 0.6/15.0 m (need 3.5); landings: none; head 23.60
  - issues: 48 risers in one flight; start zone 0.59 < 3.50
- AFTER:  w 3.2; 3 flt, max 16 risers; tread 0.30, 2R+T 0.633; side-gap(min) 1.30; zones in/out 3.3/6.3 m (need 3.2); landings: s 1.8,s 1.8; head 3.55
  - issues: none

## S_GR2W / S_GR2E (grand stair L2->L3)
- BEFORE: w 3.4; 2 flt, max 24 risers; tread 0.30, 2R+T 0.633; side-gap(min) 3.90; zones in/out 12.6/12.6 m (need 3.4); landings: t 3.2; head 15.60
  - issues: 24 risers in one flight; landing 0 depth 3.20 < 3.40
- AFTER:  w 3.2; 4 flt, max 12 risers; tread 0.30, 2R+T 0.633; side-gap(min) 5.40; zones in/out 11.0/11.0 m (need 3.2); landings: s 1.2,t 3.2,s 1.2; head 15.60
  - issues: none

## S_PAV_{NW,NE,SW,SE}_{L1,L2,L3} (12 pavilion core stairs)
- BEFORE: w 3.4; 2 flt, max 24 risers; tread 0.28, 2R+T 0.613; side-gap(min) 0.90; zones in/out 2.0/2.0 m (need 3.4); landings: t 5.0; head 7.53
  - issues: tread 0.28; 24 risers in one flight; wall slot [0.7, 0.9, 1.1]; start zone 1.99 < 3.40; end zone 1.99 < 3.40
- AFTER:  w 3.0; 4 flt, max 12 risers; tread 0.30, 2R+T 0.633; side-gap(min) 0.05; zones in/out 3.0/3.0 m (need 3.0); landings: s 1.2,t 3.0,s 1.2; head 7.53
  - issues: none

**Stairs with at least one violation: 20 of 20 before -> 0 of 20 after.**
