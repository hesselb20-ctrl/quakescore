# References

The curated reference list the rest of the repository cites. Every number here comes from
`docs/research/prior_art_and_ground_truth.md` or `docs/research/codes_and_fragility.md` (compiled
2026-11-11). Nothing has been added from outside those two files. Where they say NOT VERIFIED, this
file says NOT VERIFIED. "DERIVED" means arithmetic on a verified number; the formula is given.

Status labels follow `DESIGN.md`: everything in this file is `REF` unless marked otherwise.

Conventions: f1 = first-mode frequency; EW/NS = east-west/north-south; L/T = longitudinal/transverse;
zeta = damping ratio; ambient = wind, traffic and occupancy only; forced = shaker; EQ-level = recorded
during an earthquake (amplitude-dependent softening applies).

## Three corrections to a common misreading

1. **Kong et al. 2018 (Millikan Library) was a forced test, not an ambient one.** A roof shaker swept
   0.2-2.45 Hz. It shows phones can record a known structural signal at high amplitude. It does not
   show that phones can see ambient vibration.
2. **Patel et al. 2023 used earthquake-triggered recordings** (forced shaking plus the free-vibration
   coda). The authors state that ambient-level measurement was not feasible at the phone noise floor.
3. **Kumar et al. 2025 is the only ambient phone study found.** It covers four tall buildings
   (54-197 m). For shorter buildings many recordings are rejected for low signal-to-noise.

**Insurance claim: unverified.** No sentence naming insurance or insurers as an application was found
in Kong 2016, Kong 2018, Patel 2023 or Kumar 2025. Kong 2016 mentions "financial loss" from
earthquakes in general; Kong 2018 mentions reducing earthquake risks at city or national scale; Patel
2023 describes a remote diagnostic for engineering first responders to prioritise inspections;
Kumar 2025 states health monitoring, deterioration, damage and retrofit aims. So the claim that the
group lists "seismic risk assessment for insurers" as an application is unverified here and must not
be repeated in any pitch material without a source.

---

## (a) Prior art: phones and building modal identification

### Kong, Allen, Kohler, Heaton, Bunn (2018)

Kong, Q., Allen, R. M., Kohler, M. D., Heaton, T. H., Bunn, J. (2018). Structural health monitoring of
buildings using smartphone sensors. Seismological Research Letters 89(2A), 594-602.
DOI 10.1785/0220170111. https://doi.org/10.1785/0220170111

- Forced-vibration (roof shaker) test of Millikan Library, Pasadena. 25 phones of 18 listed models lay
  on the 9th floor NW corner beside the permanent Episensor (station CI MIK). Phones at 25 samples/s.
- Phones recovered f1 EW 1.2 Hz, N-S 1.7 Hz and torsion about 2.4 Hz from single-phone records, and
  double-integrated displacement matched the reference. Stacking 7 phones improved SNR.
- Spec resolution across the 18 models ranges from 5.99e-4 to 1.53e-1 m/s^2 (about 0.06 to 15.6 mg),
  a best case.
- Limits stated: ideal placement only (top floor, corner, flat on floor); other buildings, floors and
  surfaces untested; ambient recovery and lower limits of useful shaking need more work.
- Unreadable in the extracted text: units of the quoted spectral noise levels; per-phone chip mapping.

### Patel, Gunay, Marcou, Gou, Kumar, Allen (2023)

Patel, S. C., Gunay, S., Marcou, S., Gou, Y., Kumar, U., Allen, R. M. (2023). Toward Structural Health
Monitoring with the MyShake Smartphone Network. Sensors 23(21), 8668. DOI 10.3390/s23218668.
https://doi.org/10.3390/s23218668

- Earthquake-triggered data only. Shake table: 3-storey steel frame, 9 phones against reference
  accelerometers; pre-event f1 about 3.4-3.5 Hz; brace disengagement lowered f1 by up to 22%; modes
  more than about 0.4 Hz apart could be resolved.
- Real buildings: 7 structures of 3 to 18 storeys, one earthquake each (table in section c-2).
  One 5-storey L-shaped building across three earthquakes over four months gave 4.85, 4.62, 4.50 Hz.
- Repeat measurements within 7%; most frequencies within about 41% of at least one ASCE-based estimate.
- Limits: one sensor per building, unknown height and orientation, higher noise and lower sampling
  than conventional sensors, forced-vibration frequencies may be biased low relative to ambient.

### Kumar, Marcou, Allen (2025)

Kumar, U., Marcou, S., Allen, R. M. (2025). Ambient vibration analysis of high-rise buildings using
MyShake smartphone data. Journal of Building Engineering 106, 112496. DOI 10.1016/j.jobe.2025.112496.
https://doi.org/10.1016/j.jobe.2025.112496

