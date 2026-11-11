# Code period formulas, measured period relations, fragility parameters, damping, taxonomy/licences and damage datasets

Compiled 2026-11-11. Purpose: reference parameters for mapping a building's measured fundamental period and damping to seismic fragility curves.

Rules used in this file:
- Every number below was read in a page, PDF or file that was actually retrieved. Where a source could not be retrieved or its equation could not be read, the item is marked NOT VERIFIED with what was tried.
- Where a value is derived by simple arithmetic from verified numbers, it is labelled "derived".
- Source files read as PDF were text-extracted and, where equations were images, the page was rendered and read visually. Table values for Hazus were extracted programmatically from the PDF text layer and cross-checked on spot rows against the printed layout.

---

## 1. Code period formulas

### 1.1 ASCE 7, approximate period Ta = Ct * hn^x (Eq. 12.8-7), Table 12.8-2

hn = height above the base to the highest level of the structure, in ft for the Ct values labelled "feet" below; Ta in seconds.

**ASCE 7-16 values (feet).** Source: Bentley RAM Structural System help page that reproduces Table 12.8-2 of ASCE 7-16 (page states "ASCE 7-16", hn "given in feet"). URL: https://docs.bentley.com/LiveContent/web/RAM%20Structural%20System%20Help-v4/en/GUID-7C0568C6-D473-4EF0-B1A3-25C2CC31A10B.html (secondary reproduction of Table 12.8-2; the standard itself was not retrieved).

| Lateral system | Ct (hn in ft) | x |
|---|---|---|
| Steel moment-resisting frame | 0.028 | 0.80 |
| Concrete moment-resisting frame | 0.016 | 0.90 |
| Steel eccentrically braced frames (Table 12.2-1 lines B1 or D1) | 0.030 | 0.75 |
| Steel buckling-restrained braced frames | 0.030 | 0.75 |
| All other structural systems | 0.020 | 0.75 |

**Metres.** The metric Ct values below were read in the printed table of ASCE 7-05 (Table 12.8-2, page 129 of the standard, footnote "a Metric equivalents are shown in parentheses"). Source: excerpt of ASCE 7-05 Chapter 12 (pages 129-130), http://www.ce.memphis.edu/7119/notes2/asce003c12_p119-142.pdf . The ASCE 7-05 table has no separate BRBF row.

| Structure type (ASCE 7-05, Table 12.8-2) | Ct, hn in ft | Ct, hn in m (printed) | x |
|---|---|---|---|
| Steel moment-resisting frames | 0.028 | 0.0724 | 0.8 |
| Concrete moment-resisting frames | 0.016 | 0.0466 | 0.9 |
| Eccentrically braced steel frames | 0.03 | 0.0731 | 0.75 |
| All other structural systems | 0.02 | 0.0488 | 0.75 |

Cross-checks:
- Derived: Ct_m = Ct_ft x 3.28084^x gives 0.0724, 0.0466, 0.0731, 0.0488, matching the printed ASCE 7-05 values.
- The ACI 133 Turkey 2023 dataset (section 6) header names a column "T_1 [0.0466H^0.9]" with H in metres, consistent with the concrete-frame metric value.
- NOT VERIFIED: the metric column of Table 12.8-2 in ASCE 7-16 or ASCE 7-22 (not seen; the ASCE 7-16 page above gives feet only). The ASCE 7-22 table itself was not retrieved.
- A page at https://iisee.kenken.go.jp/net/seismic_design_code/usa/table5_usa.html lists "Ct (hn in m)" as 0.068 / 0.044 / 0.070 / 0.055 for the same four rows. It does not state the edition and its metric values disagree with the ASCE 7-05 printed values. Do not use them.

**Alternative for moment frames (Eq. 12.8-8), ASCE 7-05 text:** Ta = 0.1 N, N = number of stories; permitted for structures not exceeding 12 stories where the seismic force-resisting system consists entirely of concrete or steel moment-resisting frames and the story height is at least 10 ft (3 m). The ASCE 7-16 page above shows Ta = 0.1N but its conditions were not stated there (7-16 conditions NOT VERIFIED).