- Ambient (wind-triggered) 5-minute recordings from phones left in 4 San Francisco Bay Area buildings
  for about six months, 50 Hz sampling. Multitaper PSD, automated peak picking, half-power damping.
- Results: Millennium Tower (197 m) 0.30 and 0.26 Hz, zeta 0.7% and 0.8%; 188 Minna St (138 m)
  about 0.33 and 0.40 Hz; Pacific Park Plaza (95 m) about 0.47-0.48 Hz, matching an earlier ambient
  0.48 Hz; SkyDeck (54 m) 0.70-0.85 Hz.
- Taller buildings give reliable estimates even in low wind; shorter buildings need stronger
  excitation and many recordings are rejected on low SNR.
- Unresolved in the paper: SkyDeck zeta "0.08 to 0.12" has no unit (NOT VERIFIED whether fraction or
  percent; 8-12% would be very high for ambient). Millennium Tower is 58 floors in the table and 56 in
  the text. The dB reference of the noise values is not restated.

### Kong, Allen, Schreier, Kwon (2016), MyShake

Kong, Q., Allen, R. M., Schreier, L., Kwon, Y.-W. (2016). MyShake: A smartphone seismic network for
earthquake early warning and beyond. Science Advances 2(2). DOI 10.1126/sciadv.1501055. The article
number e1501055 is inferred from the DOI, not separately seen.

- Phones in a quiet Berkeley basement for 1 month at 50 samples/s; noise floor by the McNamara and
  Buland method, shown only in a figure (NOT VERIFIED numerically). Free phones slid at about 0.3 g
  above about 3 Hz, so recorded amplitudes are lower bounds.

### Other peer-reviewed work

| Paper | What it showed | Limits |
|---|---|---|
| Feng, Fukuda, Mizuta, Ozer (2015). Sensors 15(2), 2980-2998. DOI 10.3390/s150202980 | Phones (iPhone 3GS, iPhone 5, Galaxy S4) matched a reference on a masonry column model (f1 ambient 18.2 vs 18.4 Hz) and a pedestrian bridge (ambient f1 3.13 vs 3.16 Hz; response under 0.005 g) | Not a building. 3 phones, not synchronised with the reference |
| Mugabo, Barbosa, Riggio (2019). Front. Built Environ. 5:86. DOI 10.3389/fbuil.2019.00086 | Four-storey mass-timber building modal values with conventional accelerometers (used here as ground truth, section c) | Not phone-based |

Not read: Ozer and Feng conference and chapter material; other groups' smartphone-in-building ambient
studies; the Sarmadi et al. review cited by Kumar. NOT VERIFIED: any further smartphone-in-building
papers.

---

## (b) Phone accelerometer noise

### Published phone noise floors

| Source | Quantity | Value | Notes |
|---|---|---|---|
| Patel 2023 (MyShake 2017 and 2021 models) | PSD floor | about -75 dB re 1 (m/s^2)^2/Hz | range -50 to -80 dB at low f, -78 to -85 dB at high f; 25-50 Hz sampling |
| Patel 2023 (2010-2013 models, 2016 basement test) | PSD floor | about -40 dB | |
| Kumar 2025 (phones in buildings) | PSD seen in field | near -70 dB; structural peaks often above -60 dB | 50 Hz, 5-min records; dB reference not restated, taken from Patel |
| DERIVED | -75 dB | 1.78e-4 m/s^2/sqrt(Hz) = 18 ug/sqrt(Hz) | sqrt(10^(-7.5)), g = 9.80665 |
| DERIVED | -70 dB | 3.2e-4 = 32 ug/sqrt(Hz) | |
| DERIVED | -60 dB | 1.0e-3 = 102 ug/sqrt(Hz) | |

### Datasheet and measured values

| Sensor | Noise density | Conditions | Source |
|---|---|---|---|
| Bosch BMI160 | typ 180, max 300 ug/sqrt(Hz) | +/-8 g, normal mode, 25 C; datasheet rev 1.0 Nov 2020 | bst-bmi160-ds000.pdf |
| Bosch BMI270 | typ 160 ug/sqrt(Hz) (0.16 mg/sqrt(Hz)) | +/-8 g, normal mode, 25 C; rev 1.6 | bst-bmi270-ds000.pdf |
| ST LSM6DSO | 70 (+/-2 g) to 110 (+/-16 g) ug/sqrt(Hz) | high-performance mode; DocID030608 Rev 1, third-party mirror | |
| TDK ICM-42688-P | AXY 65, AZ 70 ug/sqrt(Hz) | product brief PB-000072 only; full datasheet not read, conditions NOT VERIFIED | |
| iPhone 4 (LIS331DLH) | datasheet 0.218 mg/sqrt(Hz); measured 0.25 mg/sqrt(Hz) average over 6 units | Allan variance | Kos et al. 2016, https://doi.org/10.3390/s16030301 |
| iPhone 5 (LIS331DLH) / Galaxy S4 (SMB380) | 0.218 / 0.5 mg/sqrt(Hz) as printed | | Feng 2015 Table 1 (unit symbol lost in extraction) |

BMI160 and BMI270 values were read from PDFs with partly scrambled layout and must be confirmed
against the PDF tables before use. Full bibliographic details of Kos et al. 2016 are not in the
research files beyond the DOI.

### Open question: the roughly 20 dB gap

The published fleet floor (about 18 to 32 ug/sqrt(Hz), from -75 to -70 dB) is lower than the datasheet
densities (65 to 180 ug/sqrt(Hz) typical, up to 300). DERIVED: 180 vs 18 ug/sqrt(Hz) is a factor of
10, about 20 dB; 70 vs 18 is about 12 dB; 180 vs 32 is about 15 dB.

The research files cannot reconcile them. Candidate explanations, none verified: the datasheet figures
are for specific chips at +/-2 to +/-8 g in particular modes; the MyShake phones are mixed models; the
PSD estimation methods differ; the dB reference is not restated in Kumar 2025.

**This matters** because the detection-limit argument in `DESIGN.md` section 2 uses 70-300 ug/sqrt(Hz).
If the true floor is near 20 ug/sqrt(Hz), detection of short buildings is easier by a large factor in
power; if it is near the datasheet value, it is not. **Our own noise-floor measurements (protocol M2,
`docs/validation_protocol.md`) must settle this.** Until then simulator results use both values and
say which.

Not found: a peer-reviewed measured noise-density spectrum in ug/sqrt(Hz) for a named modern phone
(an Allan-variance snippet for a Xiaomi Mi8 was seen but not read; NOT VERIFIED).

---

## (c) Ground-truth buildings

Test type: amb = ambient, forced = shaker, EQ = earthquake-level. NOT VERIFIED means the value was
not in the pages read.

### c-1 Instrumented buildings

| # | Building, city | Storeys | Height (m) | System | f1 (Hz) | Torsion (Hz) | Damping | Test type, year | Citation |
|---|---|---|---|---|---|---|---|---|---|
| 1 | Broad Center (Caltech), Pasadena CA | 3 plus 2 basements | NOT VERIFIED | Steel, stiff braced frame, 2002 | EW 2.67, NS 2.43 (preliminary, 14 days of data) | 3.65 (preliminary) | NOT VERIFIED | amb, 2003 | Clinton et al. 2006, BSSA 96(1), 237-257, https://doi.org/10.1785/0120050052 |
| 2 | Albina Yard, Portland OR | 4 | 15.39 | Mass timber, glulam and CLT, plywood shear walls, 2017 | NS 2.86, EW 4.20 (SSI) | 4.29 | EW f1: 1.38% (EFDD) vs 5.66% (SSI) | amb, Jan 2017, about 2 h on a weekend | Mugabo et al. 2019, https://doi.org/10.3389/fbuil.2019.00086 |
| 3 | 9-storey RC dwelling (1939), Grenoble | 9 | NOT VERIFIED | Poorly reinforced RC frames with shear walls, no seismic code | T 2.28, L 2.73 (FDD); demolition test 2.27, 2.75 | 4.74 | 4% (random decrement, demolition test) | amb 15 min at 200 Hz plus small demolition excitation; year NOT VERIFIED | Michel, Gueguen, Bard, arXiv:0710.1210 (preprint; final volume/pages NOT VERIFIED) |
| 4 | Millikan Library, Pasadena CA | 9 plus basement | 43.9 (48.2 from basement) | RC moment frame with RC shear walls, 1967 | Ambient (2-yr mean): EW 1.19, NS 1.72. Forced 2002: EW 1.14, NS 1.67. Forced 1968: EW 1.45, NS 1.90 | amb 2.46; forced 2.38 | NOT VERIFIED | amb 2002-2004; forced 2002 | Clinton et al. 2006 |
| 5 | Grenoble City Hall | 13 | 52 | RC, two shear-wall cores, 1967 | L 1.16, T 1.22 (Michel 2010 as cited); one-year means L 1.162, T 1.224 | 1.45 (as cited) | RDT mean 1.03% (L), 1.03% (T) | amb, one-year monitoring | Mikael et al. 2013, BSSA 103(1), 236-246, https://doi.org/10.1785/0120120048 |
| 6 | Ophite Tower, Lourdes | 18 | about 59 (DERIVED: 18 x 3.3 m, not stated) | RC shear-wall dwelling, 1972 | L 1.74, T 1.73 | about 2.2 | 0.88% (L), 0.83% (T) | amb, one year | Mikael et al. 2013 |
| 7 | UCLA Factor Building, Los Angeles | 17 | NOT VERIFIED | Steel moment frame | Ambient: NS 0.58-0.60, EW 0.54-0.56. EQ-level (Encino 2003): NS 0.52 | amb 0.80-0.81; EQ 0.7 | NOT VERIFIED | amb and EQ, 2002-2003 | Kohler, Davis, Safak 2005, Earthquake Spectra 21(3), 715-736, https://doi.org/10.1193/1.1946707 |
| 8 | Belledonne and Mont-Blanc towers (Ile Verte), Grenoble | 30 each | 100 | RC, continuous walls, 1963-67 | Belledonne T 0.67, L 0.89; Mont-Blanc T 0.65, L 0.84 | about 1 | Belledonne 1.09% (L), 0.67% (T); Mont-Blanc 0.86% (L), 0.59% (T) | amb, one month; year NOT VERIFIED | Mikael et al. 2013 |
| 9 | Pacific Park Plaza, Emeryville CA | 30 | 95 | RC frame | Recent ambient 0.48 (Celebi, as cited); phones 0.47. Ambient range 0.48-0.54; forced 1985: 0.58; Loma Prieta 1989 EQ: 0.38 | NOT VERIFIED | NOT VERIFIED | amb and EQ; all second-hand via Kumar 2025 | Kumar et al. 2025 (Celebi primary NOT located) |
| 10 | Millennium Tower, San Francisco | 58 (table) vs 56 (text) | 197 | RC frame | 0.26 and 0.30; another peak at 0.43 | NOT VERIFIED | 0.7% (X), 0.8% (Y) | amb (wind), 2024 | Kumar et al. 2025 |