**Shear-wall alternative (ASCE 7-05 Eq. 12.8-9, 12.8-10),** for masonry or concrete shear wall structures (read from the rendered page, ASCE 7-05 p. 130):
- Ta = (0.0019 / sqrt(Cw)) * hn
- Cw = (100 / AB) * sum over i=1..x of [ (hn/hi)^2 * Ai / (1 + 0.83 (hi/Di)^2) ]
- AB = base area (ft^2); Ai = web area of shear wall i (ft^2); Di = length of wall i (ft); hi = height of wall i (ft); x = number of walls effective in the direction considered.
- NOT VERIFIED: whether these equations are still in ASCE 7-16 / 7-22 in this form (Bentley's ASCE 7-16 page says its Eq. 12.8-9 for masonry or concrete shear wall structures is "not implemented" and does not print it).

**Upper limit coefficient Cu (Table 12.8-1), ASCE 7-16 per ideCAD help page** https://help.idecad.com/ideCAD/12-8-2-determination-of-the-building-s-fundamental : SD1 >= 0.4: Cu 1.4; 0.3: 1.4; 0.2: 1.5; 0.15: 1.6; <= 0.1: 1.7 (Tmax = Cu * Ta).

### 1.2 Eurocode 8 (EN 1998-1:2004), clause 4.3.3.2.2

Source: text of EN 1998-1:2004 (with corrigendum markers AC1), PDF page 59 of the retrieved file = printed page 57; equation block read from the rendered page. URL of copy: https://www.phd.eng.br/wp-content/uploads/2015/02/en.1998.1.2004.pdf

- Applicability: 4.3.3.2.2(3) "For buildings with heights of up to 40 m".
- Eq. (4.6): T1 = Ct * H^(3/4), T1 in s, H = building height in m from the foundation or top of a rigid basement.
- Ct = 0.085 for moment resistant space steel frames; 0.075 for moment resistant space concrete frames and for eccentrically braced steel frames; 0.050 for all other structures.
- 4.3.3.2.2(4) alternative for structures with concrete or masonry shear walls: Ct = 0.075 / sqrt(Ac) (Eq. 4.7), with Ac = sum[ Ai * (0.2 + (lwi/H)^2) ] (Eq. 4.8), Ac = total effective area of shear walls in the first storey (m^2), Ai = effective cross-section area of wall i in the direction considered in the first storey (m^2), lwi = length of wall i in the first storey parallel to the applied forces (m), with the restriction lwi/H <= 0.9.
- 4.3.3.2.2(5) alternative: T1 from Eq. (4.9) based on the lateral elastic displacement d of the top of the building under gravity loads applied horizontally (the equation itself is not reproduced here; clause present on the next page of the file).
- National annexes: not checked (the clause as printed carries no NDP).

---

## 2. Empirical period-height relations from measurements

Notation: T in s; H in the units stated; N = number of storeys. "Ambient" = ambient vibration (very low amplitude). "Earthquake" = periods identified from recorded building responses during earthquakes.

### 2.1 Verified in a retrieved primary document

| # | Study | Data and region | Formula | Scatter, as reported | Citation |
|---|---|---|---|---|---|
| 1 | Goel and Chopra 1997, RC moment-resisting frames | Earthquake records, 8 California earthquakes 1971-1994; 27 RC MRF buildings, 37 data points; H in ft | Best fit (unconstrained) T = 0.017 H^0.92; best-fit minus 1 sigma TL = 0.014 H^0.92. Constrained beta = 0.90: TR = 0.018 H^0.90, TL = 0.015 H^0.90. Recommended for buildings shaken at PGA >= 0.15g: TL = 0.016 H^0.90 (Eq. 14); upper limit TU = 0.023 H^0.90 (Eq. 15); rational-analysis period not to exceed 1.4 TL. | se = 0.209 (unconstrained and constrained 0.90) of the log-space fit; se = 0.229 for beta 0.75; 0.214 for beta 1 (Table 3). Log base not stated in the extracted text. | Goel, R.K., Chopra, A.K. (1997) J. Struct. Eng. 123(11):1454-1461, DOI 10.1061/(ASCE)0733-9445(1997)123:11(1454) (DOI seen in a search-result URL; the journal page returned HTTP 403). Full data and regressions read in report UCB/EERC-97/14, Dec 1997, Tables 3-4 and Eqs. 14-17: https://nehrpsearch.nist.gov/static/files/NSF/PB99106106.pdf |
| 2 | Goel and Chopra 1997, steel moment-resisting frames | Earthquake records, same database; 42 steel MRF buildings, 53 data points; H in ft | Unconstrained TR = 0.035 H^0.805, TL = 0.027 H^0.805; constrained beta = 0.80: TR = 0.035 H^0.80, TL = 0.028 H^0.80. Recommended TL = 0.028 H^0.80 (Eq. 16); TU = 0.045 H^0.80 (Eq. 17); rational period not to exceed 1.6 TL. | se = 0.233 (Table 4); 0.237 for beta 0.75; 0.277 for beta 1.0 | as above (EERC-97/14, Table 4) |
| 3 | Goel and Chopra 1998, RC shear-wall buildings | Earthquake records, same California database; 9 concrete shear-wall buildings, 17 data points | T = C * H / sqrt(Ae) form (Eq. 15 of the report; Ae = equivalent shear area as a percent of building plan area, built from wall areas and lengths, reproduced as Eq. 3.2 in Michel et al. 2010). Best fit C = 0.0023, best-fit minus 1 sigma C = 0.0018; for PGA >= 0.15g buildings: C = 0.0026 (best fit) and 0.0019 (lower). Unit of H (ft) is the report's working unit; not separately confirmed for this equation. | se = 0.143 for this formula versus 0.546 for UBC-97 formulas (Eqs. 1 to 3 of the report). Rational period not to exceed 1.4 TL. | Goel, R.K., Chopra, A.K. (1998) J. Struct. Eng. 124(4):426-433, DOI 10.1061/(ASCE)0733-9445(1998)124:4(426) (DOI from a search-result URL; Cal Poly full text blocked). Numbers read in EERC-97/14 Part II, Results of Regression Analysis (PDF page 70-72 of the report file) |
| 4 | Michel, Gueguen, Lestuzzi, Bard 2010 | Ambient; RC shear-wall buildings, Grenoble and Nice (France); 173 resonance periods of RC buildings (and 66 of URM) in the study; H presumably in m (0.013 H = 0.039 N implies 3 m per storey) | T0 = 0.013 H = 0.039 N (linear; free-exponent fits gave H^0.98 and N^0.92) | sigma* = 0.08 s (H) and 0.09 s (N); H or N alone explains 85 to 90 percent of the period variance; 95 percent confidence band plotted | Bull. Earthquake Eng. 8(6):1295-1307, DOI 10.1007/s10518-010-9185-7. Read in full text: https://infoscience.epfl.ch/record/155209/files/10518_2010_Article_9185.pdf (the study also finds EC8 with Ct = 0.05 exceeds the experimental periods by 60 to 100 percent) |
| 5 | Chiauzzi, Masi, Mucciarelli, Cassidy, Kutyn, Traber, Ventura, Yao 2012 | Ambient (HVSR), RC buildings, Victoria and Vancouver, British Columbia, Canada; H in m (the paper expresses the code formula with H in metres) | T = 0.037 H^0.76 ("fully elastic condition") | regression coefficient R = 0.88 | 15th World Conference on Earthquake Engineering, 2012, paper 3033: https://www.iitk.ac.in/nicee/wcee/article/WCEE2012_3033.pdf . Number of buildings measured: NOT VERIFIED (not located in the text read). Note: this paper is the Canada study; it is not an Italian study |
| 6 | Ditommaso, Vona, Gallipoli, Mucciarelli 2013 | Ambient measurements after the 6 April 2009 L'Aquila earthquake; 68 RC buildings, heights 11 to 27 m (H in m); periods grouped by EMS-98 damage level | T = alpha * H. alpha: DL0-DL1 0.016 (95 percent interval 0.014 to 0.018); DL2 0.026 (0.023 to 0.028); DL3 0.028 (0.024 to 0.033); DL2-DL3 combined 0.026 (0.024 to 0.028) (Table 3) | 95 percent confidence bounds only; no se given in the text read | Nat. Hazards Earth Syst. Sci. 13:1903-1912, DOI 10.5194/nhess-13-1903-2013 (CC BY 3.0): https://nhess.copernicus.org/articles/13/1903/2013/nhess-13-1903-2013.pdf . Derived: alpha(DL2-3)/alpha(DL0-1) = 0.026/0.016 = 1.6 |

### 2.2 Reported second-hand (read in a retrieved paper that cites the study; primary not read)

| Study | What the citing paper reports | Where read |
|---|---|---|
| Guler, Yuksel, Kocak 2008, J. Earthquake Eng. 12(S2):140-150 (RC, ambient, Turkey) | Infilled RC moment frames, ambient: Ct = 0.026 with beta = 0.9, from 6 buildings; they suggest T1 = 1.75 T0 (f1 = 0.57 f0) by fitting UBC-97 | Michel et al. 2010, section 3.3 |
| Oliveira and Navarro 2010, Bull. Earthquake Eng. 8(3):609-642 (Portugal RC, ambient plus numerical) | Their review of ambient studies (Mexico, Chile, Spain, Venezuela, Ethiopia, Japan, Italy) uses a linear relation (beta = 1) with Ct between 0.012 and 0.020, except Mexico City (0.035). Their own Portuguese formula was not seen | Michel et al. 2010, section 3.3 |
| Hong and Hwang 2000, Earthq. Eng. Struct. Dyn. 29:327-337 (Taiwan RC MRF, ambient system identification) | 21 RC buildings; periods lower than codes and than Goel and Chopra 1997; paper concludes that height is the relevant parameter. Formula not seen | Chiauzzi et al. 2012 (item 5) and Michel et al. 2010 |
| Japan full-scale data (AIJ 2000 "Damping in Buildings", via lecture notes by Y. Tamura, Tokyo Polytechnic University) | At tip drift ratio 2e-5: f1 = 1/(0.018 H) for RC buildings and f1 = 1/(0.024 H) for steel buildings (H in m), i.e. T = 0.018 H (RC) and T = 0.024 H (steel), low amplitude. Same lecture: full-scale natural period Tm = 0.80 Td (design period Td) for steel (Satake 1997) and RC (Shioya 1993) buildings | https://www.vibrationdata.com/tutorials_alt/damping_buildings_lecture.pdf (slides 28 to 33; equations partially garbled in text extraction, so treat as indicative) |

### 2.3 NOT VERIFIED (formula or scatter not seen)

- Gallipoli et al. 2010, "Empirical estimates of dynamic parameters on a large set of European buildings", Bull. Earthquake Eng. 8:593-607, DOI 10.1007/s10518-009-9133-6 (DOI read in the reference list of Chiauzzi et al.). From search-result text only: ambient noise, four European countries, 244 RC buildings of 1 to 20 floors, one regression for all countries. Publisher page redirected to a login handshake; earth-prints and CNR repository links returned 403/404. Formula and scatter: NOT VERIFIED. Ditommaso et al. 2013 states that its DL0-DL1 relation is very close to the Italian and European undamaged-building relations of Gallipoli et al. 2009 and 2010.
- Kwon and Kim 2010: not located, nothing read. NOT VERIFIED.
- Lagomarsino 1993 "Forecast models for damping and vibration periods of buildings" (J. Wind Eng. Ind. Aerodyn.): not retrieved. The Tamura lecture lists its damping form as zeta1 = alpha / f1 + beta f1 + gamma (xH/H), coefficients not shown. Its period formula: NOT VERIFIED. (Michel et al. state that Lagomarsino and Giovinazzi 2006, Risk-UE, uses Ct = 0.065 and beta = 0.9 for RC buildings; that is a different paper.)
- Crowley and Pinho 2010 (Earthquake Eng. Struct. Dyn. 39(2), DOI 10.1002/eqe.949 per a search result), a review of period formulas that would have given a consolidated table: paywalled; not read.
- Springer/Wiley/ASCE/MDPI publisher pages for the items above blocked automated retrieval (HTTP 403, login redirect or cookie handshake). Tried: publisher DOI pages, institutional repository PDFs (CNR, Unibas, Polito), a review in Applied Sciences 10(5):1568 and a review in MDPI Eng 7(1):10.

### 2.4 Ratio between ambient-vibration period and strong-motion (or damaged) period

| Quantity | Value | Source and basis |
|---|---|---|
| Frequency drop in the "elastic" domain from non-linearity as amplitude rises (PGA 0.1 to 1 m/s^2) | up to 35 percent (derived period ratio up to 1/0.65 = 1.54) | Michel et al. 2010, citing Dunand et al. 2006 |
| Frequency drop before collapse | about 60 percent limit (derived period ratio about 1/0.40 = 2.5); fundamental frequency moves between the ambient value f0 and 40 percent of it | Michel et al. 2010, citing Calvi et al. 2006 |
| Period elongation implied when comparing Risk-UE yield period with ambient periods (French RC) | 240 to 280 percent (frequency decrease of 60 to 65 percent) | Michel et al. 2010, section 3.3 |
| Ambient period to "elastic code period" | T1 = 1.75 T0 (f1 = 0.57 f0) | Guler et al. 2008, as cited by Michel et al. 2010 (second-hand) |
| Period vs damage level, same ambient method, L'Aquila RC buildings | alpha(DL2-3) / alpha(DL0-1) = 0.026 / 0.016 = 1.6 (derived) | Ditommaso et al. 2013, Table 3 |
| Earthquake-record periods of strongly shaken RC buildings relative to the code formula | lower bound of measured periods is about 1.2 times the code period (PGA >= 0.15g) | Goel and Chopra 1997, EERC-97/14 (comparison against code period, not against ambient) |
| Full-scale measured vs design period, Japan | Tm = 0.80 Td | AIJ 2000 via Tamura lecture (indicative) |

No single published ratio of "ambient period to strong-motion period" was found as one number; the entries above are the only quantities seen.

---

## 3. Hazus earthquake model parameters

**Edition used: FEMA Hazus Earthquake Model Technical Manual, Hazus 6.1, July 2024** (the title page of the retrieved file). URL: https://www.fema.gov/sites/default/files/documents/fema_hazus-earthquake-model-technical-manual-6-1.pdf . This is newer than the editions you named. The Hazus 4.2 SP3, 5.1 and MR4 technical manuals were NOT retrieved (the fema.gov path for the 4.2 manual guessed in the first attempt returned 404; a search found the 5.1 User Guidance and the 6.1 Technical Manual but no 5.1 Technical Manual). Parameters in earlier editions may differ; none are claimed here.

Table map in the 6.1 manual (printed page numbers): Table 5-1 building types (pp. 5-6, 5-7); Table 5-6 changes for Very High-Code/Severe-Code (p. 5-26); Table 5-7 design strength Cs (p. 5-27); Table 5-8 Te, alpha1, alpha2, gamma, lambda (p. 5-28); Table 5-9 ductility mu (p. 5-29); Tables 5-12 to 5-15 capacity curves for High, Moderate, Low and Pre-Code (pp. 5-33 to 5-36); Table 5-16 typical low-rise drift ratios (p. 5-41); Tables 5-19 to 5-22 structural fragility parameters for High, Moderate, Low and Pre-Code (pp. 5-45 to 5-51); Table 5-42 degradation factor k (pp. 5-75, 5-76); Table 11-2 structural repair cost ratios (pp. 11-7, 11-8). The manual also has Severe-Code and Very High-Code levels (Tables 5-10, 5-11, 5-17, 5-18); they are not tabulated here. Per Table 5-6 they scale the High-Code capacity by 2.0 (Severe) and 1.5 (Very High), the structural fragility medians by 1.25 and 1.15 with beta unchanged.

Conventions: Dy, Du in inches; Ay, Au in g; spectral displacement medians in inches; beta is the lognormal standard deviation. Roof height and modal (pushover) height in inches in the fragility tables. "(*)" = the manual flags the type as not permitted by current seismic codes for that design level; for those rows drift ratios are printed as "-" in Tables 5-19 and 5-20. For all four design levels Te, alpha1, alpha2, gamma and lambda are the same (Table 5-8 note: independent of design level). Transcription notes: Table 5-20 lists the C2M Slight beta as 0.821 (printed that way); other columns follow the printed values.

**Selected 21 types.** Not all of W2, S3, S4, S5, PC1, PC2L, PC2H, RM1M, RM2L, RM2H, MH are listed in this file; they are in the same tables.

### 3.1 Parameters by building type and design level

#### 3a. Level-independent building parameters (Table 5-1 and Table 5-8)

| Type | Stories range | Typical stories | Typical height (ft), Tbl 5-1 | Height to roof (ft), Tbl 5-8 | Te (s) | alpha1 (weight) | alpha2 (height) | gamma (yield/design) | lambda (ultimate/yield) |
|---|---|---|---|---|---|---|---|---|---|
| W1 | 1-2 | 1 | 14 | 14 | 0.35 | 0.75 | 0.75 | 1.50 | 3.00 |
| S1L | 1-3 | 2 | 24 | 24 | 0.50 | 0.80 | 0.75 | 1.50 | 3.00 |
| S1M | 4-7 | 5 | 60 | 60 | 1.08 | 0.80 | 0.75 | 1.25 | 3.00 |
| S1H | 8+ | 13 | 156 | 156 | 2.21 | 0.75 | 0.60 | 1.10 | 3.00 |
| S2L | 1-3 | 2 | 24 | 24 | 0.40 | 0.75 | 0.75 | 1.50 | 2.00 |
| S2M | 4-7 | 5 | 60 | 60 | 0.86 | 0.75 | 0.75 | 1.25 | 2.00 |
| S2H | 8+ | 13 | 156 | 156 | 1.77 | 0.65 | 0.60 | 1.10 | 2.00 |
| C1L | 1-3 | 2 | 20 | 20 | 0.40 | 0.80 | 0.75 | 1.50 | 3.00 |
| C1M | 4-7 | 5 | 50 | 50 | 0.75 | 0.80 | 0.75 | 1.25 | 3.00 |
| C1H | 8+ | 12 | 120 | 120 | 1.45 | 0.75 | 0.60 | 1.10 | 3.00 |
| C2L | 1-3 | 2 | 20 | 20 | 0.35 | 0.75 | 0.75 | 1.50 | 2.50 |
| C2M | 4-7 | 5 | 50 | 50 | 0.56 | 0.75 | 0.75 | 1.25 | 2.50 |
| C2H | 8+ | 12 | 120 | 120 | 1.09 | 0.65 | 0.60 | 1.10 | 2.50 |
| C3L | 1-3 | 2 | 20 | 20 | 0.35 | 0.75 | 0.75 | 1.50 | 2.25 |
| C3M | 4-7 | 5 | 50 | 50 | 0.56 | 0.75 | 0.75 | 1.25 | 2.25 |
| C3H | 8+ | 12 | 120 | 120 | 1.09 | 0.65 | 0.60 | 1.10 | 2.25 |
| RM1L | 1-3 | 2 | 20 | 20 | 0.35 | 0.75 | 0.75 | 1.50 | 2.00 |
| RM2M | 4-7 | 5 | 50 | 50 | 0.56 | 0.75 | 0.75 | 1.25 | 2.00 |
| PC2M | 4-7 | 5 | 50 | 50 | 0.56 | 0.75 | 0.75 | 1.25 | 2.00 |
| URML | 1-2 | 1 | 15 | 15 | 0.35 | 0.50 | 0.75 | 1.50 | 2.00 |
| URMM | 3+ | 3 | 35 | 35 | 0.50 | 0.75 | 0.75 | 1.25 | 2.00 |

#### High-Code: Cs, mu, capacity curve, structural fragility, drift ratios

Cs = design strength (fraction of weight, Table 5-7); mu = ductility (Table 5-9). Capacity points Dy (in), Ay (g), Du (in), Au (g) from Table 5-12. Fragility median Sd (in) / beta from Table 5-19. (*) = flagged in the manual as not permitted by current seismic codes.

| Type | Cs | mu | Dy | Ay | Du | Au | Slight med/beta | Moderate med/beta | Extensive med/beta | Complete med/beta | Roof ht (in) | Modal ht (in) | Drift ratio S / M / E / C |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| W1 | 0.2 | 8.0 | 0.48 | 0.400 | 11.51 | 1.200 | 0.50/0.80 | 1.51/0.81 | 5.04/0.85 | 12.60/0.97 | 168 | 126 | 0.0040 / 0.0120 / 0.0400 / 0.1000 |
| S1L | 0.133 | 8.0 | 0.611 | 0.250 | 14.667 | 0.749 | 1.30/0.80 | 2.59/0.76 | 6.48/0.69 | 17.28/0.72 | 288 | 216 | 0.0060 / 0.0120 / 0.0300 / 0.0800 |
| S1M | 0.1 | 5.3 | 1.775 | 0.156 | 28.40 | 0.468 | 2.16/0.65 | 4.32/0.65 | 10.80/0.67 | 28.80/0.74 | 720 | 540 | 0.0040 / 0.0080 / 0.0200 / 0.0533 |
| S1H | 0.067 | 4.0 | 4.657 | 0.098 | 55.884 | 0.293 | 3.37/0.64 | 6.74/0.64 | 16.85/0.65 | 44.93/0.67 | 1,872 | 1,123 | 0.0030 / 0.0060 / 0.0150 / 0.0400 |
| S2L | 0.2 | 8.0 | 0.626 | 0.400 | 10.023 | 0.800 | 1.08/0.81 | 2.16/0.89 | 6.48/0.94 | 17.28/0.83 | 288 | 216 | 0.0050 / 0.0100 / 0.0300 / 0.0800 |
| S2M | 0.2 | 5.3 | 2.426 | 0.333 | 25.876 | 0.667 | 1.80/0.67 | 3.60/0.67 | 10.80/0.68 | 28.80/0.79 | 720 | 540 | 0.0033 / 0.0067 / 0.0200 / 0.0533 |
| S2H | 0.15 | 4.0 | 7.746 | 0.254 | 61.965 | 0.508 | 2.81/0.63 | 5.62/0.63 | 16.85/0.64 | 44.93/0.71 | 1,872 | 1,123 | 0.0025 / 0.0050 / 0.0150 / 0.0400 |
| C1L | 0.133 | 8.0 | 0.391 | 0.250 | 9.387 | 0.749 | 0.90/0.81 | 1.80/0.84 | 5.40/0.86 | 14.40/0.80 | 240 | 180 | 0.0050 / 0.0100 / 0.0300 / 0.0800 |
| C1M | 0.133 | 5.3 | 1.152 | 0.208 | 18.436 | 0.624 | 1.50/0.68 | 3.00/0.67 | 9.00/0.68 | 24.00/0.81 | 600 | 450 | 0.0033 / 0.0067 / 0.0200 / 0.0533 |
| C1H | 0.067 | 4.0 | 2.011 | 0.098 | 24.13 | 0.293 | 2.16/0.66 | 4.32/0.64 | 12.96/0.67 | 34.56/0.78 | 1,440 | 864 | 0.0025 / 0.0050 / 0.0150 / 0.0400 |
| C2L | 0.2 | 8.0 | 0.48 | 0.400 | 9.592 | 1.000 | 0.72/0.82 | 1.80/0.84 | 5.40/0.93 | 14.40/0.92 | 240 | 180 | 0.0040 / 0.0100 / 0.0300 / 0.0800 |
| C2M | 0.2 | 5.3 | 1.038 | 0.333 | 13.841 | 0.833 | 1.20/0.74 | 3.00/0.77 | 9.00/0.68 | 24.00/0.77 | 600 | 450 | 0.0027 / 0.0067 / 0.0200 / 0.0533 |
| C2H | 0.15 | 4.0 | 2.939 | 0.254 | 29.394 | 0.635 | 1.73/0.68 | 4.32/0.65 | 12.96/0.66 | 34.56/0.76 | 1,440 | 864 | 0.0020 / 0.0050 / 0.0150 / 0.0400 |
| C3L (*) | * | * | 0.12 | 0.100 | 1.349 | 0.225 | 0.54/1.09 | 1.08/1.07 | 2.70/1.08 | 6.30/0.91 | - | - | - |
| C3M (*) | * | * | 0.26 | 0.083 | 1.946 | 0.188 | 0.90/0.85 | 1.80/0.83 | 4.50/0.79 | 10.50/0.98 | - | - | - |
| C3H (*) | * | * | 0.735 | 0.063 | 4.134 | 0.143 | 1.30/0.71 | 2.59/0.74 | 6.48/0.90 | 15.12/0.96 | - | - | - |
| RM1L | 0.267 | 8.0 | 0.639 | 0.533 | 10.229 | 1.066 | 0.72/0.84 | 1.44/0.86 | 4.32/0.92 | 12.60/1.01 | 240 | 180 | 0.0040 / 0.0080 / 0.0240 / 0.0700 |
| RM2M | 0.267 | 5.3 | 1.384 | 0.444 | 14.76 | 0.889 | 1.20/0.71 | 2.40/0.79 | 7.20/0.70 | 21.00/0.73 | 600 | 450 | 0.0027 / 0.0053 / 0.0160 / 0.0467 |
| PC2M | 0.2 | 5.3 | 1.038 | 0.333 | 11.073 | 0.667 | 1.20/0.77 | 2.40/0.80 | 7.20/0.70 | 21.00/0.83 | 600 | 450 | 0.0027 / 0.0053 / 0.0160 / 0.0467 |
| URML (*) | * | * | 0.24 | 0.200 | 2.397 | 0.400 | 0.41/1.00 | 0.81/1.05 | 2.03/1.09 | 4.73/1.08 | - | - | - |
| URMM (*) | * | * | 0.272 | 0.111 | 1.812 | 0.222 | 0.63/0.91 | 1.26/0.92 | 3.15/0.87 | 7.35/0.91 | - | - | - |

#### Moderate-Code: Cs, mu, capacity curve, structural fragility, drift ratios

Cs = design strength (fraction of weight, Table 5-7); mu = ductility (Table 5-9). Capacity points Dy (in), Ay (g), Du (in), Au (g) from Table 5-13. Fragility median Sd (in) / beta from Table 5-20. (*) = flagged in the manual as not permitted by current seismic codes.

| Type | Cs | mu | Dy | Ay | Du | Au | Slight med/beta | Moderate med/beta | Extensive med/beta | Complete med/beta | Roof ht (in) | Modal ht (in) | Drift ratio S / M / E / C |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| W1 | 0.15 | 6.0 | 0.36 | 0.300 | 6.475 | 0.900 | 0.50/0.84 | 1.25/0.86 | 3.86/0.89 | 9.45/1.04 | 168 | 126 | 0.0040 / 0.0099 / 0.0306 / 0.0750 |
| S1L | 0.067 | 6.0 | 0.306 | 0.125 | 5.50 | 0.375 | 1.30/0.80 | 2.24/0.76 | 5.08/0.74 | 12.96/0.87 | 288 | 216 | 0.0060 / 0.0104 / 0.0235 / 0.0600 |
| S1M | 0.05 | 4.0 | 0.888 | 0.078 | 10.651 | 0.234 | 2.16/0.65 | 3.74/0.68 | 8.46/0.69 | 21.60/0.87 | 720 | 540 | 0.0040 / 0.0069 / 0.0157 / 0.0400 |
| S1H | 0.033 | 3.0 | 2.329 | 0.049 | 20.957 | 0.147 | 3.37/0.64 | 5.83/0.64 | 13.21/0.71 | 33.70/0.83 | 1,872 | 1,123 | 0.0030 / 0.0052 / 0.0118 / 0.0300 |
| S2L | 0.1 | 6.0 | 0.313 | 0.200 | 3.758 | 0.400 | 1.08/0.93 | 1.87/0.92 | 5.04/0.93 | 12.96/0.93 | 288 | 216 | 0.0050 / 0.0087 / 0.0233 / 0.0600 |
| S2M | 0.1 | 4.0 | 1.213 | 0.167 | 9.704 | 0.333 | 1.80/0.70 | 3.12/0.69 | 8.40/0.69 | 21.60/0.89 | 720 | 540 | 0.0033 / 0.0058 / 0.0156 / 0.0400 |
| S2H | 0.075 | 3.0 | 3.873 | 0.127 | 23.237 | 0.254 | 2.81/0.66 | 4.87/0.64 | 13.10/0.69 | 33.70/0.80 | 1,872 | 1,123 | 0.0025 / 0.0043 / 0.0117 / 0.0300 |
| C1L | 0.067 | 6.0 | 0.196 | 0.125 | 3.52 | 0.375 | 0.90/0.89 | 1.56/0.90 | 4.20/0.90 | 10.80/0.88 | 240 | 180 | 0.0050 / 0.0087 / 0.0233 / 0.0600 |
| C1M | 0.067 | 4.0 | 0.576 | 0.104 | 6.914 | 0.312 | 1.50/0.69 | 2.60/0.69 | 7.00/0.69 | 18.00/0.90 | 600 | 450 | 0.0033 / 0.0058 / 0.0156 / 0.0400 |
| C1H | 0.033 | 3.0 | 1.005 | 0.049 | 9.049 | 0.147 | 2.16/0.66 | 3.74/0.67 | 10.08/0.76 | 25.92/0.91 | 1,440 | 864 | 0.0025 / 0.0043 / 0.0117 / 0.0300 |
| C2L | 0.1 | 6.0 | 0.24 | 0.200 | 3.597 | 0.500 | 0.72/0.92 | 1.52/0.97 | 4.17/1.03 | 10.80/0.87 | 240 | 180 | 0.0040 / 0.0084 / 0.0232 / 0.0600 |
| C2M | 0.1 | 4.0 | 0.519 | 0.167 | 5.191 | 0.417 | 1.20/0.821 | 2.53/0.77 | 6.95/0.73 | 18.00/0.91 | 600 | 450 | 0.0027 / 0.0056 / 0.0154 / 0.0400 |
| C2H | 0.075 | 3.0 | 1.47 | 0.127 | 11.023 | 0.317 | 1.73/0.66 | 3.64/0.68 | 10.00/0.70 | 25.92/0.87 | 1,440 | 864 | 0.0020 / 0.0042 / 0.0116 / 0.0300 |
| C3L (*) | * | * | 0.12 | 0.100 | 1.349 | 0.225 | 0.54/1.09 | 1.08/1.07 | 2.70/1.08 | 6.30/0.91 | - | - | - |
| C3M (*) | * | * | 0.26 | 0.083 | 1.946 | 0.188 | 0.90/0.85 | 1.80/0.83 | 4.50/0.79 | 10.50/0.98 | - | - | - |
| C3H (*) | * | * | 0.735 | 0.063 | 4.134 | 0.143 | 1.30/0.71 | 2.59/0.74 | 6.48/0.90 | 15.12/0.96 | - | - | - |
| RM1L | 0.133 | 6.0 | 0.32 | 0.267 | 3.836 | 0.533 | 0.72/0.96 | 1.25/1.00 | 3.37/1.05 | 9.45/0.94 | 240 | 180 | 0.0040 / 0.0069 / 0.0187 / 0.0525 |
| RM2M | 0.133 | 4.0 | 0.692 | 0.222 | 5.535 | 0.444 | 1.20/0.80 | 2.08/0.80 | 5.61/0.76 | 15.75/0.88 | 600 | 450 | 0.0027 / 0.0046 / 0.0125 / 0.0350 |
| PC2M | 0.1 | 4.0 | 0.519 | 0.167 | 4.153 | 0.333 | 1.20/0.82 | 2.08/0.79 | 5.61/0.75 | 15.75/0.93 | 600 | 450 | 0.0027 / 0.0046 / 0.0125 / 0.0350 |
| URML (*) | * | * | 0.24 | 0.200 | 2.397 | 0.400 | 0.41/1.00 | 0.81/1.05 | 2.03/1.09 | 4.73/1.08 | - | - | - |
| URMM (*) | * | * | 0.272 | 0.111 | 1.812 | 0.222 | 0.63/0.91 | 1.26/0.92 | 3.15/0.87 | 7.35/0.91 | - | - | - |

#### Low-Code: Cs, mu, capacity curve, structural fragility, drift ratios

Cs = design strength (fraction of weight, Table 5-7); mu = ductility (Table 5-9). Capacity points Dy (in), Ay (g), Du (in), Au (g) from Table 5-14. Fragility median Sd (in) / beta from Table 5-21. (*) = flagged in the manual as not permitted by current seismic codes.

| Type | Cs | mu | Dy | Ay | Du | Au | Slight med/beta | Moderate med/beta | Extensive med/beta | Complete med/beta | Roof ht (in) | Modal ht (in) | Drift ratio S / M / E / C |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| W1 | 0.1 | 6.0 | 0.24 | 0.200 | 4.316 | 0.600 | 0.50/0.93 | 1.25/0.97 | 3.86/1.03 | 9.45/0.99 | 168 | 126 | 0.0040 / 0.0099 / 0.0306 / 0.0750 |
| S1L | 0.033 | 5.0 | 0.153 | 0.062 | 2.292 | 0.187 | 1.30/0.78 | 2.07/0.78 | 4.38/0.78 | 10.80/0.96 | 288 | 216 | 0.0060 / 0.0096 / 0.0203 / 0.0500 |
| S1M | 0.025 | 3.3 | 0.444 | 0.039 | 4.437 | 0.117 | 2.16/0.68 | 3.44/0.78 | 7.30/0.85 | 18.00/0.98 | 720 | 540 | 0.0040 / 0.0064 / 0.0135 / 0.0333 |
| S1H | 0.017 | 2.5 | 1.164 | 0.024 | 8.732 | 0.073 | 3.37/0.66 | 5.37/0.70 | 11.38/0.76 | 28.08/0.92 | 1,872 | 1,123 | 0.0030 / 0.0048 / 0.0101 / 0.0250 |
| S2L | 0.05 | 5.0 | 0.157 | 0.100 | 1.566 | 0.200 | 1.08/0.95 | 1.73/0.90 | 4.32/0.86 | 10.80/0.99 | 288 | 216 | 0.0050 / 0.0080 / 0.0200 / 0.0500 |
| S2M | 0.05 | 3.3 | 0.607 | 0.083 | 4.043 | 0.167 | 1.80/0.69 | 2.88/0.73 | 7.20/0.85 | 18.00/0.97 | 720 | 540 | 0.0033 / 0.0053 / 0.0133 / 0.0333 |
| S2H | 0.038 | 2.5 | 1.936 | 0.063 | 9.682 | 0.127 | 2.81/0.66 | 4.49/0.68 | 11.23/0.74 | 28.08/0.92 | 1,872 | 1,123 | 0.0025 / 0.0040 / 0.0100 / 0.0250 |
| C1L | 0.033 | 5.0 | 0.098 | 0.062 | 1.467 | 0.187 | 0.90/0.95 | 1.44/0.91 | 3.60/0.85 | 9.00/0.97 | 240 | 180 | 0.0050 / 0.0080 / 0.0200 / 0.0500 |
| C1M | 0.033 | 3.3 | 0.288 | 0.052 | 2.881 | 0.156 | 1.50/0.71 | 2.40/0.74 | 6.00/0.86 | 15.00/0.98 | 600 | 450 | 0.0033 / 0.0053 / 0.0133 / 0.0333 |
| C1H | 0.017 | 2.5 | 0.503 | 0.024 | 3.77 | 0.073 | 2.16/0.70 | 3.46/0.81 | 8.64/0.89 | 21.60/0.97 | 1440 | 864 | 0.0025 / 0.0040 / 0.0100 / 0.0250 |
| C2L | 0.05 | 5.0 | 0.12 | 0.100 | 1.499 | 0.250 | 0.72/1.04 | 1.37/1.02 | 3.55/0.99 | 9.00/0.95 | 240 | 180 | 0.0040 / 0.0076 / 0.0197 / 0.0500 |
| C2M | 0.05 | 3.3 | 0.26 | 0.083 | 2.163 | 0.208 | 1.20/0.83 | 2.29/0.81 | 5.92/0.82 | 15.00/1.00 | 600 | 450 | 0.0027 / 0.0051 / 0.0132 / 0.0333 |
| C2H | 0.038 | 2.5 | 0.735 | 0.063 | 4.593 | 0.159 | 1.73/0.68 | 3.30/0.73 | 8.53/0.84 | 21.60/0.95 | 1440 | 864 | 0.0020 / 0.0038 / 0.0099 / 0.0250 |
| C3L (*) | 0.05 | 5.0 | 0.12 | 0.100 | 1.349 | 0.225 | 0.54/1.09 | 1.08/1.07 | 2.70/1.08 | 6.30/0.91 | 240 | 180 | 0.0030 / 0.0060 / 0.0150 / 0.0350 |
| C3M (*) | 0.05 | 3.3 | 0.26 | 0.083 | 1.946 | 0.188 | 0.90/0.85 | 1.80/0.83 | 4.50/0.79 | 10.50/0.98 | 600 | 450 | 0.0020 / 0.0040 / 0.0100 / 0.0233 |
| C3H (*) | 0.038 | 2.5 | 0.735 | 0.063 | 4.134 | 0.143 | 1.30/0.71 | 2.59/0.74 | 6.48/0.90 | 15.12/0.96 | 1,440 | 864 | 0.0015 / 0.0030 / 0.0075 / 0.0175 |
| RM1L | 0.067 | 5.0 | 0.16 | 0.133 | 1.598 | 0.267 | 0.72/1.12 | 1.15/1.10 | 2.89/1.10 | 7.88/0.92 | 240 | 180 | 0.0040 / 0.0064 / 0.0161 / 0.0438 |
| RM2M | 0.067 | 3.3 | 0.346 | 0.111 | 2.306 | 0.222 | 1.20/0.84 | 1.92/0.81 | 4.81/0.77 | 13.12/0.96 | 600 | 450 | 0.0027 / 0.0043 / 0.0107 / 0.0292 |
| PC2M | 0.05 | 3.3 | 0.26 | 0.083 | 1.73 | 0.167 | 1.20/0.81 | 1.92/0.79 | 4.81/0.84 | 13.12/0.99 | 600 | 450 | 0.0027 / 0.0043 / 0.0107 / 0.0292 |
| URML (*) | 0.067 | 5.0 | 0.24 | 0.200 | 2.397 | 0.400 | 0.41/1.00 | 0.81/1.05 | 2.03/1.09 | 4.73/1.08 | 180 | 135 | 0.0030 / 0.0060 / 0.0150 / 0.0350 |
| URMM (*) | 0.067 | 3.3 | 0.272 | 0.111 | 1.812 | 0.222 | 0.63/0.91 | 1.26/0.92 | 3.15/0.87 | 7.35/0.91 | 420 | 315 | 0.0020 / 0.0040 / 0.0100 / 0.0233 |

#### Pre-Code: Cs, mu, capacity curve, structural fragility, drift ratios

Cs = design strength (fraction of weight, Table 5-7); mu = ductility (Table 5-9). Capacity points Dy (in), Ay (g), Du (in), Au (g) from Table 5-15. Fragility median Sd (in) / beta from Table 5-22. (*) = flagged in the manual as not permitted by current seismic codes.

| Type | Cs | mu | Dy | Ay | Du | Au | Slight med/beta | Moderate med/beta | Extensive med/beta | Complete med/beta | Roof ht (in) | Modal ht (in) | Drift ratio S / M / E / C |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| W1 | 0.1 | 6.0 | 0.24 | 0.200 | 4.316 | 0.600 | 0.40/1.01 | 1.00/1.05 | 3.09/1.07 | 7.56/1.05 | 168 | 126 | 0.0032 / 0.0079 / 0.0245 / 0.0600 |
| S1L | 0.033 | 5.0 | 0.153 | 0.062 | 2.292 | 0.187 | 1.04/0.85 | 1.65/0.83 | 3.50/0.79 | 8.64/0.95 | 288 | 216 | 0.0048 / 0.0076 / 0.0162 / 0.0400 |
| S1M | 0.025 | 3.3 | 0.444 | 0.039 | 4.437 | 0.117 | 1.73/0.71 | 2.76/0.76 | 5.84/0.82 | 14.40/0.97 | 720 | 540 | 0.0032 / 0.0051 / 0.0108 / 0.0267 |
| S1H | 0.017 | 2.5 | 1.164 | 0.024 | 8.732 | 0.073 | 2.70/0.68 | 4.30/0.71 | 9.11/0.85 | 22.46/0.93 | 1,872 | 1,123 | 0.0024 / 0.0038 / 0.0081 / 0.0200 |
| S2L | 0.05 | 5.0 | 0.157 | 0.100 | 1.566 | 0.200 | 0.86/1.01 | 1.38/0.96 | 3.46/0.88 | 8.64/0.98 | 288 | 216 | 0.0040 / 0.0064 / 0.0160 / 0.0400 |
| S2M | 0.05 | 3.3 | 0.607 | 0.083 | 4.043 | 0.167 | 1.44/0.73 | 2.30/0.75 | 5.76/0.79 | 14.40/0.97 | 720 | 540 | 0.0027 / 0.0043 / 0.0107 / 0.0267 |
| S2H | 0.038 | 2.5 | 1.936 | 0.063 | 9.682 | 0.127 | 2.25/0.71 | 3.59/0.70 | 8.99/0.84 | 22.46/0.91 | 1,872 | 1,123 | 0.0020 / 0.0032 / 0.0080 / 0.0200 |
| C1L | 0.033 | 5.0 | 0.098 | 0.062 | 1.467 | 0.187 | 0.72/0.98 | 1.15/0.94 | 2.88/0.90 | 7.20/0.96 | 240 | 180 | 0.0040 / 0.0064 / 0.0160 / 0.0400 |
| C1M | 0.033 | 3.3 | 0.288 | 0.052 | 2.881 | 0.156 | 1.20/0.73 | 1.92/0.77 | 4.80/0.84 | 12.00/0.98 | 600 | 450 | 0.0027 / 0.0043 / 0.0107 / 0.0267 |
| C1H | 0.017 | 2.5 | 0.503 | 0.024 | 3.77 | 0.073 | 1.73/0.71 | 2.76/0.80 | 6.91/0.94 | 17.28/1.01 | 1,440 | 864 | 0.0020 / 0.0032 / 0.0080 / 0.0200 |
| C2L | 0.05 | 5.0 | 0.12 | 0.100 | 1.499 | 0.250 | 0.58/1.12 | 1.10/1.08 | 2.84/1.06 | 7.20/0.93 | 240 | 180 | 0.0032 / 0.0061 / 0.0158 / 0.0400 |
| C2M | 0.05 | 3.3 | 0.26 | 0.083 | 2.163 | 0.208 | 0.96/0.86 | 1.83/0.83 | 4.74/0.80 | 12.00/0.98 | 600 | 450 | 0.0021 / 0.0041 / 0.0105 / 0.0267 |
| C2H | 0.038 | 2.5 | 0.735 | 0.063 | 4.593 | 0.159 | 1.38/0.73 | 2.64/0.75 | 6.82/0.92 | 17.28/0.97 | 1,440 | 864 | 0.0016 / 0.0031 / 0.0079 / 0.0200 |
| C3L | 0.05 | 5.0 | 0.12 | 0.100 | 1.349 | 0.225 | 0.43/1.19 | 0.86/1.15 | 2.16/1.16 | 5.04/0.92 | 240 | 180 | 0.0024 / 0.0048 / 0.0120 / 0.0280 |
| C3M | 0.05 | 3.3 | 0.26 | 0.083 | 1.946 | 0.188 | 0.72/0.90 | 1.44/0.86 | 3.60/0.90 | 8.40/0.96 | 600 | 450 | 0.0016 / 0.0032 / 0.0080 / 0.0187 |
| C3H | 0.038 | 2.5 | 0.735 | 0.063 | 4.134 | 0.143 | 1.04/0.73 | 2.07/0.74 | 5.18/0.90 | 12.10/0.95 | 1,440 | 864 | 0.0012 / 0.0024 / 0.0060 / 0.0140 |
| RM1L | 0.067 | 5.0 | 0.16 | 0.133 | 1.598 | 0.267 | 0.58/1.20 | 0.92/1.17 | 2.31/1.17 | 6.30/0.94 | 240 | 180 | 0.0032 / 0.0051 / 0.0128 / 0.0350 |
| RM2M | 0.067 | 3.3 | 0.346 | 0.111 | 2.306 | 0.222 | 0.96/0.90 | 1.54/0.87 | 3.85/0.86 | 10.50/0.96 | 600 | 450 | 0.0021 / 0.0034 / 0.0086 / 0.0233 |
| PC2M | 0.05 | 3.3 | 0.26 | 0.083 | 1.73 | 0.167 | 0.96/0.87 | 1.54/0.83 | 3.85/0.92 | 10.50/1.00 | 600 | 450 | 0.0021 / 0.0034 / 0.0086 / 0.0233 |
| URML | 0.067 | 5.0 | 0.24 | 0.200 | 2.397 | 0.400 | 0.32/1.15 | 0.65/1.19 | 1.62/1.20 | 3.78/1.18 | 180 | 135 | 0.0024 / 0.0048 / 0.0120 / 0.0280 |
| URMM | 0.067 | 3.3 | 0.272 | 0.111 | 1.812 | 0.222 | 0.50/1.0 | 1.01/0.97 | 2.52/0.90 | 5.88/0.88 | 420 | 315 | 0.0016 / 0.0032 / 0.0080 / 0.0187 |

### 3.2 Structural repair cost ratios, Table 11-2 (percent of building replacement cost)

Source: same manual, Table 11-2 "Structural Repair Cost Ratios (in % of building replacement cost)", printed pp. 11-7 and 11-8. The manual gives these by occupancy class and structural damage state only; it does not vary them by structural model building type or by seismic design level. The method (Eq. 11-1, 11-2) multiplies the replacement cost by the probability of each damage state and the ratio below; "None" does not contribute. Nonstructural repair ratios are in Tables 11-3 and 11-4 and were not transcribed.

| Occupancy | Slight | Moderate | Extensive | Complete |
|---|---|---|---|---|
| RES1 Single-family dwelling | 0.5 | 2.3 | 11.7 | 23.4 |
| RES2 Mobile home | 0.4 | 2.4 | 7.3 | 24.4 |
| RES3A-F Multi-family dwelling | 0.3 | 1.4 | 6.9 | 13.8 |
| RES4 Temporary lodging | 0.2 | 1.4 | 6.8 | 13.6 |
| RES5 Institutional dormitory | 0.4 | 1.9 | 9.4 | 18.8 |
| RES6 Nursing home | 0.4 | 1.8 | 9.2 | 18.4 |
| COM1 Retail trade | 0.6 | 2.9 | 14.7 | 29.4 |
| COM2 Wholesale trade | 0.6 | 3.2 | 16.2 | 32.4 |
| COM3 Personal and repair services | 0.3 | 1.6 | 8.1 | 16.2 |
| COM4 Professional/technical/business services | 0.4 | 1.9 | 9.6 | 19.2 |
| COM5 Banks/financial institutions | 0.3 | 1.4 | 6.9 | 13.8 |
| COM6 Hospital | 0.2 | 1.4 | 7.0 | 14.0 |
| COM7 Medical office/clinic | 0.3 | 1.4 | 7.2 | 14.4 |
| COM8 Entertainment and recreation | 0.2 | 1.0 | 5.0 | 10.0 |
| COM9 Theaters | 0.3 | 1.2 | 6.1 | 12.2 |
| COM10 Parking | 1.3 | 6.1 | 30.4 | 60.9 |
| IND1 to IND6 (heavy, light, food/drugs/chemicals, metals/minerals, high technology, construction) | 0.4 | 1.6 | 7.8 | 15.7 |
| AGR1 Agriculture | 0.8 | 4.6 | 23.1 | 46.2 |
| REL1 Church/membership organization | 0.3 | 2.0 | 9.9 | 19.8 |
| GOV1 General services | 0.3 | 1.8 | 9.0 | 17.9 |
| GOV2 Emergency response | 0.3 | 1.5 | 7.7 | 15.3 |
| EDU1 Schools/libraries | 0.4 | 1.9 | 9.5 | 18.9 |
| EDU2 Colleges/universities | 0.2 | 1.1 | 5.5 | 11.0 |

### 3.3 Elastic damping and degradation (kappa) factors

- Elastic damping: Section 5.6.1.1 states that elastic damping BE "is dependent on structure type and is based on the recommendations of Newmark and Hall" and that the 5 percent-damped input spectrum is reduced for effective damping (elastic plus hysteretic, Eq. 5-9 and 5-10, which are images in the PDF). No per-building-type table of elastic damping values (BE) was found in the manual text. NOT VERIFIED: numeric BE by building type.
- Degradation factor k (kappa) that scales hysteretic damping with ground-motion duration: Table 5-42 (printed pp. 5-75 and 5-76). The manual assigns Short duration to scenario earthquakes at one magnitude threshold (5.5), Long duration at another (7.5) and Moderate otherwise (the inequality signs were lost in the text extraction; the context is Short below 5.5 and Long above 7.5). It states the k values for Severe-Code and Very High-Code equal those for High-Code. In the manual's Figure 5-7 example (M 7.0, Moderate-Code) Short, Moderate and Long durations use k = 0.80, 0.40 and 0.20, consistent with the Moderate-Code column below.
- Columns: Short / Moderate / Long duration. The Pre-Code S1M and S1H long-duration entry prints 0.20 (not 0.00) in this edition.

| Type | High-Code S/M/L | Moderate-Code S/M/L | Low-Code S/M/L | Pre-Code S/M/L |
|---|---|---|---|---|
| W1 | 1.00/0.80/0.50 | 0.90/0.60/0.30 | 0.70/0.40/0.20 | 0.50/0.30/0.10 |
| S1L | 0.90/0.60/0.40 | 0.80/0.40/0.20 | 0.60/0.30/0.10 | 0.40/0.20/0.00 |
| S1M | 0.90/0.60/0.40 | 0.80/0.40/0.20 | 0.60/0.30/0.10 | 0.40/0.20/0.20 |
| S1H | 0.90/0.60/0.40 | 0.80/0.40/0.20 | 0.60/0.30/0.10 | 0.40/0.20/0.20 |
| S2L | 0.70/0.50/0.30 | 0.60/0.40/0.20 | 0.50/0.30/0.10 | 0.40/0.20/0.00 |
| S2M | 0.70/0.50/0.30 | 0.60/0.40/0.20 | 0.50/0.30/0.10 | 0.40/0.20/0.00 |
| S2H | 0.70/0.50/0.30 | 0.60/0.40/0.20 | 0.50/0.30/0.10 | 0.40/0.20/0.00 |
| C1L | 0.90/0.60/0.40 | 0.80/0.40/0.20 | 0.60/0.30/0.10 | 0.40/0.20/0.00 |
| C1M | 0.90/0.60/0.40 | 0.80/0.40/0.20 | 0.60/0.30/0.10 | 0.40/0.20/0.00 |
| C1H | 0.90/0.60/0.40 | 0.80/0.40/0.20 | 0.60/0.30/0.10 | 0.40/0.20/0.00 |
| C2L | 0.90/0.60/0.40 | 0.80/0.40/0.20 | 0.60/0.30/0.10 | 0.40/0.20/0.00 |
| C2M | 0.90/0.60/0.40 | 0.80/0.40/0.20 | 0.60/0.30/0.10 | 0.40/0.20/0.00 |
| C2H | 0.90/0.60/0.40 | 0.80/0.40/0.20 | 0.60/0.30/0.10 | 0.40/0.20/0.00 |
| C3L | 0.50/0.30/0.10 | 0.50/0.30/0.10 | 0.50/0.30/0.10 | 0.40/0.20/0.00 |
| C3M | 0.50/0.30/0.10 | 0.50/0.30/0.10 | 0.50/0.30/0.10 | 0.40/0.20/0.00 |
| C3H | 0.50/0.30/0.10 | 0.50/0.30/0.10 | 0.50/0.30/0.10 | 0.40/0.20/0.00 |
| RM1L | 0.90/0.60/0.40 | 0.80/0.40/0.20 | 0.60/0.30/0.10 | 0.40/0.20/0.00 |
| RM2M | 0.90/0.60/0.40 | 0.80/0.40/0.20 | 0.60/0.30/0.10 | 0.40/0.20/0.00 |
| PC2M | 0.70/0.50/0.30 | 0.60/0.40/0.20 | 0.50/0.30/0.10 | 0.40/0.20/0.00 |
| URML | 0.50/0.30/0.10 | 0.50/0.30/0.10 | 0.50/0.30/0.10 | 0.40/0.20/0.00 |
| URMM | 0.50/0.30/0.10 | 0.50/0.30/0.10 | 0.50/0.30/0.10 | 0.40/0.20/0.00 |

---

## 4. Damping of buildings

### 4.1 Earthquake-amplitude statistics, Cruz and Miranda (Stanford)

Primary paper: Cruz, C., Miranda, E. (2017) "Evaluation of damping ratios for the seismic analysis of tall buildings", J. Struct. Eng. 143(1):04016144, DOI 10.1061/(ASCE)ST.1943-541X.0001628 (DOI read in search-result text citing the paper; the ASCE page was not retrieved, so the paper's own equations and scatter are NOT VERIFIED).

Read in a retrieved document: Miranda and Cruz, "Using Acceleration Sensors to Learn and Improve the Modeling of Damping in Buildings", 2020 PEER Annual Meeting slides (39 pages), https://peer.berkeley.edu/sites/default/files/e_miranda_peer.pdf :
- Dataset (slide 18): 1335 recorded seismic responses, 154 buildings, 117 earthquakes, 1038 reliable data points for damping in the first translational mode; compared with 86 data points in ATC-72 (basis of PEER TBI v1.0).
- Buildings taller than 150 m (490 ft): all inferred damping ratios are smaller than the currently recommended 2.5 percent, except one building with sloshing dampers in one direction (slide 17, 14 tall buildings).
- Conclusions (slide 38): damping ratio decreases with increasing building height; beyond a very small lateral deformation little or no amplitude dependence; no statistically significant difference between steel and reinforced-concrete buildings; lateral system sometimes changes the value; damping ratio increases roughly linearly with frequency for fundamental and higher modes; no evidence for mass-proportional damping (Rayleigh damping not recommended); the values are similar to those in the wind literature at large amplitude.
- Quoted baseline (slide 8, ASCE 7-10 commentary, for wind serviceability): about 1 percent (steel) and 2 percent (concrete) in the United States; ISO (1997): 1 percent and 1.5 percent.
- Slide 20 shows "Proposed simplified equations" of damping ratio versus height (if H in m / if H in ft) but the equations are images and could not be read. NOT VERIFIED: the height-damping formula and the scatter.

### 4.2 Low-amplitude / Japanese full-scale data and predictor forms

Read in lecture notes by Y. Tamura (Tokyo Polytechnic University), Lecture 10 "Damping in buildings", which cite AIJ 2000 "Damping in Buildings" and the Japanese database: https://www.vibrationdata.com/tutorials_alt/damping_buildings_lecture.pdf (slides 23 to 33). Equations are partly garbled in extraction; clean items only:
- Very low amplitude frequency-dependent term (f1 = fundamental frequency in Hz; zeta as a fraction): RC buildings zeta1 = 0.0143 f1 (r = 0.89); SRC buildings zeta1 = 0.0231 f1 (r = 0.32); steel buildings zeta1 = 0.013 f1 (r = 0.65).
- Predictor structure: Jeary (1986): zeta1 = zeta0 + zetaI * (xH/H), with a frequency-dependent zeta0 (one slide shows zeta0 = 0.01 f1 + a term in the building dimension D); Lagomarsino (1993): zeta1 = alpha/f1 + beta f1 + gamma (xH/H). xH/H is the tip drift ratio. Coefficients for the full amplitude-dependent forms could not be read cleanly. NOT VERIFIED: complete Jeary and Lagomarsino coefficients.
- Related period relations from the same slides: see section 2.2.
- Satake, Suda, Arakawa, Sasaki, Tamura (2003), "Damping evaluation using full-scale data of buildings in Japan", J. Struct. Eng. 129(4):470-477, DOI 10.1061/(ASCE)0733-9445(2003)129:4(470) (DOI read in a search-result URL). From search-result text only: database of 137 steel, 25 RC and 43 steel-framed RC buildings; first-mode damping decreases with increasing natural period. The simplified height formula reported in secondary text (zeta = 98.9/H) and the paper's regressions were NOT retrieved: NOT VERIFIED.

### 4.3 Other items

- Goel and Chopra, EERC-97/14 (read), Appendix B gives period and modal damping ratios identified for 21 Northridge buildings, but no summary statistic of damping was extracted. The report's identification text uses initial guesses of 2 percent and 3 percent of critical for the first two modes. No statistic quoted here.
- Bernal et al. 2015 (damping identification in buildings from earthquake records; CSMIP seminar paper at conservation.ca.gov): retrieval returned no file. NOT VERIFIED.
- Ambient-versus-earthquake damping ratio: no ratio was found in the retrieved documents beyond the qualitative amplitude trends above.

---

## 5. GEM taxonomy and vulnerability model; OpenStreetMap and Overture licences

### 5.1 GEM Building Taxonomy
- Repository: https://github.com/gem/gem_taxonomy . README: "GEM Building taxonomy v4.0 contains 15 building attributes" (material, lateral load-resisting system, earthquake resistance design, date of construction, number of storeys, and others); spreadsheet Taxonomy_tables_v4.0.xlsx. Glossary site https://taxonomy.openquake.org/ states it is aligned with taxonomy v2 ("support for v4 is coming soon"; footer shows glossary site version 4.0.1). Validation tool: https://tools.openquake.org/taxonomy/ ; Python package: https://github.com/gem/oq-gem-taxonomy .
- Citations listed in the README: Silva et al. (2022), "A Building Classification System for Multi-hazard Risk Assessment", Int. J. Disaster Risk Science, https://doi.org/10.1007/s13753-022-00400-x ; GED4ALL multi-hazard exposure taxonomy (2018, based on GEM Taxonomy v3.0); GEM Building Taxonomy v2.0 (2013), https://www.globalquakemodel.org/gempublications/gem-building-taxonomy-version-2.0 (report authors not read).
- Licence (README "Licensing" and the repository files): code under GNU Affero General Public License v3.0 (LICENSE file begins "GNU AFFERO GENERAL PUBLIC LICENSE Version 3"); data under Creative Commons Attribution-ShareAlike 4.0 International (DATA_LICENSE file begins "Attribution-ShareAlike 4.0 International"). CC BY-SA permits commercial use with attribution and share-alike.

### 5.2 GEM global vulnerability model
- Repository: https://github.com/gem/global_vulnerability_model ; documentation https://docs.openquake.org/vulnerability/ ; version v2026.0.0, date-released 2026-06-17 (CITATION.cff), Zenodo DOI 10.5281/zenodo.8391743.
- Content per country (README): vulnerability_structural.xml, vulnerability_nonstructural.xml, vulnerability_contents.xml, vulnerability_fatalities.xml (OpenQuake Engine format), for regions Africa, Caribbean/Central America, Central Asia, East Asia, Europe (including Turkey, Italy, Portugal), Middle East, North America, North Asia, Oceania, South America, South Asia, Southeast Asia. Fragility functions are not in the repository; the README FAQ says to contact product@globalquakemodel.org for fragility functions or other metrics. Building classes follow the GEM Building Taxonomy.
- **Licence: Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International** (LICENSE.txt begins "Attribution-NonCommercial-ShareAlike 4.0 International"; CITATION.cff "license: CC-BY-NC-SA-4.0"; README states the material may not be used for commercial purposes and that "For commercial use of the data contained within this work, a specific license agreement must be made", contact product@globalquakemodel.org; other use cases: license@globalquakemodel.org). **Commercial use is not allowed under the public licence.** GitHub's licence detector shows "Other" because it does not recognise the file.
- Citations (README): Nafeh, Aljawhari, Silva (2025) The 2025 Global Vulnerability Model of the GEM Foundation, GitHub, doi 10.5281/zenodo.8391742; Aljawhari, Nafeh, Silva, "A new global vulnerability model for regional seismic risk assessments: Part 1 - structural vulnerability", Bull. Earthquake Eng. (2026), https://doi.org/10.1007/s10518-026-02443-7 ; Part 2 (nonstructural and contents) listed as in press.
- README intended-use statement: (sub-)national and regional risk assessments, loss metrics such as average annual loss ratio; apply only to building classes consistent with the taxonomy attributes used in derivation. Re-calibration tool: https://github.com/GEMScienceTools/oq-vmtk .
- The GEM global exposure model repository https://github.com/gem/global_exposure_model exists; its LICENSE.txt was not read. NOT VERIFIED.

### 5.3 OpenStreetMap
- Data licence: Open Data Commons Open Database License (ODbL). Users must credit OpenStreetMap (display the attribution notice) and make clear the data is available under the ODbL (a link to the copyright page suffices). URL: https://www.openstreetmap.org/copyright
- Tile usage policy, https://operations.osmfoundation.org/policies/tiles/ (page undated): heavy use may be blocked without notice, no SLA; show "(c) OpenStreetMap contributors" attribution; send a distinct, stable User-Agent and a valid Referer; honour cache headers (keep tiles at least 7 days if headers cannot be read); no numeric rate limit stated; prohibited: bulk downloading or pre-seeding areas, building tile archives, wide-area automated scans (especially at z >= 14), headless panning bots, and offline-download features on tile.openstreetmap.org; use HTTPS.

### 5.4 Overture Maps buildings
- Page https://docs.overturemaps.org/attribution/ : licence for the buildings theme is ODbL. Listed sources and their licences: OpenStreetMap contributors (ODbL), Esri Community Maps contributors (CC BY 4.0), Microsoft Global ML Building Footprints (ODbL), Google Open Buildings (CC BY 4.0), USGS 3D Elevation Program (no licence stated), Qian Shi et al. Zenodo 10.5281/zenodo.8174931 (CC BY 4.0), derived from BTN 2024 from ign.es (CC BY 4.0). Attribution line used in Overture's Explore tool: "(c) OpenStreetMap contributors, Overture Maps Foundation"; for publications cite "Overture Maps Foundation, overturemaps.org" with access date. CDLA Permissive 2.0 is listed for the Places theme, not buildings. Release version of the buildings data was not checked.

---

## 6. Open post-earthquake damage datasets

| Dataset | Event | Content | Access | Licence | Height/storeys per building | Damage grade per building |
|---|---|---|---|---|---|---|
| ACI 133 Turkey RC database, Hariri-Ardebili (2024), Zenodo DOI 10.5281/zenodo.13386343 (file ACI133v3.xlsx, 317 KB) | 2023 Kahramanmaras / Turkiye sequence | About 240 surveyed RC buildings (245 sheet rows by 106 columns, opened and read). Columns include age, number of stories, total height (m), floor area, column and wall areas, structural damage in 5 classes and 3 classes, soft-story flag, latitude, longitude, Vs30, T_1 columns "N/10" and "0.0466 H^0.9", and ground-motion intensity measures (M7.8 and M6.7 distances and others). Part (1) developed from the ACI Committee 133 effort (Pujol et al. 2024); companion paper Hariri-Ardebili and Sattar (2024), Earthquake Spectra | https://zenodo.org/records/13386343 | CC BY 4.0 (Zenodo metadata) | Yes (No Stories, Total Height in m) | Yes (5-class and 3-class structural damage) |
| Building damage datasets for the 2023 Turkiye earthquake, Liu, Zenodo DOI 10.5281/zenodo.18437501 (one zip, 584,760,454 bytes, published 2026-01-31) | 2023 Turkiye | Footprint shapefile of building polygons (GBA); damage from five sources (NASA ARIA damage proxy maps, UNOSAT grading, Microsoft team, manual visual interpretation, the study's result); raster layers (DEM, epicentre distance, fault distance and others). Content of the zip was not opened | https://zenodo.org/records/18437501 | CC BY 4.0 (Zenodo metadata) | Not described on the record; footprint attribute table not opened. NOT VERIFIED | Remote-sensing based damage classes (UNOSAT categories such as destroyed, major damage named on the record); not field-surveyed |
| Copernicus EMS rapid mapping EMSR648 | 2023 East Anatolian Fault Zone | 20 areas of interest; 37 products on the page (grading products, monitoring grading 01 and 02), each as a PDF map plus a vector package (.zip). Page lists delivery dates; schema of the vector data not described on the page | https://mapping.emergency.copernicus.eu/activations/EMSR648 (direct file link seen: https://emergency.copernicus.eu/mapping/download/200810/EMSR648_AOI11_GRA_MONIT01_r1_RTP01_v1_vector.zip ; not downloaded) | No licence stated on the activation page (links to a Terms and Conditions page not read). NOT VERIFIED | Not stated; satellite grading, unlikely to carry storeys. NOT VERIFIED | Damage grading of buildings (the page does not list the classes). NOT VERIFIED |
| StEER 2023 Kahramanmaras PVRR and media repository, DesignSafe project PRJ-3824 (DOIs 10.17603/ds2-7ry2-gv66 and 10.17603/ds2-mm04-xq43 from search-result text); EERI/SSEER collection PRJ-5797 | 2023 | Reconnaissance reports and media; project description cites about 28,500 buildings collapsed or partly collapsed and 66,000 severely damaged (search-result text). Project pages returned HTTP 403 | https://www.designsafe-ci.org/data/browser/public/designsafe.storage.published/PRJ-3824 | NOT VERIFIED | NOT VERIFIED | NOT VERIFIED |
| Da.D.O. (Database of Observed Damage), EUCENTRE for Italian Civil Protection | Italian earthquakes (list for 2016 Central Italy not confirmed) | Per the EUCENTRE page: type of construction and condition, damage level from none to collapse, geographic location from individual building to municipal level, post-earthquake usability, interventions; stated audience: administrators, technicians, researchers, civil protection personnel. Web GIS at https://egeos.eucentre.it/danno_osservato/web/?lang=EN (fetch failed on a certificate error) | https://www.eucentre.it/en/dado/ | No licence or terms stated on the page read | Number of storeys is a standard field of the AeDES form, but this page does not list it. NOT VERIFIED | Damage level: yes per the page; per-building download rights NOT VERIFIED |
| Mendeley Data cfp65g3v3c, Bernardini, Quagliarini, Lucesoli (2019), DOI 10.17632/cfp65g3v3c.1 | 2016 Central Italy | 50 structural units in historic centres (Accumoli, Amatrice, Arquata del Tronto, Capodacqua, Illica), with street clear/blocked status and geometric measures | https://data.mendeley.com/datasets/cfp65g3v3c/1 | CC BY NC 3.0 (as stated on the page) | Not specified on the page | EMS-98 grade 1 to 5 |

Not found: an open building-level AeDES dataset for the 2016 Central Italy sequence (searched Zenodo through its API and the web; the closest are the small Mendeley set and the access-controlled Da.D.O.). A 2019 paper snippet in search results lists nine events stored in Da.D.O. without 2016; this was not confirmed from a fetched page.

---

## Verification notes

Not confirmed, with what was tried:

1. ASCE 7-16 and 7-22 Table 12.8-2 metric Ct: only ASCE 7-16 feet values (secondary reproduction) and ASCE 7-05 printed metric values were seen. The standards themselves were not retrieved (NIBS/FEMA NEHRP provisions links returned 404; Autodesk, SkyCiv, ideCAD, Bentley pages show feet only).
2. ASCE 7-16/7-22 conditions for Ta = 0.1N and whether the Cw shear-wall formula is retained in the current standard.
3. Eurocode 8: clause 4.3.3.2.2(5) Eq. 4.9 not transcribed; national annexes not checked.
4. Gallipoli et al. 2010 formula and scatter; Oliveira and Navarro 2010 own formula; Guler et al. 2008 primary paper (only second-hand through Michel et al.); Hong and Hwang 2000 formula; Kwon and Kim 2010 (not located); Lagomarsino 1993 period formula; Crowley and Pinho 2010 table. Publisher pages blocked retrieval (403, login redirects); open mirrors returned 403/404/410.
5. Chiauzzi et al. 2012: number of measured buildings not located in the text read.
6. Goel and Chopra 1998 shear-wall equation: Ae definition read second-hand from Michel et al.; unit of H for the constants not separately confirmed. The base of the logarithm in se (log space) is not stated in the extracted text.
7. Hazus: editions 4.2 SP3, 5.1 and MR4 not retrieved; all Hazus numbers are from the 6.1 manual (July 2024). Elastic damping BE per building type is not tabulated in the text read (equations are images). Hazus Severe-Code and Very High-Code tables not transcribed; Table 11-3 and 11-4 (nonstructural) not transcribed; building types other than the 21 requested are in the same tables but not listed here. Hazus tables were extracted programmatically from the PDF text layer; the printed anomalies noted in section 3 are transcribed as printed.
8. Damping: Cruz and Miranda 2017 equations and scatter (paper not retrieved; only the 2020 slides); Satake et al. 2003 regressions; Jeary 1986 and Lagomarsino 1993 full coefficients; Bernal et al. 2015.
9. Datasets: licence and attribute schema of EMSR648 vector products; DesignSafe PRJ-3824 and PRJ-5797 contents (HTTP 403); Da.D.O. licence, 2016 coverage and storeys field; contents of the Liu Zenodo zip (not opened); GEM global exposure model licence file.
10. Overture buildings: the release version was not checked, and the attribution page carries no date.