Span: 3 to 58 storeys. Low-rise (3-6 storeys): only rows 1 and 2.

### c-2 Earthquake-level phone values (not ground truth)

From Patel et al. 2023, all EQ-level, one phone each.

| Location | Storeys | f1 (Hz) | Event |
|---|---|---|---|
| Berkeley CA (hotel) | 8 | 2.08 | Mw 4.4 |
| Carson CA (condo) | 14 | 1.42 | Mw 4.28 |
| Searles Valley CA (apartments) | 18 | 0.82 | Mw 5.37 |
| Carson CA (apartments) | 3 | 2.71 | Mw 4.28 |
| Tsukuba, Japan (apartments) | 5 | 3.05 | Mwr 4.7 |
| Ferndale CA (hotel) | 3 | 4.26 | Mw 6.4 |
| Santa Rosa CA (L-shaped apartments) | 5 | 4.85; 4.62 (Mw 5.06); 4.50 (Mw 3.57) | Ml 4.29 |

NOT VERIFIED: MIT Green Building (Cambridge MA) 0.75 (NS) and 0.67 (EW) Hz, from a search-result
summary only. The NIST IR 4511 report was opened and contains no frequencies.

---

## (d) Ambient amplitude and ground noise

### Building amplitudes

| Item | Value | Source |
|---|---|---|
| Millikan roof, ambient | Daytime about 10 times night level; in a Santa Ana windstorm mode amplitudes rose about 10 times and E-W f1 dropped about 3%. Absolute ambient RMS NOT VERIFIED | Clinton 2006 |
| Millikan roof in earthquakes (for scale) | 2.8 cm/s^2 (Anza M6.1), 5 (Yorba Linda M4.8), 7 (Beverly Hills M4.2), 18 (Big Bear M5.4); 8 cm/s^2 at the N-S fundamental with full shaker weights | Clinton 2006 |
| Millikan strong shaking | 49 cm/s^2 (Lytle Creek 1970); 306-341 cm/s^2 (San Fernando 1971) | Clinton 2006 |
| Pedestrian bridge, ambient (not a building) | peak below 0.005 g | Feng 2015 |
| Millikan forced displacement | peak about 0.05 cm at 1.7 Hz (shaker) | Kong 2018 |
| Phone-detectable building signal | structural PSD peaks often above -60 dB vs phone noise near -70 dB in 54-197 m buildings under wind. DERIVED: -60 dB = 1.0e-3 m/s^2/sqrt(Hz) | Kumar 2025 |
| Shorter buildings | many phone measurements rejected for low SNR | Kumar 2025 |

NOT VERIFIED, do not use: a 167 m office tower at about 2 mg RMS with a proposed 5 mg limit; a Boston
tower median wind-event RMS of about 0.46 mg; occupant-survey RMS 1-2 mg average and 2-5 mg storm
peaks. These were search snippets. No verified absolute ambient RMS for typical, non-storm conditions
was obtained. The simulator therefore treats excitation level as a scenario parameter.

### Ground noise

Peterson (1993) NHNM and NLNM, USGS OFR 93-322, https://pubs.usgs.gov/publication/ofr93322. The USGS
PDF returned HTTP 403. Values below come from the model tables in the ObsPy 1.5.1 source distribution
(secondary copy, not cross-checked against the report). Units dB re 1 (m/s^2)^2/Hz.

| Period / frequency | NLNM (dB) | NHNM (dB) | NHNM amplitude, DERIVED |
|---|---|---|---|
| 0.1 s / 10 Hz | -168.0 | -91.5 | 2.7 ug/sqrt(Hz) |
| 0.2 s / 5 Hz | -166.7 | -96.7 | 1.5 ug/sqrt(Hz) |
| 0.5 s / 2 Hz | -167.5 | -115.2 | 0.18 ug/sqrt(Hz) |
| 1 s / 1 Hz | -166.3 | -116.8 | 0.15 ug/sqrt(Hz) |
| 2 s / 0.5 Hz | -152.8 | -107.0 | |
| 5 s / 0.2 Hz | -142.2 | -98.1 | |

Urban measurements:

- Barcelona seismic stations, 2-20 Hz, business hours: most stations -90 to -95 dB; louder -80 to -90
  dB; quiet -105 to -110 dB; day-night difference about 15 dB on average, over 20 dB at some sites.
  Diaz, Ruiz, Jara (2021), Solid Earth 12, 725-739, https://doi.org/10.5194/se-12-725-2021.
- Central London, 5 broadband stations, summer 2015: traffic noise at periods below 0.4 s about 20 dB
  above the new high-noise model. Green, Bastow, Dashwood, Nippress (2017), Seismol. Res. Lett. 88(1),
  113-124, https://doi.org/10.1785/0220160128. Median PSD tables in the supplement not read.
- DERIVED inference, not stated by any source: NHNM at 10 Hz (-91.5 dB) plus 20 dB is about -71.5 dB,
  in the range of phone noise (-70 to -75 dB), so urban traffic noise at several Hz to 10 Hz can
  approach phone self-noise.

---

## (e) Frequency variability and post-earthquake drops

From Clinton et al. 2006 unless stated.

| Effect | Numbers | Building |
|---|---|---|
| Forced amplitude | 1.11 vs 1.14 Hz between full and reduced shaker weights: 2.5%, force factor 2.23 | Millikan EW |
| Strong motion | frequencies drop about 20% temporarily; Big Bear 2003 (M5.4): EW 1.06 Hz, 11% below ambient 1.19 | Millikan |
| Small EQ | Encino: 0.52 vs 0.59 Hz NS (about 12%); recovery within 5 minutes after Yorba Linda; Encino recovery after about 6 hours (Kohler 2005) | Factor |
| Wind | Santa Ana storm: EW f1 down about 3% | Millikan |
| Rain | over 100 mm in 2 days: about +3% EW and torsion, decay over about 10 days | Millikan |
| Temperature (diurnal) | at least 1% daily swing in hot weather; frequency rises with daytime temperature | Millikan |
| Season | no long-term seasonal trend in 2.5 years | Millikan |
| Seasonal range | EW 2.55 (mid-Oct) to 2.72 Hz (early Feb), 6.5%; NS 2.40 to 2.52 Hz, 4.9% | Broad Center |
| Two-year daily means | EW 1.155-1.215 (5.1%); NS 1.71-1.74 (1.7%); torsion 2.44-2.55 (4.4%) | Millikan |
| Occupancy | partitions added 2004: gradual 4% rise in EW f1 (about 8% stiffness) | Millikan |
| Long-term CV of f1 | about 0.4% (City Hall), 1.0% (Ophite), about 0.3% (Ile Verte, one month); zeta CV 9-14%; changes under 0.5% cannot be tied to damage | Mikael 2013 |
| Factor CV | about 1-2% for most modes (abstract-level only, NOT VERIFIED beyond that) | Nayeri et al. 2008, https://doi.org/10.1088/0964-1726/17/2/025006 |
| Post-earthquake drop | Millikan EW: permanent 16.6% drop (to 1.21 Hz) after the 1970 and 1971 events; 2002 forced EW f1 is 22% below 1968; other strong events usually under 2.5%; Pacific Park Plaza 1989 EQ 0.38 Hz vs ambient 0.48-0.54 | Clinton 2006; Kumar 2025 |
| Phone repeat | 4.85 to 4.50 Hz over 4 months (about 7%), three different earthquakes | Patel 2023 |
| Shake table | brace disengagement: f1 down by up to 22% | Patel 2023 |

Consequence for change detection: a few percent of frequency change can be weather, amplitude or
occupancy. Detection thresholds must be set against these numbers, not against zero.

---

## (f) Period formulas and period-height relations

### f-1 Code formulas

| Code | Formula | Coefficients | Status |
|---|---|---|---|
| ASCE 7-16, Ta = Ct hn^x (hn in ft) | Table 12.8-2 | Steel MRF 0.028/0.80; concrete MRF 0.016/0.90; steel EBF 0.030/0.75; steel BRBF 0.030/0.75; all other 0.020/0.75 | Secondary reproduction (Bentley RAM help); standard not retrieved |
| ASCE 7-05, hn in m | Table 12.8-2 printed metric | Steel MRF 0.0724/0.8; concrete MRF 0.0466/0.9; EBF 0.0731/0.75; other 0.0488/0.75 | Read in ASCE 7-05 excerpt. Metric column of 7-16 and 7-22 NOT VERIFIED. Do not use 0.068/0.044/0.070/0.055 from the iisee page (edition unstated, disagrees) |
| ASCE 7, Ta = 0.1 N | Moment frames up to 12 storeys, storey height at least 10 ft (3 m) | | ASCE 7-05 text; 7-16 conditions NOT VERIFIED |
| ASCE 7-05 shear walls | Ta = (0.0019/sqrt(Cw)) hn; Cw = (100/AB) sum[(hn/hi)^2 Ai / (1 + 0.83 (hi/Di)^2)] | | Whether retained in 7-16 / 7-22 NOT VERIFIED |
| ASCE 7-16 Cu | Tmax = Cu Ta: SD1 >= 0.4: 1.4; 0.3: 1.4; 0.2: 1.5; 0.15: 1.6; <= 0.1: 1.7 | | ideCAD help page |
| Eurocode 8 (EN 1998-1:2004) 4.3.3.2.2, up to 40 m | T1 = Ct H^(3/4), H in m | Ct 0.085 steel MRF; 0.075 concrete MRF and steel EBF; 0.050 others. Shear walls: Ct = 0.075/sqrt(Ac), Ac = sum[Ai (0.2 + (lwi/H)^2)], lwi/H <= 0.9 | Eq. 4.9 not transcribed; national annexes not checked |

### f-2 Measured period-height relations, verified in a retrieved primary document

| Study | Data | Formula | Scatter |
|---|---|---|---|
| Goel and Chopra 1997, RC MRF. J. Struct. Eng. 123(11):1454-1461, DOI 10.1061/(ASCE)0733-9445(1997)123:11(1454); data in UCB/EERC-97/14 | Earthquake records, 27 buildings, H in ft | Best fit T = 0.017 H^0.92; constrained TR = 0.018 H^0.90; recommended lower bound (PGA >= 0.15 g) TL = 0.016 H^0.90; upper TU = 0.023 H^0.90 | se = 0.209 (log space; base not stated) |
| Goel and Chopra 1997, steel MRF | Same database, 42 buildings, H in ft | TR = 0.035 H^0.80; TL = 0.028 H^0.80; TU = 0.045 H^0.80 | se = 0.233 |
| Goel and Chopra 1998, RC shear walls. J. Struct. Eng. 124(4):426-433, DOI 10.1061/(ASCE)0733-9445(1998)124:4(426) | 9 buildings, 17 points | T = C H / sqrt(Ae); C = 0.0023 best fit, 0.0018 lower; 0.0026 and 0.0019 for PGA >= 0.15 g | se = 0.143; unit of H not separately confirmed |
| Michel, Gueguen, Lestuzzi, Bard 2010. Bull. Earthquake Eng. 8(6):1295-1307, DOI 10.1007/s10518-010-9185-7 | Ambient; 173 RC building periods, Grenoble and Nice | T0 = 0.013 H = 0.039 N (H in m, presumed) | sigma* = 0.08 s (H), 0.09 s (N). EC8 with Ct = 0.05 exceeds measured periods by 60 to 100% |
| Chiauzzi et al. 2012, 15 WCEE paper 3033 | Ambient (HVSR), RC buildings, British Columbia, Canada; H in m | T = 0.037 H^0.76 | R = 0.88; number of buildings NOT VERIFIED |
| Ditommaso, Vona, Gallipoli, Mucciarelli 2013. NHESS 13:1903-1912, DOI 10.5194/nhess-13-1903-2013 | Ambient after L'Aquila 2009; 68 RC buildings, 11-27 m | T = alpha H. alpha: DL0-1 0.016 (0.014-0.018); DL2 0.026 (0.023-0.028); DL3 0.028 (0.024-0.033). DERIVED ratio DL2-3 / DL0-1 = 1.6 | 95% bounds only |

### f-3 Second-hand (read in a citing paper; primary not read)

| Study | What the citing paper reports | Read in |
|---|---|---|
| Guler, Yuksel, Kocak 2008 | Infilled RC frames, ambient: Ct = 0.026, beta = 0.9, 6 buildings; T1 = 1.75 T0 | Michel 2010 |
| Oliveira and Navarro 2010 | Review of ambient studies uses beta = 1 with Ct 0.012-0.020, Mexico City 0.035 | Michel 2010 |
| Hong and Hwang 2000 | 21 Taiwan RC buildings, periods below codes and below Goel and Chopra; formula not seen | Chiauzzi 2012, Michel 2010 |
| AIJ 2000 via Tamura lecture notes | At tip drift 2e-5: T = 0.018 H (RC), T = 0.024 H (steel), H in m; Tm = 0.80 Td. Indicative (equations garbled) | vibrationdata.com lecture |

### f-4 NOT VERIFIED

Gallipoli et al. 2010 (Bull. Earthquake Eng. 8:593-607, DOI 10.1007/s10518-009-9133-6; 244 RC buildings,
1-20 floors, formula and scatter not seen); Kwon and Kim 2010 (not located); Lagomarsino 1993 period
formula; Crowley and Pinho 2010 review (paywalled). Risk-UE (Lagomarsino and Giovinazzi 2006) uses
Ct = 0.065 and beta = 0.9 for RC, as stated by Michel 2010.

### f-5 Ambient versus strong-motion period

| Quantity | Value | Basis |
|---|---|---|
| Frequency drop from amplitude (PGA 0.1 to 1 m/s^2) | up to 35% (period ratio up to 1.54, DERIVED) | Michel 2010 citing Dunand 2006 |
| Frequency drop before collapse | about 60% (period ratio about 2.5, DERIVED) | Michel 2010 citing Calvi 2006 |
| Risk-UE yield period vs ambient, French RC | 240-280% elongation | Michel 2010 |
| Ambient to "elastic code" period | T1 = 1.75 T0 | Guler 2008 via Michel (second-hand) |
| Damage level, same method | alpha ratio 1.6 (DERIVED) | Ditommaso 2013 |

No single published ambient-to-strong-motion ratio was found.

---

## (g) Hazus 6.1 tables used

Source: FEMA Hazus Earthquake Model Technical Manual, Hazus 6.1, July 2024.
https://www.fema.gov/sites/default/files/documents/fema_hazus-earthquake-model-technical-manual-6-1.pdf.
Editions 4.2 SP3, 5.1 and MR4 were not retrieved; no claim is made about their parameters.

The full parameter tables (21 building types by High, Moderate, Low and Pre-Code) are in
`docs/research/codes_and_fragility.md` section 3. They are not reproduced here.

| Table (printed pages) | Content |
|---|---|
| 5-1 (5-6, 5-7) | Building types, stories, typical height |
| 5-6 (5-26) | Changes for Very High-Code and Severe-Code: capacity x1.5 and x2.0; structural fragility medians x1.15 and x1.25, beta unchanged |
| 5-7 (5-27) | Design strength Cs |
| 5-8 (5-28) | Te, alpha1, alpha2, gamma, lambda (independent of design level) |
| 5-9 (5-29) | Ductility mu |
| 5-12 to 5-15 (5-33 to 5-36) | Capacity curves: High, Moderate, Low, Pre-Code |
| 5-16 (5-41) | Typical low-rise drift ratios |
| 5-19 to 5-22 (5-45 to 5-51) | Structural fragility parameters: High, Moderate, Low, Pre-Code |
| 5-42 (5-75, 5-76) | Degradation factor kappa by duration |
| 11-2 (11-7, 11-8) | Structural repair cost ratios by occupancy |

Transcription caveats: tables were extracted from the PDF text layer and spot-checked; Table 5-20 C2M
Slight beta prints as 0.821; rows flagged (*) are types not permitted by current codes at that design
level; Pre-Code S1M and S1H long-duration kappa prints 0.20. Not transcribed: Severe-Code and
Very High-Code tables (5-10, 5-11, 5-17, 5-18), nonstructural repair ratios (11-3, 11-4), and types
beyond the 21 listed.

---

## (h) Damping statistics

| Item | Value | Source |
|---|---|---|
| Earthquake-amplitude dataset | 1335 recorded responses, 154 buildings, 117 earthquakes, 1038 reliable first-mode damping points (ATC-72 had 86) | Miranda and Cruz, 2020 PEER Annual Meeting slides, https://peer.berkeley.edu/sites/default/files/e_miranda_peer.pdf |
| Tall buildings | Above 150 m all inferred damping is below 2.5%, except one building with sloshing dampers | same |
| Trend | Damping falls with height; little amplitude dependence beyond very small drift; no significant steel/RC difference; rises about linearly with frequency; Rayleigh mass-proportional damping not supported | same |
| Design baselines for wind serviceability | about 1% (steel), 2% (concrete), US, ASCE 7-10 commentary; ISO 1997: 1% and 1.5% | same, slide 8 |
| Very low amplitude, Japan | zeta1 = 0.0143 f1 (RC, r = 0.89); 0.0231 f1 (SRC, r = 0.32); 0.013 f1 (steel, r = 0.65); f1 in Hz, zeta as a fraction | Tamura lecture citing AIJ 2000 (equations partly garbled) |
| Ambient, measured | 0.59-1.09% (Ile Verte towers); 1.03% (City Hall); 0.83-0.88% (Ophite); 0.7-0.8% (Millennium Tower, half-power); 4% (Grenoble 9-storey, demolition test); EW f1 1.38% (EFDD) vs 5.66% (SSI) (Albina Yard) | Mikael 2013; Kumar 2025; Michel; Mugabo 2019 |
| Scatter | zeta CV 9-14% (towers), 12-14% (City Hall) over time | Mikael 2013 |

Method spread matters: the same Albina Yard mode gives 1.38% or 5.66% depending on the estimator.

NOT VERIFIED: Cruz and Miranda 2017 (J. Struct. Eng. 143(1):04016144, DOI
10.1061/(ASCE)ST.1943-541X.0001628) height-damping equations and scatter (the slide equations are
images); Satake et al. 2003 regressions (J. Struct. Eng. 129(4):470-477; the secondary "98.9/H" was not
retrieved); Jeary 1986 and Lagomarsino 1993 full coefficients; Bernal et al. 2015; Hazus elastic
damping BE by building type (equations are images; no per-type table in the text read); Millikan
damping ratios; any ambient-to-earthquake damping ratio.

---

## (i) Open items

Checklist of everything still NOT VERIFIED. Close an item only by reading the primary source and
recording where.

**Claims and prior art**
- [ ] Any source naming insurance or insurers as an application (none in Kong 2016, Kong 2018, Patel 2023, Kumar 2025)
- [ ] Further smartphone-in-building papers (Ozer and Feng material, other groups, Sarmadi review)
- [ ] Kong 2016 numeric noise floor (figure only); Kong 2016 article number
- [ ] Kong 2018 noise-level units and per-phone chip mapping
- [ ] Kumar 2025: SkyDeck zeta unit; Millennium Tower 58 vs 56 floors; dB reference of noise values

**Noise and amplitude**
- [ ] The roughly 20 dB gap between datasheet and published phone noise (our own measurements, protocol M2)
- [ ] Measured noise density in ug/sqrt(Hz) for a named modern phone
- [ ] ICM-42688-P full datasheet; BMI160 and BMI270 table values against the PDFs
- [ ] Absolute ambient RMS on upper floors in typical conditions; Millikan absolute ambient RMS
- [ ] Peterson report PDF cross-check; London median PSD table

**Ground truth**
- [ ] Heights of Broad Center, Grenoble 9-storey, Factor Building
- [ ] Ophite Tower height (derived, not stated)
- [ ] Celebi primary paper for Pacific Park Plaza; Michel 2010 City Hall primary
- [ ] Michel et al. 2008 final volume and pages; Mikael 2013 Ile Verte test year and BSSA page check
- [ ] Millikan damping; Bradford et al. 2004; Nayeri et al. 2008 full text; MIT Green Building

**Codes and period relations**
- [ ] ASCE 7-16 / 7-22 metric Ct; 7-16 conditions for Ta = 0.1 N; Cw shear-wall equation status
- [ ] EC8 Eq. 4.9 and national annexes
- [ ] Gallipoli 2010, Kwon and Kim 2010, Lagomarsino 1993, Crowley and Pinho 2010 formulas; Guler 2008 and Hong and Hwang 2000 primaries
- [ ] Chiauzzi 2012 sample size; Goel and Chopra 1998 unit of H and log base of se

**Hazus and damping**
- [ ] Hazus editions 4.2 SP3, 5.1, MR4; Hazus elastic damping BE by type
- [ ] Cruz and Miranda 2017 equations; Satake 2003; Jeary and Lagomarsino coefficients; Bernal 2015

**Licences and datasets** (details in `docs/licences.md`)
- [ ] GEM global exposure model licence file
- [ ] EMSR648 vector schema and licence; DesignSafe PRJ-3824 and PRJ-5797 contents and licence; Da.D.O. licence, coverage and storeys field; Liu Zenodo zip contents
- [ ] Overture buildings release version
